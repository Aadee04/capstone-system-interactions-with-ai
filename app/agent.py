from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import json
from prompts.system_prompts import verifier_system_prompt, chatter_system_prompt, coder_system_prompt
from prompts.system_prompts import router_system_prompt, get_tooler_system_prompt, get_planner_system_prompt
from agents.discover_tools import discover_tools

# -------------------------------------- Initial Setup ---------------------------------------
tools = discover_tools()
tool_list_str = ", ".join([t.name for t in tools])

# -------------------------------- Define the Agent State (Memory) ----------------------------
class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    completed_tools: list
    route: str
    verifier_decision: str  
    user_verifier_decision: str 
    last_executor: str

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
        # print(f"[Router decision (LLM)]: {decision}") # DEBUGGING ---------------
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

# Router decision function for switching to chat or tool use------------------------------------------
def router_decision(state: AgentState) -> str:
    return state.get("route", "chat").strip().lower()


# --- PLANNER AGENT ---
planner_model = ChatOllama(model="freakycoder123/phi4-fc")
def planner_agent(state: AgentState) -> AgentState:
    print("[Planner Agent Invoked]")  # DEBUGGING ---------------
    system_prompt = SystemMessage(content=get_planner_system_prompt())
    response = planner_model.invoke([system_prompt] + state["messages"])
    
    print(f"[Planner] Raw response: {response.content}")  # DEBUGGING ---------------
    # Try to parse the LLM response as JSON
    try:
        parsed = json.loads(response.content)
        print(f"[Planner] Parsed JSON: {parsed}")  # DEBUGGING ---------------
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
    print("[Tool Agent Invoked]")
    system_prompt = SystemMessage(content=get_tooler_system_prompt(tool_list_str))
    response = tool_model.invoke([system_prompt] + state["messages"])
    
    print(f"[Tool Agent] Raw response content: {response.content}")
    print(f"[Tool Agent] Has tool_calls attr: {hasattr(response, 'tool_calls')}")
    
    # FIX: Parse ANY JSON format from content and convert to tool_calls
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls or len(tool_calls) == 0:
        try:
            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            # Try to parse as JSON
            parsed = None
            if content.startswith("["):
                # Direct list format: [{"name": "tool", "arguments": {...}}]
                parsed = json.loads(content)
            elif content.startswith("{"):
                # Could be {"functools": [...]} or direct object
                parsed_obj = json.loads(content)
                if "functools" in parsed_obj:
                    parsed = parsed_obj["functools"]
                elif "name" in parsed_obj:
                    parsed = [parsed_obj]
            
            if parsed and isinstance(parsed, list):
                # Normalize the format
                tool_calls = []
                for item in parsed:
                    if isinstance(item, dict) and "name" in item:
                        tool_calls.append({
                            "name": item.get("name"),
                            "args": item.get("arguments", item.get("args", {})),
                            "id": f"call_{len(tool_calls)}"
                        })
                
                if tool_calls:
                    response.tool_calls = tool_calls
                    print(f"[Tool Agent] Converted to tool_calls: {tool_calls}")
        except Exception as e:
            print(f"[Tool Agent] Could not parse tool calls: {e}")
    else:
        print(f"[Tool Agent] Using existing tool_calls: {tool_calls}")
    
    return {
        "messages": state["messages"] + [response],
        "last_executor": "tool_agent" 
    }



# --- CODER AGENT ---
coder_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools if t.name=="run_python"])
def coder_agent(state: AgentState) -> AgentState:
    print("[Coder Agent Invoked]")
    system_prompt = SystemMessage(content=coder_system_prompt)
    response = coder_model.invoke([system_prompt] + state["messages"])
    
    print(f"[Coder Agent] Raw response content: {response.content}")
    
    # FIX: Same robust parsing as tool_agent
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls or len(tool_calls) == 0:
        try:
            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            parsed = None
            if content.startswith("["):
                parsed = json.loads(content)
            elif content.startswith("{"):
                parsed_obj = json.loads(content)
                if "functools" in parsed_obj:
                    parsed = parsed_obj["functools"]
                elif "name" in parsed_obj:
                    parsed = [parsed_obj]
            
            if parsed and isinstance(parsed, list):
                tool_calls = []
                for item in parsed:
                    if isinstance(item, dict) and "name" in item:
                        tool_calls.append({
                            "name": item.get("name"),
                            "args": item.get("arguments", item.get("args", {})),
                            "id": f"call_{len(tool_calls)}"
                        })
                
                if tool_calls:
                    response.tool_calls = tool_calls
                    print(f"[Coder Agent] Converted to tool_calls: {tool_calls}")
        except Exception as e:
            print(f"[Coder Agent] Could not parse tool calls: {e}")
    
    return {
        "messages": state["messages"] + [response],
        "last_executor": "coder_agent" 
    }


