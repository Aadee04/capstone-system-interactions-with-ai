from langchain_core.messages import HumanMessage
from agents.agent_state import AgentState


def user_verifier(state: AgentState) -> AgentState:
    print("[User Verifier Invoked]")
    # Ask user directly
    user_msg = HumanMessage(content="Does the last step result look correct? (yes / no / abort)")
    # Save for trace
    state["messages"] = state["messages"] + [user_msg]

    # Here you'd hook into actual user input (e.g., CLI, web UI, chat frontend)
    print("\n" + "="*60)
    print("[User Verifier] Does the last step result look correct?")
    print("Options: yes / no / abort")
    print("="*60)
    user_reply = input("Your decision: ").strip().lower()

    # Validate decision
    if user_reply not in {"yes", "no", "abort"}:
        print(f"Invalid input '{user_reply}'. Defaulting to 'abort' for safety.")
        user_reply = "abort"

    # Ask for optional context if user said 'no'
    if user_reply == "no":
        print("\n[Optional] Please provide context on what's wrong (or press Enter to skip):")
        context = input("Context: ").strip()
        if context:
            # Add user's context as a message to help the agent understand the issue
            context_msg = HumanMessage(content=f"User feedback: {context}")
            state["messages"] = state["messages"] + [context_msg]
            print(f"[User Verifier] Context recorded: {context}")

    state["user_verifier_decision"] = user_reply
    print(f"[User Verifier] Decision: {user_reply}")
    return state

