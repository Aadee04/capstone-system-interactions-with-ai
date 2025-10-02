from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
import json
from agents.agent_state import AgentState
import re


planner_system_prompt = """
You are a workflow planner. Break down complex requests into sequential subtasks.
Only respond to the last user message, the rest of the conversation is context.
Output a list of all subtasks that need to be done to fulfill the user's request. In this format:

{
  "tasks": "<description of the subtask>",
  "current_executor": "tooler_agent"
}

CRITICAL RULES:
- "current_executor" field MUST be EXACTLY either "tooler_agent" OR "coder_agent" (nothing else)
- Use "tooler_agent" for desktop actions (opening apps, browsers, files, system operations)
- Use "coder_agent" for calculations, data processing, or programming tasks
- DO NOT specify tool names - the tooler agent will select the appropriate tool
- Always end the list with a final subtask "done"


Examples:
Request: "Open Chrome"
Response: {"tasks": ["open Chrome browser", "done"], "current_executor": "tooler_agent"}

Request: "Calculate 5+3"
Response: {"tasks": ["calculate sum", "done"], "current_executor": "coder_agent"}

Request: "Open the file report.txt, and then open Chrome"
Response: {"tasks": ["Open the file report.txt", "open Chrome", "done"], "current_executor": "tooler_agent"}

Request: "Open task manager using code, then calculate 12*7"
Response: {"tasks": ["Open task manager using code", "calculate 12*7", "done"], "current_executor": "coder_agent"}

DO NOT write explanations. ONLY output valid JSON. Always end tasks list with "done".
"""

def safe_json_parse(content: str):
    try:
        # Remove markdown fences if present
        content = content.strip()
        if content.startswith("```"):
            # Take only the inside of the code block
            content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"[Planner]: json parsing failed: {e}")
        return {}

planner_model = ChatOllama(model="freakycoder123/phi4-fc")
def planner_agent(state: AgentState) -> AgentState:
    print("[Planner Agent Invoked]")  # DEBUGGING ---------------

    if state["subtask_index"] != 0:
        subtask_index = state["subtask_index"]
        tasks = state.get("tasks", [])

        if subtask_index >= len(tasks) or state.get("tasks")[subtask_index] == "done":
            return {
                "current_executor": "exit",
                "current_subtask": "done",
                "subtask_index": subtask_index
            }

        return {
            "current_executor": state.get("current_executor", "tooler_agent"),
            "current_subtask": state.get("tasks", [])[subtask_index],
            "subtask_index": subtask_index
        }

    system_prompt = HumanMessage(content=planner_system_prompt)
    response = planner_model.invoke([system_prompt] + state["messages"])
    
    print(f"[Planner] Raw response: {response.content}")  # DEBUGGING ---------------

    try:
        parsed = safe_json_parse(response.content)
    except Exception:
        parsed = {"tasks": ["done"], "current_executor": "exit"}  # fallback
        print("[Planner]: json parsing failed") # DEBUGGING ---------------
    
    print(f"[Planner parsed]: {parsed}")  # DEBUGGING ---------------
    
    response.tasks = parsed.get("tasks", ["done"])
    response.subtask = response.tasks[0]
    response.current_executor = parsed.get("current_executor")

    return {
        "current_executor": response.current_executor,
        "current_subtask": response.subtask,
        "tasks": response.tasks
    }

# Decision function for planner routing
def planner_decision(state: AgentState) -> str:
    current_executor = state.get("current_executor", "exit")
    current_subtask = state.get("current_subtask", "done")
    
    if current_executor == "exit" or current_subtask == "done":
        return "exit"  # all subtasks complete
    elif current_executor == "tooler_agent":
        return "tooler_agent"
    elif current_executor == "coder_agent":
        return "coder_agent"
    else:
        return "tooler_agent" # fallback