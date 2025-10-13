
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from agents.agent_state import tools_list


# -------------------------------------- Initial Setup ---------------------------------------
from agents.agent_state import AgentState

# AGENT NODES 
from agents.router_agent import router_node, router_decision
from agents.planner_agent import planner_agent, planner_decision
from agents.chatter_agent import chat_agent
from agents.tooler_agent import tooler_agent
from agents.coder_agent import coder_agent
from agents.verifier_agent import verifier_agent, verifier_routing
from agents.user_verifier import user_verifier

tool_node = ToolNode(tools=tools_list)

# ------------------------------ Helper Functions for the graph ------------------------------

# def should_continue(state: AgentState, agent_type="tools"): # For both tooler and coder
#     last_message = state["messages"][-1]
#     completed = state.get("completed_tools", [])
#     tool_calls = getattr(last_message, "tool_calls", []) or []
    
#     print(f"[should_continue] agent_type={agent_type}, tool_calls={tool_calls}, completed={completed}")

#     # Tools agent → missing tool → handoff to coder
#     if agent_type == "tools":
#         unavailable_tools = [t for t in tool_calls if t["name"] not in [x.name for x in tools_list]]
#         if unavailable_tools:
#             print(f"[should_continue] Unavailable tools found: {unavailable_tools}")
#             return "coder_agent"

#     # Pending tool calls → send to executor
#     pending = [t for t in tool_calls if t.get("name") not in completed]
#     if pending:
#         print(f"[should_continue] Pending tools: {pending}")
#         return "execute"

#     # No pending, no unavailable → go verify
#     print("[should_continue] No pending tools, going to exit")
#     return "exit"


# Helper function to execute tool and track completed tools
def execute_tool_with_tracking(state: AgentState) -> AgentState:
    print("[Execute Tool Invoked]")
    
    # Invoke the tool node (handles tool execution + adding ToolMessages)
    result = tool_node.invoke(state)
    
    print(f"[Execute Tool] Tool execution complete")
    print(f"[Execute Tool] Messages after execution: {len(result.get('messages', []))} messages")
    
    # Track completed tools (from the last AI message’s tool_calls)
    messages = result.get("messages", [])
    ai_msg = next((m for m in reversed(messages) if hasattr(m, "tool_calls")), None)
    if ai_msg:
        tool_calls = getattr(ai_msg, "tool_calls", []) or []
        
        completed = state.get("completed_tools", []).copy()
        for tc in tool_calls:
            tool_name = tc.get("name")
            if tool_name and tool_name not in completed:
                completed.append(tool_name)
        
        result["completed_tools"] = completed
        print(f"[Execute Tool] Completed tools: {completed}")
    
    return result


# ---------------------------------- Build the Agent App / Graph ------------------------------

graph = StateGraph(AgentState)

# Nodes
graph.add_node("router", router_node)
graph.add_node("chat_agent", chat_agent)
graph.add_node("planner_agent", planner_agent)
graph.add_node("tooler_agent", tooler_agent)
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
        "tooler_agent": "tooler_agent",
        "coder_agent": "coder_agent",
        "exit": END
    }
)

# Can tool agent do the task?
graph.add_edge("tooler_agent","execute_tool")

# Coder agent execution
graph.add_edge("coder_agent", "execute_tool")

# Always verify after execution
graph.add_edge("execute_tool", "verifier_agent")

# Verifier decides next step
graph.add_conditional_edges(
    "verifier_agent",
    verifier_routing,
    {
        "tooler_agent": "tooler_agent",     # retry with tooler
        "coder_agent": "coder_agent",   # retry with coder
        "planner": "planner_agent",     # success, next subtask
        "user_verifier": "planner_agent", # TODO REMOVE 
        # "user_verifier": "user_verifier",
        "exit": END
    }
)

graph.add_conditional_edges(
    "user_verifier",
    lambda state: state.get("user_verifier_decision", "abort"),
    {
        "yes": "planner_agent",    # continue to next step
        "no": "verifier_agent",      # tell verifier to retry
        "abort": END               # stop the graph
    }
)

graph.add_edge("chat_agent", END)

app = graph.compile()


# ------------------------------- Run the Agent --------------------------------------------
def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        
        # If the message is a dict with 'functs' key (LangGraph tool call JSON)
        if isinstance(message, dict) and "functs" in message:
            for call in message["functs"]:
                tool_name = call.get("name")
                args = call.get("arguments", {})

                # Find the actual tool function
                tool_func = next((t for t in tools_list if t.name == tool_name), None)
                if tool_func:
                    result = tool_func(**args)
                    print(f"[Tool: {tool_name}] Output: {result}")
        else:
            # Normal message
            if hasattr(message, "pretty_print"):
                message.pretty_print()
            else:
                print(message)


# -------------------------------- Main Loop (CLI) -----------------------------------------
print("\n------------------------ Desktop Assistant ------------------------")
while True:
    print("\n----------------- User Request ------------------------")
    user_input = input("\nEnter your request (or type 'exit' to quit): ")
    print("\n-------------------------------------------------------")
    if user_input.lower() in ["exit", "quit", "q"]:
        print("Exiting Desktop Assistant.")
        break

    # Wrap into the expected format
    inputs = {"messages": [HumanMessage(content=user_input)], "completed_tools": []}
    
    # Stream and print the agent’s response
    print_stream(app.stream(inputs, stream_mode="values"))

