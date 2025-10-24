
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.agents.agent_state import tools_list, create_initial_state


# -------------------------------------- Initial Setup ---------------------------------------
from app.agents.agent_state import AgentState

# AGENT NODES 
from app.agents.planner_agent import planner_agent, planner_decision
from app.agents.chatter_agent import chat_agent
from app.agents.tooler_agent import tooler_agent
from app.agents.coder_agent import coder_agent
from app.agents.verifier_agent import verifier_agent, verifier_routing
from app.agents.user_verifier import user_verifier

tool_node = ToolNode(tools=tools_list)

# ------------------------------ Helper Functions for the graph ------------------------------

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
graph.add_node("planner_agent", planner_agent)
graph.add_node("chatter_agent", chat_agent)
graph.add_node("tooler_agent", tooler_agent)
graph.add_node("coder_agent", coder_agent)
graph.add_node("execute_tool", execute_tool_with_tracking)
graph.add_node("verifier_agent", verifier_agent)
graph.add_node("user_verifier", user_verifier)

# Entry point - planner is now the entry point
graph.set_entry_point("planner_agent")

# Planner sends subtask to appropriate agent
graph.add_conditional_edges(
    "planner_agent", planner_decision, 
    {
        "chatter_agent": "chatter_agent",
        "tooler_agent": "tooler_agent", 
        "coder_agent": "coder_agent",
        "exit": END
    }
)

# Chatter goes directly to verifier (verify output)
graph.add_edge("chatter_agent", "verifier_agent")

# Tooler agent execution
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
        "chatter_agent": "chatter_agent",   # retry chatter / re-route
        "tooler_agent": "tooler_agent",     # retry with tooler / re-route
        "coder_agent": "coder_agent",       # retry with coder / re-route / escalate
        "user_verifier": "user_verifier",   # ask user for help
        "planner": "planner_agent",         # success, next subtask
        "exit": END                         # abort
    }
)

graph.add_conditional_edges(
    "user_verifier",
    lambda state: state.get("user_verifier_decision", "abort"),
    {
        "yes": "planner_agent",         # manual override - continue to next step
        "no": "verifier_agent",         # manual override - needs further working
        "abort": END                    # manual override - abort
    }
)


app = graph.compile()

# Optional visualization:
try:
    bytes_png = app.get_graph().draw_mermaid_png()
    with open("agent_graph.png", "wb") as f:
        f.write(bytes_png)
    print("Graph diagram saved as agent_graph.png")
except Exception as e:
    print("Could not generate graph diagram:", e)


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
def agent_main():
    print("\n------------------------ Desktop Assistant ------------------------")
    while True:
        print("\n----------------- User Request ------------------------")
        user_input = input("\nEnter your request (or type 'exit' to quit): ")
        print("\n-------------------------------------------------------")
        if user_input.lower() in ["exit", "quit", "q"]:
            print("Exiting Desktop Assistant.")
            break

        inputs = create_initial_state()
        inputs["messages"] = [HumanMessage(content=user_input)]
        
        # Stream and print the agent’s response
        print_stream(app.stream(inputs, stream_mode="values"))


if __name__ == "__main__":
    agent_main()

