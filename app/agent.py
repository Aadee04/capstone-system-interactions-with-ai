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

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage],add_messages]


model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools(tools)
def desktop_agent(state:AgentState)->AgentState:
    system_prompt = SystemMessage(content=f"""
You are a Desktop Assistant. Available tools: {tool_list_str}.

Rules:
1. If the user request matches a tool → call it only once.
2. Once a tool returns a valid result, consider the subtask completed.
3. For casual conversation (greetings, chit-chat, small talk, questions unrelated to tools) → call talk_to_user only.
4. If no tool matches → generate minimal Python code and call run_python.
5. Never repeat a tool call for the same user input.
6. Respond with plain text only if explicitly asked.
7. Return a valid summary of any tool's valid output.
""")
    response = model.invoke([system_prompt]+state['messages'])
    return {"messages": state["messages"] + [response]}



def should_continue(state: AgentState): 
    messages = state["messages"]
    last_message = messages[-1]
    
    # Track completed tools in state
    completed = state.get("completed_tools", [])

    # Check tool calls in last message
    tool_calls = getattr(last_message, "tool_calls", []) or []
    pending = [t for t in tool_calls if getattr(t, "name", None) not in completed]

    if pending:
        # mark tools as completed
        for t in pending:
            completed.append(getattr(t, "name", None))
        state["completed_tools"] = completed
        return "execute"
    else:
        return "exit"



# TESTING CODE TO SAVE GENERATED TOOLS
def generate_tool_node(code: str, tool_name: str):
    """Save generated Python code into app/tools so it's reusable later."""
    filename = f"app/tools/{tool_name}.py"
    with open(filename, "w") as f:
        f.write(textwrap.dedent(code))
    print(f"New tool saved: {filename}")
    

graph = StateGraph(AgentState)
graph.add_node("desktop_agent",desktop_agent)
tool_node = ToolNode(tools=tools)
graph.add_node("execute_tool",tool_node)

graph.set_entry_point("desktop_agent")


graph.add_conditional_edges(
    "desktop_agent",
    should_continue,
    {
        "execute":"execute_tool",
        "exit":END
    }
)

graph.add_edge("execute_tool","desktop_agent")

app = graph.compile()

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

