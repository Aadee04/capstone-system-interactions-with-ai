from langchain_core.messages import HumanMessage, AIMessage
from app.agents.agent_state import AgentState
from langgraph.types import interrupt
from copy import deepcopy


def user_verifier(state: AgentState) -> AgentState:
    print("[User Verifier Invoked] Subtask:", state['current_subtask'])
    
    # Get thread_id from config if available
    thread_id = state.get("__config__", {}).get("thread_id", "")
    
    # Interrupt for input
    value = interrupt({"thread_id": thread_id})

    print(state.get("messages", []))
    last_msg = state.get("messages", [])[-1] if state.get("messages") else None
    decision, context = "abort", ""

    if last_msg and hasattr(last_msg, "content"):
        content = last_msg.content.strip()
        # Try to parse "User decision: X, context: Y"
        try:
            prefix = "User decision:"
            if prefix in content:
                # Split after prefix
                remainder = content.split(prefix, 1)[1].strip()
                # Split decision and context
                decision_part, context_part = remainder.split(", context:", 1)
                decision = decision_part.strip().lower()
                context = context_part.strip()
        except Exception as e:
            print("[User Verifier Parsing Error]:", e)

    
    # Update external messages for frontend
    state["external_messages"] = [{
        "type": "info",
        "agent": "user_verifier",
        "message": f"User decision: {decision}, context: {context}",
        "thread_id": thread_id
    }]
    state["user_verifier_decision"] = decision
    state["user_context"] = context

    return state