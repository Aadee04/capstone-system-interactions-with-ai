from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_ollama import ChatOllama
from app.agents.agent_state import AgentState, tools_list

verifier_system_prompt = """
You are a verifier. Check if the previous execution completed the assigned subtask.

Different verification criteria apply based on the executor:
CHATTER_AGENT: Check if the response is appropriate, conversational, and addresses the subtask.
TOOLER_AGENT: Check if tool calls are correct and successful.
CODER_AGENT: Check if code execution was successful and produced expected results.

Reply with EXACTLY ONE of these words:
- "success" (task completed, move to next subtask)
- "retry" (same approach failed, try again - max 3 tries for a task)
- "user_verifier" (unclear, ask user)
- "failure" (impossible to complete)
- "escalate" (retry with coder if tool missing or calculations needed)

ONE WORD ONLY. With Only 1 line of explanation in reasons, Do not explain my instructions to me.

Escalation Guidelines:
- Chatter response inappropriate/unhelpful → "retry"
- Tooler failed on calculations/math → "escalate"
- Tooler used wrong tool repeatedly → "escalate" 
- Task requires programming logic → "escalate"
- No appropriate tool exists → "escalate"
- After 2+ tooler retries → "escalate"
- Coder failed after escalation → "failure"

OUTPUT FORMAT: <choice> - <reason>

Examples:

Example 1:
Subtask: Respond to greeting and introduce yourself
Last Executor: chatter_agent
User says: "Hi, how are you?"
Here are the last five system messages for context:
Human: Hi, how are you?
AI: Hello! I'm doing well, thank you for asking. How can I assist you today?
→ success - The chatter_agent gave a friendly and appropriate response.

---

Example 2:
Subtask: Respond to greeting and introduce yourself
Last Executor: chatter_agent
Here are the last five system messages for context:
Human: Hello there
AI: ...
→ retry - The chatter_agent response was irrelevant or unhelpful.

---

Example 3:
Subtask: Open calculator
Last Executor: tooler_agent
Tooler executor attempt count: 0
Here are the last five system messages for context:
Human: Open calculator
AI: I'll open the calculator for you. (Tool call: open_app)
Tool: Calculator opened successfully
→ success - The tooler_agent executed correctly.

---

Example 4:
Subtask: Open calculator
Last Executor: tooler_agent
Tooler executor attempt count: 1
Here are the last five system messages for context:
Human: Open calculator
AIMessage(content='[{"name": "open_app", "args": {"url": "https://www.google.com"}}]', additional_kwargs={}, response_metadata={'model': 'freakycoder123/phi4-fc', 'created_at': '2025-10-23T17:06:37.8116301Z', 'done': True, 'done_reason': 'stop', 'total_duration': 653465200, 'load_duration': 291070800, 'prompt_eval_count': 1955, 'prompt_eval_duration': 11169500, 'eval_count': 23, 'eval_duration': 319511100, 'model_name': 'freakycoder123/phi4-fc'}, id='run--842ecb3e-5762-4436-bb2b-ff96073dd248-0', tool_calls=[{'name': 'open_app', 'args': {'url': 'https://www.google.com'}, 'id': 'call_0'}], usage_metadata={'input_tokens': 1955, 'output_tokens': 23, 'total_tokens': 1978})], 'tool_calls': [{'name': 'open_browser', 'args': {'url': 'https://www.google.com'}, 'id': 'call_0'}]
Tool: Error: Application not found
→ retry - The tooler_agent did not try to open the correct application. Only failed once; allow retry.

---

Example 5:
Subtask: Open calculator
Last Executor: tooler_agent
Tooler executor attempt count: 2
Here are the last five system messages for context:
Human: Open calculator
AI: I'll open the calculator for you. (Tool call: open_app)
Tool: Error: Application not found
→ escalate - tooler_agent failed multiple times; escalate to coder_agent.

---

Example 6:
Subtask: Calculate 5 * 3
Last Executor: tooler_agent
Tooler executor attempt count: 1
Here are the last five system messages for context:
Human: Calculate 5*3
AI: I'll use a tool to calculate that. (Tool call: open_app)
Tool: Failed to compute
→ escalate - tooler_agent cannot perform mathematical computation; escalate to coder_agent.

---

Example 7:
Subtask: Calculate 5 * 3
Last Executor: coder_agent
Coder executor attempt count: 0
Here are the last five system messages for context:
Human: Calculate 5*3
AI: I'll calculate that for you. (Tool call: run_python)
Tool: 15
→ success - Code executed correctly.

---

Example 8:
Subtask: Calculate factorial of 5
Last Executor: tooler_agent
Tooler executor attempt count: 2
Here are the last five system messages for context:
Human: Calculate factorial of 5
AI: I'll try to use a tool for this.
Tool: No appropriate tool available
→ escalate - No tool available for computation; escalate to coder_agent.

---

Example 9:
Subtask: Calculate factorial of 5
Last Executor: coder_agent
Coder executor attempt count: 1
Here are the last five system messages for context:
Human: Calculate factorial of 5
AIMessage(content='{\n  "name": "run_python",\n  "arguments": {\n    "code": "def factorial(n):\\n    if n == 0 or n == 1:\\n        return 10\\n    else:\\n        return n * factorial(n-1)\\n\\nresult = factorial(5)\\nprint(result)"\n  }\n}', additional_kwargs={}, response_metadata={'model': 'freakycoder123/phi4-fc', 'created_at': '2025-10-23T17:03:18.3096038Z', 'done': True, 'done_reason': 'stop', 'total_duration': 1772507900, 'load_duration': 311003900, 'prompt_eval_count': 671, 'prompt_eval_duration': 475115400, 'eval_count': 72, 'eval_duration': 968406800, 'model_name': 'freakycoder123/phi4-fc'}, id='run--9eba2d75-2114-4697-80f5-c76b8b9b2e14-0', tool_calls=[{'name': 'run_python', 'args': {'code': 'def factorial(n):\n    if n == 0 or n == 1:\n        return 10\n    else:\n        return n * factorial(n-1)\n\nresult = factorial(5)\nprint(result)'}, 'id': 'call_0'}]
→ retry - coder_agent did not provide proper code for the stopping condition n == 0 or n == 1.


"""

verifier_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools_list if t.name=="run_python"])
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

    if current_executor == "tooler_agent":
        messages.append(HumanMessage(content=f"Tooler executor attempt count: {tooler_tries}"))
    elif current_executor == "coder_agent":
        messages.append(HumanMessage(content=f"Coder executor attempt count: {coder_tries}"))
    
    messages.append(HumanMessage(content="Here are the last five system messages for context:"))
    messages.extend(state.get("messages", [])[-5:])

    # --- Invoke model ---
    response = verifier_model.invoke(messages)
    raw_text = getattr(response, "content", "") or ""
    raw_text = raw_text.strip()
    print(f"[Verifier] Raw Response: {raw_text}")

    if not raw_text:
        print("[Verifier] Empty model response, defaulting to 'user_verifier'")
        decision_text = "user_verifier"
        reason = ""
    else:
        # Split only once on '-' to separate reason
        parts = raw_text.split("-", 1)
        decision_text = parts[0].strip().lower()
        print(f"[Verifier] Raw Decision: {decision_text}")
        reason = parts[1].strip().split("\n\n")[0] if len(parts) > 1 else ""
        print(f"[Verifier] Reason: {reason}")

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
    return {
        "verifier_decision": decision,
        "subtask_index": subtask_index + 1 if decision == "success" else subtask_index,
        "verifier_reason": reason
    }
    


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
