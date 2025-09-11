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

Follow these rules strictly:
1. If the user request matches exactly one of the tools above → call it.
2. If no tool matches → generate minimal valid Python code and call the tool `run_python` with the code.
3. Never substitute with a different tool.
4. Do not answer in plain text unless explicitly asked.
""")
    response = model.invoke([system_prompt]+state['messages'])
    return {"messages": state["messages"] + [response]}



def should_continue(state: AgentState): 
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls: 
        return "exit"
    else:
        return "execute"


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
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()

# Main loop
while True:
    user_input = input("\nEnter your request (or type 'exit' to quit): ")
    if user_input.lower() in ["exit", "quit", "q"]:
        print("👋 Exiting Desktop Assistant.")
        break

    # Wrap into the expected format
    inputs = {"messages": [HumanMessage(content=user_input)]}
    
    # Stream and print the agent’s response
    print_stream(app.stream(inputs, stream_mode="values"))

