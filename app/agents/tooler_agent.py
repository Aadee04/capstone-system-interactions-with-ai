from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
import json, re
from agents.agent_state import AgentState
from agents.agent_state import tools_list, tool_list_with_desc_str

available_tools_str = "\n".join(
    f"{name}: {desc}" 
    for name, desc in tool_list_with_desc_str
    if name != "run_python"
)

print("Available tools for Tooler Agent:", available_tools_str)

tooler_system_prompt = f"""You are a desktop tool executor. You are given one subtask to complete.
Available tools: { available_tools_str }

CRITICAL:
- Select the ONE most appropriate tool for the request
- Call it exactly ONCE
- Do not explain, do not add extra text
- Just output the function call in JSON format
- Use EXACT tool names and correct argument keys
- Do Not Attempt to code or use "run_python"
- If no tool can help, respond with {{"name": "no_op", "args": {{}}}}

You will be judged on whether the tool executed successfully for that subtask.
Do NOT declare success/failure yourself - that's the verifier's job.

Subtask: "Open Chrome and go to google.com"
Response: {{"name": "open_browser", "args": {{"url": "https://www.google.com"}}}}

Subtask: "Launch the calculator"
Response: {{"name": "open_app", "args": {{"app_name": "calculator"}}}}

Subtask: "Get the current system time"
Response: {{"name": "get_time", "args": {{}}}}
"""

tooler_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools_list if not t.name=="run_python"])
def tooler_agent(state: AgentState) -> AgentState:
    print("[Tool Agent Invoked] Current Subtask:", state['current_subtask'])

    system_prompt = SystemMessage(content=tooler_system_prompt)
    response = tooler_model.invoke(
        [system_prompt] +
        [HumanMessage(content=str(state['current_subtask']))] +
        ([HumanMessage(content=state['user_context'])] if state['user_context'] else [])
    )
    
    print(f"[Tool Agent] Raw response content: {response.content}")
    print(f"[Tool Agent] Has tool_calls attr: {hasattr(response, 'tool_calls')}")
    
    
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls or len(tool_calls) == 0:
        print("[Tool Agent] No tool_calls found, attempting to parse from content")
        try:
            content = response.content.strip()
            # Strip markdown code blocks
            content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
            
            # Try to parse as JSON
            parsed = None
            if content.startswith("["):
                # Direct list format: [{"name": "tool", "arguments": {...}}]
                parsed = json.loads(content)
            elif content.startswith("{"):
                # Could be {"functools": [...]} or direct object
                parsed_obj = json.loads(content)
                if "functools" in parsed_obj:
                    parsed = parsed_obj["functools"]
                elif "name" in parsed_obj:
                    parsed = [parsed_obj]
            
            if parsed and isinstance(parsed, list):
                # Normalize the format
                tool_calls = []
                for idx, item in enumerate(parsed):
                    if isinstance(item, dict) and "name" in item:
                        tool_calls.append({
                            "name": item["name"],
                            "args": item.get("arguments", item.get("args", {})),
                            "id": f"call_{idx}"
                        })
                
                if tool_calls:
                    response.tool_calls = tool_calls
                    print(f"[Tool Agent] Converted to tool_calls: {tool_calls}")
        except Exception as e:
            print(f"[Tool Agent] Could not parse tool calls: {e}")
    
    return {
        "messages": [response],  # Only return new message
        "tool_calls": state.get("tool_calls", []) + (response.tool_calls or [])
    }
