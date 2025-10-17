from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from agents.agent_state import AgentState
from agents.agent_state import tools_list
import json
from datetime import datetime

router_system_prompt = """
You are a routing classifier. Analyze the user's request step by step:

STEP 1: Identify if the request requires ACTION or is just CONVERSATION
STEP 2: Classify based on these criteria:

PLANNER (requires action):
- File operations, system commands, application control
- Code execution, calculations, data processing
- Web browsing, downloads, system configuration
- Any request with verbs like: open, run, create, delete, execute, calculate

CHAT (conversation only):
- Greetings, questions, explanations without action
- Vague requests, general discussion
- Information requests without execution

STEP 3: Output ONLY: "planner" or "chat"

Examples:
"Open Chrome" → ACTION needed → planner
"How are you?" → CONVERSATION only → chat
"Calculate 5+3" → ACTION needed → planner
"What is Python?" → CONVERSATION only → chat
Can you help me with Python? → chat
Help me install Python → planner  
What's machine learning? → chat
Run my ML script → planner
I'm confused about this error → chat
Fix this error in my code → planner
Explain what this code does → chat
What's 5 factorial → planner
Ping google.com → planner
Stop the current process → planner
Tell me something interesting → chat

Response format: ONE WORD ONLY
"""

router_model = ChatOllama(
    model="freakycoder123/phi4-fc",
    temperature=0.1,      # Lower temperature for more consistent responses
    top_p=0.9,           # Nucleus sampling
    num_ctx=2048,        # Context window
    repeat_penalty=1.1,   # Avoid repetition
    num_predict=10,  # Limit tokens since we only need one word
    top_k=2         # Only consider top 2 tokens (planner/chat)
)


def router_node(state: AgentState) -> AgentState:
    print("[Router Agent Invoked]")  # DEBUGGING ---------------
    last_user_msg = state["messages"][-1].content

    if last_user_msg.strip() == "":
        route = "chat"
        confidence = 1.0
        print(f"[Final Router decision]: {route} (empty input)")  # DEBUGGING ---------------

        log_router_decision(last_user_msg, route, confidence)
        return {
            "route": route,
            # Reset state for new requests
            "subtask_index": 0,
            "tasks": [],
            "current_executor": "",
            "user_context": "",
            "current_subtask": "",
            "verifier_decision": "",
            "user_verifier_decision": "",
            "coder_tries": 0,
            "tooler_tries": 0
            }

    resp = router_model.invoke([
        HumanMessage(content=router_system_prompt),
        HumanMessage(content=last_user_msg)
    ])

    decision = resp.content.strip().lower()
    
    if decision == "planner":
        route = "planner"
    elif decision == "chat":
        route = "chat"
    elif "tools" in decision:  # Failsafe for hallucinated tool calls
        route = "planner"
    else:
        print(f"[Router] Unrecognized decision '{decision}', defaulting to 'chat'")
        route = "chat"  # Default safe fallback

    confidence = calculate_decision_confidence(resp.content, decision)
    print(f"[Final Router decision]: {route} (confidence: {confidence:.2f})") # DEBUGGING ---------------
    
    log_router_decision(last_user_msg, route, confidence)
    return {
        "route": route,
        # Reset state for new requests
        "subtask_index": 0,
        "tasks": [],
        "current_executor": "",
        "user_context": "",
        "current_subtask": "",
        "verifier_decision": "",
        "user_verifier_decision": "",
        "coder_tries": 0,
        "tooler_tries": 0
        }


# Decision Function for routing based on LLM
def router_decision(state: AgentState) -> str:
    print(f"[Router Decision Route Check: {state['route']}")  # DEBUGGING ---------------
    return state.get("route", "chat").strip().lower()


def log_router_decision(user_input, decision, confidence=None):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "input": user_input,
        "decision": decision,
        "confidence": confidence
    }
    
    with open("router_log.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def calculate_decision_confidence(response_text, decision):
    """Calculate confidence based on response characteristics"""
    response = response_text.strip().lower()
    
    # High confidence if exact match
    if response == decision:
        return 0.95
    
    # Medium confidence if decision is contained but with extra text
    elif decision in response:
        # Lower confidence if there's extra explanation
        extra_words = len(response.split()) - 1
        return max(0.7 - (extra_words * 0.1), 0.3)
    
    # Low confidence for unclear responses
    else:
        return 0.2
