import textwrap
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langchain_core.messages import ToolMessage
from langchain_core.messages import HumanMessage
from langchain_community.llms import Ollama
from IPython.display import Image, display
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import os, importlib, inspect



# --- Dynamically discover tools in app/tools ---
def discover_tools():
    tools = []
    for file in os.listdir("app/tools"):
        if file.endswith(".py") and file not in ["__init__.py"]:
            name = file[:-3]
            module = importlib.import_module(f"tools.{name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                # Pick only callables that have `name` and `description` attributes
                if callable(attr) and hasattr(attr, "name") and hasattr(attr, "description"):
                    tools.append(attr)
    return tools

tools = discover_tools()

tool_list_str = ", ".join([t.name for t in tools])

# --- Define the Agent ---
class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    completed_tools: list
    

# ------- PROMPTS FOR EACH AGENT -------

router_system_prompt =  """
You are a strict classifier (router).
Your ONLY task: classify the user request into exactly one of:
  - chat
  - tools
  - code

Rules:
- If the request involves opening, running, starting, using, or mentions "tool" or "agent" → respond with: tools
- If it involves programming, debugging, or code explanation → respond with: code
- Otherwise → respond with: chat

Critical:
- Reply with EXACTLY one word: chat, tools, or code.
- Do not explain, do not format JSON, do not add punctuation or text.
- Any other format is invalid.
"""

chat_agent_system_prompt = """Absolutely never produce JSON, function calls, 
                 or text starting with "functs" or "functools". 
                 If the user asks something, respond only in plain text. 
                 If the input is empty, greet the user.
                 If the user’s request looks like a tool call, you must still reply conversationally (plain text).
                 """

tools_agent_system_prompt = f"You are a desktop tool executor. Available tools: {tool_list_str}. Only call them once per request."

code_agent_system_prompt = """You are a coding assistant. Generate proper, safe Python code for the request, "
    "and run it with the run_python tool."""

# --------------------------------------


# -------------------------------------- All the Agents ---------------------------------------

# --- CHAT AGENT ---
chat_model = ChatOllama(model="freakycoder123/phi4-fc") # no desktop tools
def chat_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(
        content=(chat_agent_system_prompt))
    response = chat_model.invoke([system_prompt] + state["messages"])
    return {"messages": state["messages"] + [response]}


# --- TOOL AGENT ---
tool_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools if not t.name=="run_python"])
def tool_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=tools_agent_system_prompt)
    response = tool_model.invoke([system_prompt] + state["messages"])
    return {"messages": state["messages"] + [response]}


# --- CODER AGENT ---
coder_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools if t.name=="run_python"])
def coder_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=code_agent_system_prompt)
    response = coder_model.invoke([system_prompt] + state["messages"])
    return {"messages": state["messages"] + [response]}

# --- ROUTER AGENT ---
router_model = ChatOllama(model="freakycoder123/phi4-fc")

def router_node(state: AgentState) -> AgentState:
    last_user_msg = state["messages"][-1].content
    text = last_user_msg.lower()

    # Rule-based quick decisions
    if any(word in text for word in ["hi", "hello", "hey"]):
        route = "chat"
    elif any(tool.name.lower() in text for tool in tools):
        route = "tools"
    elif "code" in text or "python" in text:
        route = "code"
    else:
        # Fallback to LLM classification
        resp = router_model.invoke([
            SystemMessage(content=router_system_prompt),
            HumanMessage(content=last_user_msg)
        ])
        decision = resp.content.strip().lower()
        print(f"[Router decision (LLM)]: {decision}") # DEBUGGING ---------------
        if "tools" in decision:
            route = "tools"
        elif "code" in decision:
            route = "code"
        else:
            route = "chat"

    # Append routing instruction
    new_messages = state["messages"] + [SystemMessage(content=f"ROUTE:{route}")]
    return {"messages": new_messages, "completed_tools": state.get("completed_tools", [])}


# Router decision function for conditional edges
def router_decision(state: AgentState) -> str:
    last = state["messages"][-1].content
    if last.startswith("ROUTE:"):
        return last.split("ROUTE:", 1)[1].strip()
    return "chat"




# --- Trying to fix tool looping ---
def should_continue(state: AgentState, agent_type="tools"): 
    messages = state["messages"]
    last_message = messages[-1]
    
    completed = state.get("completed_tools", [])
    tool_calls = getattr(last_message, "tool_calls", []) or []

    # Tools agent → missing tool → handoff to coder
    if agent_type == "tools":
        unavailable_tools = [t for t in tool_calls if t["name"] not in [x.name for x in tools]]
        if unavailable_tools:
            return "coder_agent"  # must match edge mapping

    # Pending tool calls
    pending = [t for t in tool_calls if getattr(t, "name", None) not in completed]
    if pending:
        for t in pending:
            completed.append(getattr(t, "name", None))
        state["completed_tools"] = completed
        return "execute"  # must match edge mapping

    # No pending, no unavailable → exit
    return "exit"  # must match edge mapping




# --- Generated Tools saving ---
def generate_tool_node(code: str, tool_name: str):
    """Save generated Python code into app/tools so it's reusable later."""
    filename = f"app/tools/{tool_name}.py"
    with open(filename, "w") as f:
        f.write(textwrap.dedent(code))
    print(f"New tool saved: {filename}")
    

# ---------- Build the Agent App / Graph --------------
graph = StateGraph(AgentState)

# Nodes
graph.add_node("router", router_node)
graph.add_node("chat_agent", chat_agent)
graph.add_node("tool_agent", tool_agent)
graph.add_node("coder_agent", coder_agent)
graph.add_node("execute_tool", ToolNode(tools=tools))

# Entry point
graph.set_entry_point("router")

# Router edges
graph.add_conditional_edges(
    "router",
    router_decision,
    {
        "chat": "chat_agent",
        "tools": "tool_agent",
        "code": "coder_agent"
    }
)
graph.add_conditional_edges(
    "tool_agent", 
    lambda state: should_continue(state, agent_type="tools"), 
    {
        "execute": "execute_tool",
        "coder_agent": "coder_agent",
        "exit": END
    }
)

graph.add_conditional_edges(
    "coder_agent", 
    lambda state: should_continue(state, agent_type="code"), 
    {
        "execute": "execute_tool",
        "exit": END
    }
)

graph.add_edge("execute_tool", "tool_agent")  # tools can loop
graph.add_edge("execute_tool", "coder_agent") # code can loop

app = graph.compile()



# --- Run the Agent ---
def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        
        # If the message is a dict with 'functs' key (LangGraph tool call JSON)
        if isinstance(message, dict) and "functs" in message:
            for call in message["functs"]:
                tool_name = call.get("name")
                args = call.get("arguments", {})

                # Find the actual tool function
                tool_func = next((t for t in tools if t.name == tool_name), None)
                if tool_func:
                    result = tool_func(**args)
                    print(f"[Tool: {tool_name}] Output: {result}")
        else:
            # Normal message
            if hasattr(message, "pretty_print"):
                message.pretty_print()
            else:
                print(message)



# Main loop
while True:
    user_input = input("\nEnter your request (or type 'exit' to quit): ")
    if user_input.lower() in ["exit", "quit", "q"]:
        print("Exiting Desktop Assistant.")
        break

    # Wrap into the expected format
    inputs = {"messages": [HumanMessage(content=user_input)], "completed_tools": []}
    
    # Stream and print the agent’s response
    print_stream(app.stream(inputs, stream_mode="values"))

