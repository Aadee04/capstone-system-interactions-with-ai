from langchain_core.messages import HumanMessage
from agents.agent_state import AgentState


def user_verifier(state: AgentState) -> AgentState:
    print("[User Verifier Invoked] Subtask:", state['current_subtask'])
    
    user_msg = HumanMessage(content="Does the last step result look correct? (yes / no / abort)")
    state["messages"] = state["messages"] + [user_msg]

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
    state["messages"] = state["messages"] + [decision_msg]

    return {
        "user_context": context,
        "messages": state["messages"],
        "user_verifier_decision": user_reply
        }