# --- VERIFIER AGENT ---
verifier_model = ChatOllama(model="freakycoder123/phi4-fc")
def verifier_agent(state: AgentState) -> AgentState:
    print("[Verifier Agent Invoked]")
    VALID_DECISIONS = {"success", "retry", "user_verifier", "failure"}
    
    # Check if there are any ToolMessage results in recent messages
    recent_messages = state["messages"][-5:]  # Check last 5 messages
    has_tool_results = any(isinstance(msg, ToolMessage) for msg in recent_messages)
    
    print(f"[Verifier] Has tool results in recent messages: {has_tool_results}")
    
    # If no tool results found, default to user_verifier to be safe
    if not has_tool_results:
        print("[Verifier] No tool execution detected, routing to user_verifier")
        return {
            "messages": state["messages"],
            "completed_tools": state.get("completed_tools", []),
            "verifier_decision": "user_verifier",
        }
    
    system_prompt = SystemMessage(content=verifier_system_prompt)
    response = verifier_model.invoke([system_prompt] + state["messages"])
    decision_text = response.content.strip().lower()
    
    print(f"[Verifier] Raw response: {decision_text}")
    
    # FIX: Better parsing - extract decision from mixed JSON/text response
    decision = "user_verifier"  # default
    for valid_decision in VALID_DECISIONS:
        if valid_decision in decision_text:
            decision = valid_decision
            break
    
    print(f"[Verifier] Parsed decision: {decision}")
    
    return {
        "messages": state["messages"] + [response],
        "completed_tools": state.get("completed_tools", []),
        "verifier_decision": decision,
    }

# Verifier routing decision
def verifier_routing(state: AgentState) -> str:
    decision = state.get("verifier_decision", "user_verifier")
    
    if decision == "retry":
        last_executor = state.get("last_executor", "tool_agent")
        return last_executor
    elif decision == "success":
        return "planner"
    elif decision == "user_verifier":
        return "user_verifier"
    else:  # failure
        return "exit"

# --- USER VERIFIER AGENT ---
def user_verifier(state: AgentState) -> AgentState:
    print("[User Verifier Invoked]")
    # Ask user directly
    user_msg = HumanMessage(content="Does the last step result look correct? (yes / no / abort)")
    # Save for trace
    state["messages"] = state["messages"] + [user_msg]

    # Here you'd hook into actual user input (e.g., CLI, web UI, chat frontend)
    print("\n" + "="*60)
    print("[User Verifier] Does the last step result look correct?")
    print("Options: yes / no / abort")
    print("="*60)
    user_reply = input("Your decision: ").strip().lower()

    # Validate decision
    if user_reply not in {"yes", "no", "abort"}:
        print(f"Invalid input '{user_reply}'. Defaulting to 'abort' for safety.")
        user_reply = "abort"

    # Ask for optional context if user said 'no'
    if user_reply == "no":
        print("\n[Optional] Please provide context on what's wrong (or press Enter to skip):")
        context = input("Context: ").strip()
        if context:
            # Add user's context as a message to help the agent understand the issue
            context_msg = HumanMessage(content=f"User feedback: {context}")
            state["messages"] = state["messages"] + [context_msg]
            print(f"[User Verifier] Context recorded: {context}")

    state["user_verifier_decision"] = user_reply
    print(f"[User Verifier] Decision: {user_reply}")
    return state



# -----------------------------------------------------------------------------------------



# ---------- Build the Agent App / Graph --------------

tool_node = ToolNode(tools=tools)

# Helper function to check if more tool calls are needed
def should_continue(state: AgentState, agent_type="tools"):
    last_message = state["messages"][-1]
    completed = state.get("completed_tools", [])
    tool_calls = getattr(last_message, "tool_calls", []) or []
    
    print(f"[should_continue] agent_type={agent_type}, tool_calls={tool_calls}, completed={completed}")

    # Tools agent → missing tool → handoff to coder
    if agent_type == "tools":
        unavailable_tools = [t for t in tool_calls if t["name"] not in [x.name for x in tools]]
        if unavailable_tools:
            print(f"[should_continue] Unavailable tools found: {unavailable_tools}")
            return "coder_agent"

    # Pending tool calls → send to executor
    pending = [t for t in tool_calls if t.get("name") not in completed]
    if pending:
        print(f"[should_continue] Pending tools: {pending}")
        return "execute"

    # No pending, no unavailable → go verify
    print("[should_continue] No pending tools, going to exit")
    return "exit"


# Helper function to execute tool and track completed tools
def execute_tool_with_tracking(state: AgentState) -> AgentState:
    print("[Execute Tool Invoked]")
    
    # Invoke the tool node - it handles everything automatically
    result = tool_node.invoke(state)
    
    print(f"[Execute Tool] Tool execution complete")
    print(f"[Execute Tool] Messages after execution: {len(result.get('messages', []))} messages")
    
    # Optional: Track which tools were just executed (extract from the tool calls in last AI message)
    # This is only useful if you want to reference completed_tools elsewhere
    messages = result.get("messages", [])
    if len(messages) >= 2:
        # The second-to-last message should be the AI message with tool_calls
        ai_msg = messages[-2]
        tool_calls = getattr(ai_msg, "tool_calls", []) or []
        
        # Get existing completed tools and add new ones
        completed = state.get("completed_tools", []).copy()
        for tc in tool_calls:
            tool_name = tc.get("name")
            if tool_name and tool_name not in completed:
                completed.append(tool_name)
        
        result["completed_tools"] = completed
        print(f"[Execute Tool] Completed tools: {completed}")
    
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
    verifier_routing,
    {
        "tool_agent": "tool_agent",     # retry with tooler
        "coder_agent": "coder_agent",   # retry with coder
        "planner": "planner_agent",     # success, next subtask
        "user_verifier": "user_verifier",
        "exit": END
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


# --------------------------- Run the Agent ----------------------------------------------
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


# ------------------------ Main Loop (CLI) --------------------------------------------
while True:
    user_input = input("\nEnter your request (or type 'exit' to quit): ")
    if user_input.lower() in ["exit", "quit", "q"]:
        print("Exiting Desktop Assistant.")
        break

    # Wrap into the expected format
    inputs = {"messages": [HumanMessage(content=user_input)], "completed_tools": []}
    
    # Stream and print the agent’s response
    print_stream(app.stream(inputs, stream_mode="values"))

