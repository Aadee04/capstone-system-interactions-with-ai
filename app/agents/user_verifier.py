from langchain_core.messages import HumanMessage, AIMessage
from agents.agent_state import AgentState


def user_verifier(state: AgentState) -> AgentState:
    print("[User Verifier Invoked] Subtask:", state['current_subtask'])
    
    user_msg = AIMessage(content="Does the last step result look correct? (yes / no / abort)")

    print("\n" + "="*60)
    print("[User Verifier] Does the last step result look correct?")
    print("Options: yes / no / abort")
    print("="*60)
    user_reply = input("Your decision: ").strip().lower()

    if user_reply not in {"yes", "no", "abort"}:
        print(f"Invalid input '{user_reply}'. Defaulting to 'abort' for safety.")
        user_reply = "abort"

    context = ""
    if user_reply == "no":
        print("\n[Optional] Please provide context on what's wrong (or press Enter to skip):")
        context = input("Context: ").strip()
        if context:
            print(f"[User Verifier] Context recorded: {context}")

    print(f"[User Verifier] Decision: {user_reply}")
    decision_msg = HumanMessage(content=f"User decision: {user_reply}")

    return {
        "user_context": context,
        "messages": [user_msg, decision_msg],  # Only return new messages
        "user_verifier_decision": user_reply
        }

