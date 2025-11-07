from langchain_core.messages import HumanMessage, AIMessage
from app.agents.agent_state import AgentState


def user_verifier(state: AgentState) -> AgentState:
    print("[User Verifier Invoked] Subtask:", state['current_subtask'])
    
    user_msg = AIMessage(content="Does the last step result look correct? (yes / no / abort)")
    
    question = "Does the last step result look correct? (yes / no / abort)"
    # print("\n" + "="*60)
    print( f"[User Verifier] {question}")
    # print("="*60)

    state["external_messages"].append({
        "agent": "user_verifier",
        "message": question,
        "type": "query"
    })
    
    return {
        "external_messages": state["external_messages"],
        "awaiting_user_verification": True
    }
