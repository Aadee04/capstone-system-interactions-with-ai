from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from agents.agent_state import AgentState
from agents.agent_state import tools_list


router_system_prompt = """
You are a strict classifier, that will route user requests to either a chat agent or a planner agent.
The planner agent can open applications, websites, manage files, run system commands, and execute code.
The chat agent handles casual conversation, general questions, and vague requests that have no actions.
Classify user requests into EXACTLY one category: chat or planner

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
Reply with ONE WORD ONLY: chat or planner
NO explanations. NO punctuation. NO JSON.

Examples:
Open Chrome → planner
Hi there → chat
Calculate 5+3 → planner
How are you → chat
Tell me a joke → chat
Open the file report.txt → planner
Hi, can you help me open my email → planner
What's the weather like → planner
What was the last message → chat
Show me my downloads folder → planner
Delete the file temp.txt → planner
Move report.pdf to Documents → planner
Play some music → planner
Run a Python script that prints Hello World → planner
Write code to sort a list of numbers → planner
Explain how recursion works → chat
Why is the sky blue → chat
Can you debug my code → planner
Fix this Python error → planner
Summarize this text → planner
Make a new folder called Projects → planner
Search Google for cute cats → planner
Open YouTube and play lo-fi music → planner
Good morning → chat
What's your name → chat
Let's talk about movies → chat
Can you calculate the average of these numbers → planner
Show system info → planner
Restart my computer → planner
Turn on dark mode → planner
Explain the difference between AI and ML → chat
Tell me about OpenAI → chat
Generate a chart for this data → planner
Write a Python function to reverse a string → planner
Translate this sentence to Spanish → planner
Help me plan my day → chat
Remind me to drink water → planner
Compare Python and Java → chat
Write an essay about renewable energy → chat
Download this image → planner
Open settings → planner
Can you teach me about APIs → chat
Execute the last script again → planner
Show me my recent files → planner
Create a new text document → planner
Edit the file config.json → planner
Explain what this code does → chat
What's 5 factorial → planner
Ping google.com → planner
Stop the current process → planner
Tell me something interesting → chat
"""


router_model = ChatOllama(model="freakycoder123/phi4-fc")

def router_node(state: AgentState) -> AgentState:
    print("[Router Agent Invoked]")  # DEBUGGING ---------------
    last_user_msg = state["messages"][-1].content

    if last_user_msg.strip() == "":
        route = "chat"
        print(f"[Final Router decision]: {route} (empty input)")  # DEBUGGING ---------------
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