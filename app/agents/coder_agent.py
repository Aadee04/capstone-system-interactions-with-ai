from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
import json
from prompts.system_prompts import coder_system_prompt
from agents.agent_state import AgentState
from agents.agent_state import tools_list


coder_model = ChatOllama(model="freakycoder123/phi4-fc").bind_tools([t for t in tools_list if t.name=="run_python"])

def coder_agent(state: AgentState) -> AgentState:
    print("[Coder Agent Invoked]")
    system_prompt = SystemMessage(content=coder_system_prompt)
    response = coder_model.invoke([system_prompt] + state["messages"])
    
    print(f"[Coder Agent] Raw response content: {response.content}")
    
    # FIX: Same robust parsing as tool_agent
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
        "messages": state["messages"] + [response],
        "last_executor": "coder_agent" 
    }