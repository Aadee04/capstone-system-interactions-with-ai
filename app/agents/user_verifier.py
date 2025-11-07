from langchain_core.messages import HumanMessage, AIMessage
from app.agents.agent_state import AgentState
from langgraph.types import interrupt


def user_verifier(state: AgentState) -> AgentState:
    print("[User Verifier Invoked] Subtask:", state['current_subtask'])
    
    # Interrupt with context for the user
    interrupt_value = {
        "type": "verification",
        "question": "Does the last step result look correct? (yes / no / abort)",
        "current_subtask": state['current_subtask'],
        "last_messages": state.get("messages", [])[-3:]  # Last 3 messages for context
    }
    
    # This will pause execution until resumed
    interrupt(interrupt_value)
    
    # When resumed, this won't execute until user provides input
    return {
        "external_messages": state.get("external_messages", []),
        "awaiting_user_verification": False  # We're past the interrupt
    }
