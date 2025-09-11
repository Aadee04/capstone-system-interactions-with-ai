from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage
from tool_loader import discover_tools
from agent_nodes import AgentState, create_desktop_agent, verify_result


tools = discover_tools()
tool_list_str = ", ".join([t.name for t in tools])

graph = StateGraph(AgentState)

# Build agent node
desktop_agent = create_desktop_agent(tools, tool_list_str)
graph.add_node("desktop_agent", desktop_agent)

# Tool execution
tool_node = ToolNode(tools=tools)
graph.add_node("execute_tool", tool_node)

# Verifier
graph.add_node("verify_result", verify_result)

# Entry point
graph.set_entry_point("desktop_agent")

# Edges
def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return "exit"
    return "execute"

graph.add_conditional_edges("desktop_agent", should_continue,
    {"execute": "execute_tool", "exit": END})

graph.add_edge("execute_tool", "verify_result")
graph.add_edge("verify_result", "desktop_agent")

app = graph.compile()


def print_stream(stream):
    for s in stream:
        try:
            message = s["messages"][-1]
            message.pretty_print()
        except Exception as e:
            print(f"[Stream error] {e}")


if __name__ == "__main__":
    inputs = {"messages": [HumanMessage(content="Open calculator")]}
    print_stream(app.stream(inputs, stream_mode="values"))
