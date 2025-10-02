from langchain_core.messages import SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from prompts.system_prompts import verifier_system_prompt
from agents.agent_state import AgentState


verifier_model = ChatOllama(model="freakycoder123/phi4-fc")
def verifier_agent(state: AgentState) -> AgentState:
    print("[Verifier Agent Invoked]")
    VALID_DECISIONS = {"success", "retry", "user_verifier", "failure"}
    
    # Check if there are any ToolMessage results in recent messages
    recent_messages = state["messages"][-5:]  # Check last 5 messages
    has_tool_results = any(isinstance(msg, ToolMessage) for msg in recent_messages)
    
    print(f"[Verifier] Has tool results in recent messages: {has_tool_results}")
    
    # If no tool results found, default to user_verifier to be safe
    if not has_tool_results:
        print("[Verifier] No tool execution detected, routing to user_verifier")
        return {
            "messages": state["messages"],
            "completed_tools": state.get("completed_tools", []),
            "verifier_decision": "user_verifier",
        }
    
    system_prompt = SystemMessage(content=verifier_system_prompt)
    response = verifier_model.invoke([system_prompt] + state["messages"])
    decision_text = response.content.strip().lower()
    
    print(f"[Verifier] Raw response: {decision_text}")
    
    # FIX: Better parsing - extract decision from mixed JSON/text response
    decision = "user_verifier"  # default
    for valid_decision in VALID_DECISIONS:
        if valid_decision in decision_text:
            decision = valid_decision
            break
    
    print(f"[Verifier] Parsed decision: {decision}")
    
    return {
        "messages": state["messages"] + [response],
        "completed_tools": state.get("completed_tools", []),
        "verifier_decision": decision,
    }

# Verifier routing decision
def verifier_routing(state: AgentState) -> str:
    decision = state.get("verifier_decision", "user_verifier")
    
    if decision == "retry":
        last_executor = state.get("last_executor", "tool_agent")
        return last_executor
    elif decision == "success":
        return "planner"
    elif decision == "user_verifier":
        return "user_verifier"
    else:  # failure
        return "exit"
