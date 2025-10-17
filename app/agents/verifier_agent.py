from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_ollama import ChatOllama
from agents.agent_state import AgentState, tool_list_with_desc_str


verifier_system_prompt = f"""
You are a verifier. Check if the previous execution completed the user's request.
The function calls must be correct and successful.
These are the available tools: {tool_list_with_desc_str}

Reply with EXACTLY ONE of these words:
- "success" (task completed, move to next subtask)
- "retry" (same approach failed, try again - max 2 retries per task)
- "user_verifier" (unclear, ask user)
- "failure" (impossible to complete)
- "escalate" (retry with coder if tool missing or calculations needed)

ONE WORD ONLY. No explanations.

Escalation Guidelines:
- Tooler failed on calculations/math → "escalate"
- Tooler used wrong tool repeatedly → "escalate" 
- Task requires programming logic → "escalate"
- No appropriate tool exists → "escalate"
- After 2+ tooler retries → "escalate"
- Coder failed after escalation → "failure"

Examples:
Tool executed correctly → "success"
Tool failed with error (first time) → "retry"
Tool failed 2+ times → "escalate"
Calculation task with tools → "escalate"
Programming task with tools → "escalate"
Coder execution failed → "failure"

"""

verifier_model = ChatOllama(model="freakycoder123/phi4-fc")
def verifier_agent(state: AgentState) -> AgentState:
    print("[Verifier Agent Invoked] Subtask:", state.get("current_subtask", ""))

    # --- Handle direct user feedback overrides first ---
    user_verifier_decision = state.get("user_verifier_decision", "")
    subtask_index = state.get("subtask_index", 0)
    current_executor = state.get("current_executor", "")
    
    # Track retry attempts
    tooler_tries = state.get("tooler_tries", 0)
    coder_tries = state.get("coder_tries", 0)

    if user_verifier_decision:
        if user_verifier_decision == "abort":
            print("[Verifier] User aborted, exiting.")
            return {"verifier_decision": "exit"}
        elif user_verifier_decision == "yes":
            print("[Verifier] User confirmed success, moving to next subtask.")
            return {
                "verifier_decision": "success",
                "subtask_index": subtask_index + 1
            }
        elif user_verifier_decision == "no":
            print("[Verifier] User denied success, retrying tool execution.")
            return {"verifier_decision": "retry"}

    # If its a fresh run
    VALID_DECISIONS = {"success", "retry", "user_verifier", "failure", "escalate"}
    current_subtask = state.get("current_subtask", "")
    user_context = state.get("user_context", "")
    current_executor = state.get("current_executor", "")
    system_prompt = SystemMessage(content=verifier_system_prompt)

    # --- Build conversation for LLM ---
    messages = [
        system_prompt,
        HumanMessage(content=f"Subtask: {current_subtask}"),
        HumanMessage(content=f"Last Executor: {current_executor}"),
    ]

    if user_context:
        messages.append(HumanMessage(content=f"User says: {user_context}"))

    messages.extend(state.get("messages", [])[-5:])  # append last few tool responses

    # --- Invoke model ---
    response = verifier_model.invoke(messages)
    decision_text = response.content.strip().lower().split()[0]
    print(f"[Verifier] Raw response: {decision_text}")

    # --- Parse valid decision, default to user verifier ---
    decision = next((d for d in VALID_DECISIONS if d in decision_text), "user_verifier")
    print(f"[Verifier] Parsed decision: {decision}")
    
    # Apply retry limits and escalation logic
    if decision == "retry":
        if current_executor == "tooler_agent" and tooler_tries >= 2:
            print(f"[Verifier] Tooler tried {tooler_tries} times, escalating to coder")
            decision = "escalate"
        elif current_executor == "coder_agent" and coder_tries >= 2:
            print(f"[Verifier] Coder tried {coder_tries} times, marking as failure")
            decision = "failure"
    
    # Update retry counters
    new_state = {
        "verifier_decision": decision,
        "subtask_index": subtask_index + 1 if decision == "success" else subtask_index
    }
    
    if decision == "retry":
        if current_executor == "tooler_agent":
            new_state["tooler_tries"] = tooler_tries + 1
        elif current_executor == "coder_agent":
            new_state["coder_tries"] = coder_tries + 1
    elif decision == "success":
        # Reset retry counters for next task
        new_state["tooler_tries"] = 0
        new_state["coder_tries"] = 0
    
    return new_state


# Verifier routing decision
def verifier_routing(state: AgentState) -> str:
    decision = state.get("verifier_decision", "exit")
    user_decision = state.get("user_verifier_decision", "")
    current_executor = state.get("current_executor", "tooler_agent")

    # --- Handle explicit user responses first ---
    if user_decision == "abort":
        print("[Verifier Routing] User aborted, exiting.")
        return "exit"
    elif user_decision == "yes":
        print("[Verifier Routing] User confirmed success, returning to planner.")
        return "planner"
    elif user_decision == "no":
        print("[Verifier Routing] User denied success, retrying executor.")
        return current_executor

    # --- Handle verifier model decisions ---
    if decision == "retry":
        return current_executor
    elif decision == "success":
        return "planner"
    elif decision == "user_verifier":
        return "user_verifier"
    elif decision == "escalate":
        return "coder_agent"
    else:  # failure or unknown
        print("[Verifier Routing] Final decision Failure: exit.")
        return "exit"
