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
import json


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
  - planner

Rules:
- If the request involves opening, running, starting, using, or mentions "tool" or "agent" → respond with: planner
- If it involves programming, debugging, or code explanation → respond with: planner
- Otherwise → respond with: chat

Critical:
- Reply with EXACTLY one word: chat, or planner.
- Do not explain, do not format JSON, do not add punctuation or text.
- Any other format is invalid.
"""

planner_system_prompt = """
You are a workflow planner. Your task is to break down the input complex requests into sequential subtasks.
Output ONLY ONE subtask at a time in the following JSON format:

{
  "subtask": "<description of the subtask>",
  "agent": "<tool or code>",
  "tool_name": "<optional, name of tool if applicable>"
}

If all subtasks are complete or the overall goal is reached, output:
{
  "subtask": "done"
}

Never output plain text outside this JSON format.
"""

chatter_system_prompt = """
Absolutely never produce JSON, function calls, or text starting with "functs" or "functools". 
Respond only in plain text. 
If the input is empty, greet the user.
Keep your response concise and end immediately after answering.
Do not explain that you are following instructions.
"""

tooler_system_prompt = f"""You are a desktop tool executor. 
Available tools: {tool_list_str}. Only call them once per request.
Do not decide whether the task succeeded. Always return the result to the verifier.
"""

coder_system_prompt = """You are a coding assistant. 
Generate proper, safe Python code for the request. 
Run it with the run_python tool.
Do not declare success or failure. Always return the result to the verifier.
"""

verifier_system_prompt = """
You are a verifier. Evaluate whether the previous tool execution successfully completed the user's request.
Return exactly one of:
- success
- retry_tool
- fallback_coder
- user_verifier
- failure
"""

user_verifier_system_prompt = """
You are the human-in-the-loop verifier.
Ask the user whether the last step result looks correct.
Options for the user:
- yes → continue
- no → retry
- abort → stop
"""

# --------------------------------------


# -------------------------------------- All the Agents ---------------------------------------

# --- CHAT AGENT ---
chat_model = ChatOllama(model="freakycoder123/phi4-fc")
def chat_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(
        content=(chatter_system_prompt))
    response = chat_model.invoke([system_prompt] + state["messages"])
    return {"messages": state["messages"] + [response]}


# --- TOOL AGENT ---
tool_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools if not t.name=="run_python"])
def tool_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=tooler_system_prompt)
    response = tool_model.invoke([system_prompt] + state["messages"])
    return {"messages": state["messages"] + [response]}


# --- CODER AGENT ---
coder_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools if t.name=="run_python"])
def coder_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=coder_system_prompt)
    response = coder_model.invoke([system_prompt] + state["messages"])
    return {"messages": state["messages"] + [response]}


# --- VERIFIER AGENT ---
verifier_model = ChatOllama(model="freakycoder123/phi4-fc")
def verifier_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=verifier_system_prompt)
    response = verifier_model.invoke([system_prompt] + state["messages"])
    decision = response.content.strip().lower()
    # Save decision in state for routing
    state["verifier_decision"] = decision
    return {
        "messages": state["messages"] + [response], 
        "completed_tools": state.get("completed_tools", [])}


# --- PLANNER AGENT ---
planner_model = ChatOllama(model="freakycoder123/phi4-fc")
def planner_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=planner_system_prompt)
    response = planner_model.invoke([system_prompt] + state["messages"])
    
    # Try to parse the LLM response as JSON
    try:
        parsed = json.loads(response.content)
    except Exception:
        parsed = {"subtask": "done"}  # fallback
    
    print(f"[Planner parsed]: {parsed}")  # DEBUGGING ---------------
    # Attach parsed info as attributes for routing
    response.agent = parsed.get("agent")
    response.subtask = parsed.get("subtask")
    response.tool_name = parsed.get("tool_name")

    return {
        "messages": state["messages"] + [response],
        "completed_tools": state.get("completed_tools", [])
    }

# Planner decision function for switching between pre-built tools or coder
def planner_decision(state: AgentState) -> str:
    last_msg = state["messages"][-1]
    agent_type = getattr(last_msg, "agent", None)
    
    if getattr(last_msg, "subtask", None) == "done":
        return END  # all subtasks complete
    elif agent_type == "tool":
        return "tool_agent"
    elif agent_type == "code":
        return "coder_agent"
    else:
        # fallback
        return "tool_agent"


# --- ROUTER AGENT ---
router_model = ChatOllama(model="freakycoder123/phi4-fc")
def router_node(state: AgentState) -> AgentState:
    last_user_msg = state["messages"][-1].content
    text = last_user_msg.lower()
    planner_keywords = ["code", "python", "debug", "error", "function", "class"]

    # Rule-based quick decisions
    if any(word in text for word in ["hi", "hello", "hey"]):
        route = "chat"
    elif any(tool.name.lower() in text for tool in tools):
        route = "planner"
    elif any(word in text for word in planner_keywords):
        route = "planner"
    else:
        # Fallback to LLM classification
        resp = router_model.invoke([
            SystemMessage(content=router_system_prompt),
            HumanMessage(content=last_user_msg)
        ])
        decision = resp.content.strip().lower()
        print(f"[Router decision (LLM)]: {decision}") # DEBUGGING ---------------
        if "tools" in decision:
            route = "planner"
        elif "planner" in decision:
            route = "planner"
        else:
            route = "chat"

    # Append routing instruction
    state["route"] = route
    return {
        "messages": state["messages"],  # messages remain untouched
        "completed_tools": state.get("completed_tools", []),
        "route": route
        }

# Router decision function for switching to chat or tool use
def router_decision(state: AgentState) -> str:
    return state.get("route", "chat")

# -----------------------------------------------------------------------------------------

# --- Generated Tools saving ---
def generate_tool_node(code: str, tool_name: str):
    """Save generated Python code into app/tools so it's reusable later."""
    filename = f"app/tools/{tool_name}.py"
    with open(filename, "w") as f:
        f.write(textwrap.dedent(code))
    print(f"New tool saved: {filename}")
    

