from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
import json
from app.agents.agent_state import AgentState
from app.agents.agent_state import tools_list


coder_system_prompt = """
You are a coding assistant. Generate safe, working Python code.

RULES:
- Use ONLY the run_python tool to execute code
- Keep code simple and focused on the task
- No system calls (os.system, subprocess) unless explicitly needed
- No file deletions without user confirmation
- Add basic error handling
- Do 
- The user may give a helping suggestion for your current subtask

Do NOT:
- Declare whether your code succeeded/failed
- Add explanatory text outside the tool call
- Write multiple solutions

Output Format:
{
  "name": "run_python",
  "arguments": {"code": <value>}
}

Examples:

User subtask: "Calculate the factorial of 5"
Output:
{
  "name": "run_python",
  "arguments": {
    "code": "def factorial(n):\\n    if n == 0 or n == 1:\\n        return 1\\n    return n * factorial(n-1)\\n\\nresult = factorial(5)\\nprint(result)"
  }
}

User subtask: "Generate the first 10 Fibonacci numbers"
Output:
{
  "name": "run_python",
  "arguments": {
    "code": "def fibonacci(n):\\n    seq = [0, 1]\\n    for i in range(2, n):\\n        seq.append(seq[-1] + seq[-2])\\n    return seq[:n]\\n\\nprint(fibonacci(10))"
  }
}

User subtask: "Get today's date in YYYY-MM-DD format"
Output:
{
  "name": "run_python",
  "arguments": {
    "code": "import datetime\\nprint(datetime.date.today().strftime('%Y-%m-%d'))"
  }
}
"""

coder_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools_list if t.name=="run_python"])

def coder_agent(state: AgentState) -> AgentState:
    print("[Coder Agent Invoked] Subtask:", state['current_subtask'])

    system_prompt = SystemMessage(content=coder_system_prompt)
    response = coder_model.invoke(
        [system_prompt] +
        [HumanMessage(content="Subtask: " + str(state['current_subtask']))] +
        ([HumanMessage(content="User suggests: " + state.get('user_context', ''))] if state.get('user_context') else [])
    )
    
    print(f"[Coder Agent] Raw response content: {response.content}")
    
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls or len(tool_calls) == 0:
        print("[Coder Agent] No tool_calls found, attempting to parse from content")
        try:
            content = response.content.strip()

            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            parsed = None
            if content.startswith("["):
                parsed = json.loads(content)
            elif content.startswith("{"):
                parsed_obj = json.loads(content)
                if "functools" in parsed_obj:
                    parsed = parsed_obj["functools"]
                elif "name" in parsed_obj:
                    parsed = [parsed_obj]
            
            if parsed and isinstance(parsed, list):
                tool_calls = []
                for item in parsed:
                    if isinstance(item, dict) and "name" in item:
                        tool_calls.append({
                            "name": item.get("name"),
                            "args": item.get("arguments", item.get("args", {})),
                            "id": f"call_{len(tool_calls)}"
                        })
                
                if tool_calls:
                    response.tool_calls = tool_calls
                    print(f"[Coder Agent] Converted to tool_calls: {tool_calls}")
        except Exception as e:
            print(f"[Coder Agent] Could not parse tool calls: {e}")
    
    return {
        "messages": [response],  # Only return new message
        "tool_calls": state.get("tool_calls", []) + (response.tool_calls or [])
    }
