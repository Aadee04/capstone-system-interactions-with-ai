from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
import json
from prompts.system_prompts import get_tooler_system_prompt
from agents.agent_state import AgentState
from agents.agent_state import tools_list


tool_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools_list if not t.name=="run_python"])
def tool_agent(state: AgentState) -> AgentState:
    print("[Tool Agent Invoked]")
    system_prompt = SystemMessage(content=get_tooler_system_prompt(state.get("tool_list_str", "")))
    response = tool_model.invoke([system_prompt] + state["messages"])
    
    print(f"[Tool Agent] Raw response content: {response.content}")
    print(f"[Tool Agent] Has tool_calls attr: {hasattr(response, 'tool_calls')}")
    
    # FIX: Parse ANY JSON format from content and convert to tool_calls
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls or len(tool_calls) == 0:
        try:
            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
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
                for item in parsed:
                    if isinstance(item, dict) and "name" in item:
                        tool_calls.append({
                            "name": item.get("name"),
                            "args": item.get("arguments", item.get("args", {})),
                            "id": f"call_{len(tool_calls)}"
                        })
                
                if tool_calls:
                    response.tool_calls = tool_calls
                    print(f"[Tool Agent] Converted to tool_calls: {tool_calls}")
        except Exception as e:
            print(f"[Tool Agent] Could not parse tool calls: {e}")
    else:
        print(f"[Tool Agent] Using existing tool_calls: {tool_calls}")
    
    return {
        "messages": state["messages"] + [response],
        "last_executor": "tool_agent" 
    }