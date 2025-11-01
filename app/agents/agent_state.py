from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from app.agents.discover_app import discover_tools, discover_tools_descriptions


tools_list = discover_tools()
# tool_list_str = ", ".join([t.name for t in tools_list])
tool_list_with_desc_str = discover_tools_descriptions()

class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_query: str
    resolved_query: str 

    tasks: list[str]
    subtask_index: int
    current_subtask: str
    current_executor: str

    tooler_tries: int
    coder_tries: int

    verifier_decision: str
    verifier_reason: str

    user_context: str # From User Verifier

    tool_calls: list[dict]
    # tool_success: str
    # tool_message: str

def create_initial_state() -> AgentState:
    return {
        "messages": [],
        "user_query": "",
        "resolved_query": "",

        "tasks": [],
        "subtask_index": 0,
        "current_subtask": "",
        "current_executor": "",

        "tooler_tries": 0,
        "coder_tries": 0,
        
        "verifier_decision": "",
        "verifier_reason": "",
        
        "user_context": "",
        "tool_calls": []
    }
