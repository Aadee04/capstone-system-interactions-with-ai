from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from agents.agent_state import AgentState
from agents.agent_state import tools_list


router_system_prompt = """
You are a strict classifier.
Classify user requests into EXACTLY one category: "chat" or "planner"

"planner" for:
- Opening/running/starting applications or websites
- File operations (create, delete, move files)
- System commands or automation
- Programming, debugging, or code execution
- Calculations or data processing

"chat" for:
- Greetings (hi, hello, how are you)
- General questions
- Casual conversation
- Requests for explanations without execution
- Requests that are vague or unclear
- Requests that don't specify any performable action

OUTPUT FORMAT:
Reply with ONE WORD ONLY: "chat" or "planner"
NO explanations. NO punctuation. NO JSON.

Examples:
"Open Chrome" → planner
"Hi there" → chat
"Calculate 5+3" → planner
"How are you?" → chat
"Tell me a joke" → chat
"Open the file report.txt" → planner
"Hi, can you help me open my email?" → planner
"What's the weather like?" → planner
"What was the last message?" → chat
"" → chat
"""

def reset_AgentState() -> AgentState:
    return {
        "messages": [],
        "subtask_index": 0,
        "tasks": [],
        "current_executor": "planner",
        "current_subtask": "",
        "route": "chat",  # Default route
        "verifier_decision": "",
        "user_verifier_decision": "",
        "user_context": ""
    }

router_model = ChatOllama(model="freakycoder123/phi4-fc")

def router_node(state: AgentState) -> AgentState:
    print("[Router Agent Invoked]")  # DEBUGGING ---------------
    last_user_msg = state["messages"][-1].content

    resp = router_model.invoke([
        SystemMessage(content=router_system_prompt),
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
        route = "chat"  # Default safe fallback

    print(f"[Final Router decision]: {route}")  # DEBUGGING ---------------

    
    return {
        "route": route,
        # Reset state for new requests
        "subtask_index": 0,
        "tasks": [],
        "current_executor": "",
        "user_context": "",
        "current_subtask": "",
        "verifier_decision": "",
        "user_verifier_decision": ""
        }


# Decision Function for routing based on LLM
def router_decision(state: AgentState) -> str:
    print(f"[Router Decision Route Check: {state['route']}")  # DEBUGGING ---------------
    return state.get("route", "chat").strip().lower()