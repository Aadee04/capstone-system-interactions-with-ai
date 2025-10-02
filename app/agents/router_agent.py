from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from prompts.system_prompts import router_system_prompt
from agents.agent_state import AgentState


router_model = ChatOllama(model="freakycoder123/phi4-fc")

def router_node(state: AgentState) -> AgentState:
    print("[Router Agent Invoked]")  # DEBUGGING ---------------
    last_user_msg = state["messages"][-1].content
    text = last_user_msg.lower()
    planner_keywords = ["code", "python", "debug", "error", "function", "class"]

    # Rule-based quick decisions
    if any(word in text for word in ["hi", "hello", "hey"]):
        route = "chat"
    elif any(tool.name.lower() in text for tool in tools):
        route = "planner"
    elif any(word in text for word in planner_keywords):
        route = "planner"
    else:
        # Fallback to LLM classification
        resp = router_model.invoke([
            SystemMessage(content=router_system_prompt),
            HumanMessage(content=last_user_msg)
        ])
        decision = resp.content.strip().lower()
        # print(f"[Router decision (LLM)]: {decision}") # DEBUGGING ---------------
        if "tools" in decision:
            route = "planner"
        elif "planner" in decision:
            route = "planner"
        else:
            route = "chat"

    # Append routing instruction
    state["route"] = route
    print(f"[Final Router decision]: {state["route"]}")  # DEBUGGING ---------------

    return {"route": route}

# Router decision function for switching to chat or tool use------------------------------------------
def router_decision(state: AgentState) -> str:
    return state.get("route", "chat").strip().lower()