# ---------- Build the Agent App / Graph --------------

# Helper function to check if more tool calls are needed
def should_continue(state: AgentState, agent_type="tools"):
    last_message = state["messages"][-1]
    completed = state.get("completed_tools", [])
    tool_calls = getattr(last_message, "tool_calls", []) or []

    # Tools agent → missing tool → handoff to coder
    if agent_type == "tools":
        unavailable_tools = [t for t in tool_calls if t["name"] not in [x.name for x in tools]]
        if unavailable_tools:
            return "coder_agent"

    # Pending tool calls → send to executor
    pending = [t for t in tool_calls if t.get("name") not in completed]
    if pending:
        return "execute"

    # No pending, no unavailable → go verify
    return "verifier_agent"

# Helper function to execute tool and track completed tools
def execute_tool_with_tracking(state: AgentState) -> AgentState:
    tool_node = ToolNode(tools=tools)
    new_state = tool_node(state)

    last_msg = new_state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", []) or []
    if not tool_calls:
        # No tools were called → send straight to verifier
        return new_state  

    for tc in tool_calls:
        tool_name = tc.get("name")
        if tool_name:
            completed = new_state.get("completed_tools", [])
            if tool_name not in completed:
                completed.append(tool_name)
            new_state["completed_tools"] = completed

    return new_state


# Build the state graph
graph = StateGraph(AgentState)

# Nodes
graph.add_node("router", router_node)
graph.add_node("chat_agent", chat_agent)
graph.add_node("planner_agent", planner_agent)
graph.add_node("tool_agent", tool_agent)
graph.add_node("coder_agent", coder_agent)
graph.add_node("execute_tool", execute_tool_with_tracking)
graph.add_node("verifier_agent", verifier_agent)

# Entry point
graph.set_entry_point("router")

# Main Routing Branch
graph.add_conditional_edges(
    "router",
    router_decision,
    {
        "chat": "chat_agent",
        "planner": "planner_agent"
    }
)

# Planner sends subtask to agent
graph.add_conditional_edges(
    "planner_agent",
    lambda state: "tools" if "tool" in state["messages"][-1].content.lower() else "code",
    {
        "tools": "tool_agent",
        "code": "coder_agent",
    }
)

# Can tool agent do the task?
graph.add_conditional_edges(
    "tool_agent", 
    lambda state: should_continue(state, agent_type="tools"), 
    {
        "execute": "execute_tool",
        "coder_agent": "coder_agent",
        "exit": "verifier_agent"
    }
)


# Coder agent execution complete?
graph.add_conditional_edges(
    "coder_agent", 
    lambda state: should_continue(state, agent_type="code"), 
    {
        "execute": "execute_tool",
        "exit": END
    }
)

# Always verify after execution
graph.add_edge("execute_tool", "verifier_agent")

# Verifier decides next step
graph.add_conditional_edges(
    "verifier_agent",
    lambda state: state.get("verifier_decision", "success"),
    {
        "success": "planner_agent",        # go back for next subtask
        "retry_tool": "execute_tool",      # redo same tool
        "fallback_coder": "coder_agent",   # escalate to coder
        "exit": END
    }
)

graph.add_edge("chat_agent", END)
app = graph.compile()


# --- Run the Agent ----------------------------------------------------------
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

