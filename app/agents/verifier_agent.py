from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_ollama import ChatOllama
from agents.agent_state import AgentState, tool_list_with_desc_str


verifier_system_prompt = f"""
You are a verifier. Check if the previous execution completed the user's request.
The function calls must be correct and successful.
These are the available tools: {tool_list_with_desc_str}

Reply with EXACTLY ONE of these words:
- "success" (task completed, move to next subtask)
- "retry" (same approach failed, try again)
- "user_verifier" (unclear, ask user)
- "failure" (impossible to complete)
- "escalate" (retry with coder if tool missing)

ONE WORD ONLY. No explanations.

Examples:
Tool executed correctly → "success"
Tool failed with error → "retry"
Tool output unclear, user context needed → "user_verifier"
No tool can achieve this → "failure"
Repeated failure → "escalate"
Wrong tool used → "escalate"
Repeated failure after coder execution → "failure"
Code related tasks → "escalate"

"""

verifier_model = ChatOllama(model="freakycoder123/phi4-fc")
def verifier_agent(state: AgentState) -> AgentState:
    print("[Verifier Agent Invoked] Subtask:", state['current_subtask']) # DEBUGGING ---------------

    VALID_DECISIONS = {"success", "retry", "user_verifier", "failure", "escalate"}
    system_prompt = SystemMessage(content=verifier_system_prompt)
    current_subtask = state.get("current_subtask", "")

    response = verifier_model.invoke(
        [system_prompt] +
        [HumanMessage(content=current_subtask)] +
        ([HumanMessage(content="User says:" + state["user_context"])] if state.get("user_context") else []) +
        [HumanMessage(content="Last Executor: " + state.get("current_executor", ""))] +
        state["messages"][-2:]
        )

    decision_text = response.content.strip().lower()
    decision_text = decision_text.split()[0] 
    
    print(f"[Verifier] Raw response: {decision_text}")
    
    decision = "user_verifier"  # default
    for valid_decision in VALID_DECISIONS:
        if valid_decision in decision_text:
            decision = valid_decision
            break
    
    print(f"[Verifier] Parsed decision: {decision}")
    
    return {
        "verifier_decision": decision,
        "subtask_index": state["subtask_index"] + 1 if decision == "success" else state["subtask_index"]
    }

# Verifier routing decision
def verifier_routing(state: AgentState) -> str:
    decision = state.get("verifier_decision", "exit")

    user_verifier_decision = state.get("user_verifier_decision", "")
    if user_verifier_decision == "abort":
        print("[Verifier Routing] User aborted, exiting.")
        return "exit"
    elif user_verifier_decision == "yes":
        print("[Verifier Routing] User confirmed, moving to planner.")
        return "planner"
    elif user_verifier_decision == "no":
        print("[Verifier Routing] User said no, retrying tool execution.")
        return state.get("current_executor", "tooler_agent")

        
    if decision == "retry":
        current_executor = state.get('current_executor', "tooler_agent")
        return current_executor
    elif decision == "success":
        return "planner"
    elif decision == "user_verifier":
        return "user_verifier"
    elif decision == "escalate":
        return "coder_agent"
    else:  # failure
        print("[Verifier Routing] Decision error: Exiting.")
        return "exit"
