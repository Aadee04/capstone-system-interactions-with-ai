from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from discover_tools import discover_tools

tools_list = discover_tools()
tool_list_str = ", ".join([t.name for t in tools_list])

class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    route: str
    tasks: list[str]
    subtask_index: int
    current_subtask: str
    current_executor: str
    user_context: str
    tooler_tries: int
    coder_tries: int
    verifier_decision: str

def create_initial_state() -> AgentState:
    return {
        "messages": [BaseMessage(content="")],
        "route": "router",
        "tasks": [],
        "subtask_index": 0,
        "current_subtask": "",
        "current_executor": "",
        "user_context": "",
        "tooler_tries": 0,
        "coder_tries": 0,
        "verifier_decision": ""
    }