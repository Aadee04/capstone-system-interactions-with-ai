from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
import json
from prompts.system_prompts import get_planner_system_prompt
from agents.agent_state import AgentState


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