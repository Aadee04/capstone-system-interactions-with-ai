import textwrap
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langchain_core.messages import ToolMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import os, importlib, inspect
import json
from prompts.system_prompts import planner_system_prompt, chatter_system_prompt, coder_system_prompt
from prompts.system_prompts import verifier_system_prompt, router_system_prompt, get_tooler_system_prompt

# -------------------------------------- Setup ---------------------------------------
# --- Dynamically discover tools in app/tools during each run ---
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
tooler_system_prompt = get_tooler_system_prompt(tool_list_str)


# --- Define the Agent ---
class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    completed_tools: list
    route: str
    verifier_decision: str  
    user_verifier_decision: str 

# -------------------------------------- All the Agents ---------------------------------------

# --- ROUTER AGENT ---
router_model = ChatOllama(model="freakycoder123/phi4-fc")
def router_node(state: AgentState) -> AgentState:
    print("[Router Agent Invoked]")  # DEBUGGING ---------------
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
    print(f"[Final Router decision]: {state["route"]}")  # DEBUGGING ---------------

    return {"route": route}

# Router decision function for switching to chat or tool use
def router_decision(state: AgentState) -> str:
    print("[Router Edge Chosen]", state.get("route") if state.get("route") != None else None)  # DEBUGGING ---------------
    return state.get("route", "chat").strip().lower()


# --- PLANNER AGENT ---
planner_model = ChatOllama(model="freakycoder123/phi4-fc")
def planner_agent(state: AgentState) -> AgentState:
    print("[Planner Agent Invoked]")  # DEBUGGING ---------------
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
    print("[Planner decision check]")  # DEBUGGING ---------------
    last_msg = state["messages"][-1]
    agent_type = getattr(last_msg, "agent", None)

    print(f"[Planner decision]: agent_type={agent_type}, subtask={getattr(last_msg, 'subtask', None)}")  # DEBUGGING ---------------
    
    if getattr(last_msg, "subtask", None) == "done":
        return "exit"  # all subtasks complete
    elif agent_type == "tool":
        return "tool_agent"
    elif agent_type == "code":
        return "coder_agent"
    else:
        # fallback
        return "tool_agent"


# --- CHAT AGENT ---
chat_model = ChatOllama(model="freakycoder123/phi4-fc")
def chat_agent(state: AgentState) -> AgentState:
    print("[Chat Agent Invoked]")  # DEBUGGING ---------------
    system_prompt = SystemMessage(
        content=(chatter_system_prompt))
    response = chat_model.invoke([system_prompt] + state["messages"])
    return {"messages": state["messages"] + [response]}


# --- TOOL AGENT ---
tool_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools if not t.name=="run_python"])
def tool_agent(state: AgentState) -> AgentState:
    print("[Tool Agent Invoked]")  # DEBUGGING ---------------
    system_prompt = SystemMessage(content=tooler_system_prompt)
    response = tool_model.invoke([system_prompt] + state["messages"])
    return {"messages": state["messages"] + [response]}


# --- CODER AGENT ---
coder_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools if t.name=="run_python"])
def coder_agent(state: AgentState) -> AgentState:
    print("[Coder Agent Invoked]")  # DEBUGGING ---------------
    system_prompt = SystemMessage(content=coder_system_prompt)
    response = coder_model.invoke([system_prompt] + state["messages"])
    return {"messages": state["messages"] + [response]}


# --- VERIFIER AGENT ---
verifier_model = ChatOllama(model="freakycoder123/phi4-fc")
def verifier_agent(state: AgentState) -> AgentState:
    print("[Verifier Agent Invoked]")  # DEBUGGING ---------------
    VALID_DECISIONS = {"success", "retry_tool", "fallback_coder", "user_verifier", "failure"}

    system_prompt = SystemMessage(content=verifier_system_prompt)
    response = verifier_model.invoke([system_prompt] + state["messages"])
    decision = response.content.strip().lower()

    if decision not in VALID_DECISIONS:
        # Default safety net
        decision = "user_verifier"

    return {
        "messages": state["messages"] + [response],
        "completed_tools": state.get("completed_tools", []),
        "verifier_decision": decision,
    }


# --- USER VERIFIER AGENT ---
def user_verifier(state: AgentState) -> AgentState:
    print("[User Verifier Invoked]")  # DEBUGGING ---------------
    # Ask user directly
    user_msg = HumanMessage(content="Does the last step result look correct? (yes / no / abort)")
    # Save for trace
    state["messages"] = state["messages"] + [user_msg]

    # Here you’d hook into actual user input (e.g., CLI, web UI, chat frontend)
    print("[User Verifier] Does the last step result look correct? Options: (yes / no / abort)")
    user_reply = input("Input: ").strip().lower()

    if user_reply not in {"yes", "no", "abort"}:
        user_reply = "abort"  # safety default

    state["user_verifier_decision"] = user_reply
    return state


# -----------------------------------------------------------------------------------------

# --- Generated Tools saving ---
def generate_tool_node(code: str, tool_name: str):
    """Save generated Python code into app/tools so it's reusable later."""
    filename = f"app/tools/{tool_name}.py"
    with open(filename, "w") as f:
        f.write(textwrap.dedent(code))
    print(f"New tool saved: {filename}")
    

# ---------- Build the Agent App / Graph --------------

tool_node = ToolNode(tools=tools)

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
    return "exit"

# Helper function to execute tool and track completed tools# Define tool_node ONCE outside the function

def execute_tool_with_tracking(state: AgentState) -> AgentState:
    print("[Execute Tool Invoked]")
    
    # Invoke the tool node properly
    result = tool_node.invoke(state)
    
    # Track completed tools
    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", []) or []
    
    completed = result.get("completed_tools", [])
    for tc in tool_calls:
        tool_name = tc.get("name")
        if tool_name and tool_name not in completed:
            completed.append(tool_name)
    
    result["completed_tools"] = completed
    return result


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
graph.add_node("user_verifier", user_verifier)

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
    "planner_agent", planner_decision, 
    {
        "tool_agent": "tool_agent",
        "coder_agent": "coder_agent",
        "exit": END
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
        "exit": "verifier_agent"
    }
)

# Always verify after execution
graph.add_edge("execute_tool", "verifier_agent")

# Verifier decides next step
graph.add_conditional_edges(
    "verifier_agent",
    lambda state: state.get("verifier_decision", "user_verifier"),
    {
        "success": "planner_agent",
        "retry_tool": "execute_tool",
        "fallback_coder": "coder_agent",
        "user_verifier": "user_verifier",
        "failure": END,
    }
)

graph.add_conditional_edges(
    "user_verifier",
    lambda state: state.get("user_verifier_decision", "abort"),
    {
        "yes": "planner_agent",    # continue to next step
        "no": "execute_tool",      # retry tool execution
        "abort": END               # stop the graph
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

