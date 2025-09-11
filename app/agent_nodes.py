from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, HumanMessage
from langgraph.graph.message import add_messages
from langchain_ollama import ChatOllama
from prompts.desktop_assistant import SYSTEM_PROMPT


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def create_desktop_agent(tools, tool_list_str):
    model = ChatOllama(model="phi4-fc:latest").bind_tools(tools)

    def desktop_agent(state: AgentState) -> AgentState:
        system_prompt = SystemMessage(content=SYSTEM_PROMPT.format(tool_list=tool_list_str))
        response = model.invoke([system_prompt] + state["messages"])
        return {"messages": state["messages"] + [response]}

    return desktop_agent


def verify_result(state: AgentState) -> AgentState:
    """Check tool results and re-inject correction if needed."""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, ToolMessage) and "error" in str(last_msg.content).lower():
        correction = HumanMessage(content="The last tool failed. Try another way.")
        return {"messages": state["messages"] + [correction]}
    return state
