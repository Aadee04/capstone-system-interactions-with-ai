# agent.py
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
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

def serialize_messages(messages):
    serialized = []
    for m in messages:
        if hasattr(m, "content"):
            serialized.append(str(m.content))
        else:
            serialized.append(str(m))
    return serialized

# Helper function to execute tool and track completed tools
def execute_tool_with_tracking(state: AgentState) -> AgentState:
    print("[Execute Tool Invoked]")
    
    # Invoke the tool node (handles tool execution + adding ToolMessages)
    result = tool_node.invoke(state)
    
    print(f"[Execute Tool] Messages after execution: {len(result.get('messages', []))} messages")
    
    # Ensure external_messages always exists
    if "external_messages" not in result:
        result["external_messages"] = []
    
    messages = result.get("messages", [])
    serialized_messages = serialize_messages(messages)

    # Safely append a tracking message
    result["external_messages"] = [{
    "agent": "Execute Tool",
    "message": serialized_messages,
    "type": "info"
}]

    # Debug: print tool calls if present
    ai_msg = next((m for m in reversed(messages) if hasattr(m, "tool_calls")), None)
    if ai_msg:
        tool_calls = getattr(ai_msg, "tool_calls", []) or []
        print(f"[Execute Tool] Just executed: {[tc.get('name') for tc in tool_calls]}")

    # Always carry state forward to preserve external_messages
    return {
        **state,
        **result
    }



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

def user_verifier_routing(state: AgentState) -> str:
    """Route after user_verifier based on resumed input"""
    # Get decision from resumed command
    if isinstance(state.get("__command__"), dict):
        decision = state["__command__"].get("decision", "abort")
    else:
        decision = "abort"
    
    return decision

graph.add_conditional_edges(
    "user_verifier",
    user_verifier_routing,
    {
        "yes": "verifier_agent",      # Continue to next planning step
        "no": "verifier_agent",      # Back to verification
        "abort": END
    }
)

# CRITICAL: Compile with checkpointer ONLY ONCE
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)

# Verify checkpointer is set
print(f"[Agent] Checkpointer configured: {app.checkpointer is not None}")

# # Optional visualization:
# try:
#     bytes_png = app.get_graph().draw_mermaid_png()
#     with open("agent_graph.png", "wb") as f:
#         f.write(bytes_png)
#     print("Graph diagram saved as agent_graph.png")
# except Exception as e:
#     print("Could not generate graph diagram:", e)


# ------------------------------- Run the Agent --------------------------------------------
def print_stream(stream):
    printed_ids = set()  # track messages already printed
    
    for s in stream:
        messages = s.get("messages", [])
        if not messages:
            continue
        
        # print only messages that are new
        for msg in messages:
            msg_id = getattr(msg, "id", id(msg))  # fallback to object id
            if msg_id in printed_ids:
                continue
            
            printed_ids.add(msg_id)

            # handle LangGraph tool call dicts
            if isinstance(msg, dict) and "functs" in msg:
                for call in msg["functs"]:
                    tool_name = call.get("name")
                    args = call.get("arguments", {})
                    tool_func = next((t for t in tools_list if t.name == tool_name), None)
                    if tool_func:
                        result = tool_func(**args)
                        print(f"[Tool: {tool_name}] Output: {result}")
            
            # normal LangChain or BaseMessage
            elif hasattr(msg, "pretty_print"):
                msg.pretty_print()
            else:
                print(msg)


# -------------------------------- Main Loop (CLI) -----------------------------------------
def agent_main():
    print("\n------------------------ Desktop Assistant ------------------------")
    while True:
        print("\n----------------- User Request ------------------------")
        user_input = input("\nEnter your request (or type 'exit' to quit): ")
        print("\n-------------------------------------------------------")
        if user_input.lower() in ["exit", "quit", "clear", "q"]:
            print("Exiting Desktop Assistant.")
            break

        inputs = create_initial_state()
        inputs["messages"] = [HumanMessage(content=user_input)]
        
        # Stream and print the agent's response
        print_stream(app.stream(inputs, stream_mode="values", config={"recursion_limit": 200}))


if __name__ == "__main__":
    agent_main()