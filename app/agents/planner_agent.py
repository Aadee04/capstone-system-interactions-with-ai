from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
import json
import sys
import os
import re

from app.agents.agent_state import AgentState, tool_list_with_desc_str

try:
    from modules.suggestions.proactive_suggestions import get_suggestion_engine # TODO Test
    CONTEXT_AVAILABLE = True
except ImportError:
    CONTEXT_AVAILABLE = False
    print("[Planner] Context modules not available")


planner_system_prompt = """
You are an enhanced workflow planner, which is part of a system with context awareness features. 
Your task is to break down user requests into sequential subtasks and assign the appropriate agent for each.

You have three agents available:
- chatter_agent: For conversational responses, greetings, explanations, questions to user
- tooler_agent: For desktop actions, file operations, opening apps, system commands, context-aware tasks
- coder_agent: For calculations, data processing, programming tasks, code execution

CONTEXT-AWARE FEATURES:
- The system can understand context-aware queries like "open my school folder", "close that app", "restore my work session"
- Recent files, applications, and user shortcuts are available through context tools
- Smart shortcuts and session management are integrated
- System health suggestions are available

Only respond to the last user message — the rest of the conversation is just context.
Each subtask should be clear, specific, and actionable. Add context from previous subtasks only if needed.
All subtasks are fully automated — never ask for user input.
Don't wait for tasks to complete, just list them out.

Context-aware tools available:
- save_current_session, restore_session, list_available_sessions: Session management
- execute_shortcut, list_shortcuts, create_shortcut_from_template: Smart shortcuts
- resolve_context_query, get_recent_files_context: Context resolution
- get_system_suggestions, run_health_check: Proactive suggestions

OUTPUT FORMAT:
Return a JSON array where each task specifies its executor:
[
  {"task": "<description>", "executor": "tooler_agent"},
  {"task": "<description>", "executor": "coder_agent"},
  {"task": "<description>", "executor": "chatter_agent"}
]

CRITICAL RULES:
- "executor" field MUST be EXACTLY either "chatter_agent", "tooler_agent", OR "coder_agent"
- Use "chatter_agent" for conversational responses, greetings, explanations, questions
- Use "tooler_agent" for desktop actions (opening apps, browsers, files, system operations)
- Use "coder_agent" for calculations, data processing, programming tasks, or when tools are insufficient, it will generate python code and run it
- DEFAULT to tooler_agent for action requests, chatter_agent for conversational requests
- DO NOT specify tool names — the tooler agent will select the appropriate tool automatically
- If parameters are needed (like a URL), include them directly in the subtask string
- Keep subtasks descriptive but simple
- No need for "done" or completion markers - system handles task completion automatically
- Each subtask will be automatically verified and retried/escalated if needed

Examples:

Request: "Open Chrome"
Response: [
  {"task": "Open Chrome browser", "executor": "tooler_agent"}
]

Request: "Calculate 5+3"
Response: [
  {"task": "Calculate sum of 5+3", "executor": "coder_agent"}
]

Request: "Open the file report.txt, and then open Chrome"
Response: [
  {"task": "Open the file report.txt", "executor": "tooler_agent"},
  {"task": "Open Chrome browser", "executor": "tooler_agent"}
]

Request: "Hi, who are you?"
Response: [
  {"task": "Respond to greeting and introduce yourself", "executor": "chatter_agent"}
]

Request: "Open Miniclip.com and Gmail.com in Chrome, then calculate the sum of 45 and 32"
Response: [
  {"task": "Open Chrome browser and go to https://www.miniclip.com", "executor": "tooler_agent"},
  {"task": "Open Chrome browser and go to https://mail.google.com", "executor": "tooler_agent"},
  {"task": "Calculate sum of 45 and 32", "executor": "coder_agent"}
]

Request: "Open calculator thrice"
Response: [
  {"task": "Open the calculator", "executor": "tooler_agent"},
  {"task": "Open the calculator", "executor": "tooler_agent"},
  {"task": "Open the calculator", "executor": "tooler_agent"}
]

Request: "Write Python code to print 'Hello World'"
Response: [
  {"task": "Write Python code that prints 'Hello World'", "executor": "coder_agent"}
]

Request: "Open Chrome, go to YouTube, and then open Notepad"
Response: [
  {"task": "Open Chrome browser and go to https://www.youtube.com", "executor": "tooler_agent"},
  {"task": "Open Notepad", "executor": "tooler_agent"}
]

Request: "Explain what recursion is"
Response: [
  {"task": "Explain what recursion is in programming", "executor": "chatter_agent"}
]

Request: "Search Wikipedia for Quantum Computing"
Response: [
  {"task": "Search Wikipedia for 'Quantum Computing'", "executor": "tooler_agent"}
]

Request: "Convert Celsius to Fahrenheit using Python"
Response: [
  {"task": "Write Python code to convert Celsius to Fahrenheit", "executor": "coder_agent"}
]

Request: "Check system time, then open calculator"
Response: [
  {"task": "Get current system time", "executor": "tooler_agent"},
  {"task": "Open calculator", "executor": "tooler_agent"}
]

Request: "Open the Downloads folder and delete temp.txt"
Response: [
  {"task": "Open Downloads folder", "executor": "tooler_agent"},
  {"task": "Delete file temp.txt", "executor": "tooler_agent"}
]

Request: "Write a Python function to sort a list in ascending order"
Response: [
  {"task": "Write Python function to sort a list in ascending order", "executor": "coder_agent"}
]

Request: "Ping google.com"
Response: [
  {"task": "Ping google.com", "executor": "tooler_agent"}
]

Request: "Open notepad, write a hello world program, and calculate 15*23"
Response: [
  {"task": "Open Notepad", "executor": "tooler_agent"},
  {"task": "Write hello world program in Python", "executor": "coder_agent"},
  {"task": "Calculate 15*23", "executor": "coder_agent"}
]

Request: "Open task manager and kill any chrome processes"
Response: [
  {"task": "Open task manager", "executor": "tooler_agent"},
  {"task": "Kill Chrome processes", "executor": "tooler_agent"}
]

"""

# Removed Requests that may have not been implemented correctly yet

# Request: "Create a folder named 'Projects' and move report.pdf into it"
# Response: [
#   {"task": "Create folder named 'Projects'", "executor": "tooler_agent"},
#   {"task": "Move report.pdf into 'Projects'", "executor": "tooler_agent"}
# ]

# Request: "Restart the computer"
# Response: [
#   {"task": "Restart the computer", "executor": "tooler_agent"}
# ]

# CONTEXT-AWARE EXAMPLES:

# Request: "Open my work files"
# Response: [
#   {"task": "Resolve context query 'open my work files' and execute appropriate action", "executor": "tooler_agent"}
# ]

# Request: "Save my current work session as 'project_work'"
# Response: [
#   {"task": "Save current session as 'project_work'", "executor": "tooler_agent"}
# ]

# Request: "Run my coding setup"
# Response: [
#   {"task": "Execute shortcut 'coding_setup' or create from template if needed", "executor": "tooler_agent"}
# ]

# Request: "Check system health and show suggestions"
# Response: [
#   {"task": "Run system health check and show suggestions", "executor": "tooler_agent"}
# ]

# Request: "Show me recent files I worked on"
# Response: [
#   {"task": "Get recent files using context tracking", "executor": "tooler_agent"}
# ]

# Request: "Restore my last work session"
# Response: [
#   {"task": "List available sessions and restore the most recent one", "executor": "tooler_agent"}
# ]

# Request: "Set up my daily workspace"
# Response: [
#   {"task": "Execute shortcut 'daily_startup' or create from template", "executor": "tooler_agent"}
# ]

def pre_process_query_with_context(user_message: str) -> dict: # TODO Test
    """Pre-process user query using context resolution if available"""
    if not CONTEXT_AVAILABLE:
        return {"enhanced": False, "original": user_message}
    
    try:
        # Check if this looks like a context-aware query
        context_indicators = [
            "my ", "that ", "recent ", "current ", "this ", "open ",
            "close ", "show me", "get me", "find ", "school", "work", 
            "home", "project", "session", "shortcut", "setup", "restore",
            "save my", "health", "suggestions", "optimize"
        ]
        
        user_lower = user_message.lower()
        if any(indicator in user_lower for indicator in context_indicators):
            print(f"[Planner] Detected context-aware query: {user_message}")
            return {
                "enhanced": True,
                "original": user_message,
                "context_hint": "This query may benefit from context resolution"
            }
        
        return {"enhanced": False, "original": user_message}
        
    except Exception as e:
        print(f"[Planner] Context pre-processing error: {e}")
        return {"enhanced": False, "original": user_message}


def get_proactive_suggestions_context() -> str: # TODO Test
    """Get current system suggestions for context"""
    if not CONTEXT_AVAILABLE:
        return ""
    
    try:
        engine = get_suggestion_engine()
        suggestions = engine.get_active_suggestions()
        
        if suggestions:
            high_priority = [s for s in suggestions if s.priority == 'high']
            if high_priority:
                return f"\nIMPORTANT: System has {len(high_priority)} high-priority suggestions available. Consider mentioning if user asks about system optimization."
        
        return ""
        
    except Exception as e:
        print(f"[Planner] Suggestions context error: {e}")
        return ""


def safe_json_parse(content: str):
    try:
        # Remove markdown fences if present 
        content = content.strip()
        if content.startswith("```"):
            # Extract only content inside the code block
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
            if match:
                content = match.group(1).strip()

        # Extract the first valid JSON object or array
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", content)
        if match:
            content = match.group(1).strip()

        return json.loads(content)
    except Exception as e:
        print(f"[Planner]: json parsing failed: {e}")
        return {}


planner_model = ChatOllama(model="freakycoder123/phi4-fc")
def planner_agent(state: AgentState) -> AgentState:
    print("[Enhanced Planner Agent Invoked]")  # DEBUGGING ---------------

    if state["subtask_index"] != 0: # Not the first run, just return current subtask
        subtask_index = state["subtask_index"]
        tasks = state.get("tasks", [])

        # Check if all tasks completed (index >= length)
        if subtask_index >= len(tasks):
            return {
                "current_executor": "exit",
                "current_subtask": "done",
                "subtask_index": subtask_index
            }

        current_task = tasks[subtask_index]
        
        # All tasks should now be dict format with task and executor
        if isinstance(current_task, dict):
            current_subtask = current_task.get("task", "done")
            current_executor = current_task.get("executor", "tooler_agent")
        else:
            # Legacy fallback for string tasks
            current_subtask = str(current_task)
            current_executor = "tooler_agent"

        return {
            "current_executor": current_executor,
            "current_subtask": current_subtask,
            "subtask_index": subtask_index
        }

    # If it is the first run - do context-aware planning
    user_message = state["messages"][-1].content if state.get("messages") else ""
    
    # Pre-process with context if available
    context_result = pre_process_query_with_context(user_message) # TODO Test
    
    # Get system suggestions context
    suggestions_context = get_proactive_suggestions_context() # TODO Test
    
    # Build enhanced system prompt
    full_system_prompt = planner_system_prompt + suggestions_context
    
    if context_result["enhanced"]:
        print(f"[Enhanced Planner] Context-aware query detected: {context_result['context_hint']}")
        # Add context information to the planning
        context_info = f"\nCONTEXT INFO: User query '{context_result['original']}' appears to be context-aware. Use appropriate context tools for resolution."
        full_system_prompt += context_info
    
    final_system_prompt = HumanMessage(content=full_system_prompt)

    # Generate LLM Response
    response = planner_model.invoke([final_system_prompt] + state["messages"])
    print(f"[Planner] Raw response: {response.content}")  # DEBUGGING ---------------

    # Parse Response if in json format
    try:
        parsed = safe_json_parse(response.content)
    except Exception:
        parsed = None  # Will be handled by fallback below
    
    print(f"[Planner parsed]: {parsed}")  # DEBUGGING ---------------
    
    # Handle successful parsing (should be array format)
    if isinstance(parsed, list) and parsed:
        # New array format: [{"task": "...", "executor": "..."}, ...]
        tasks = parsed
        first_task = tasks[0] if tasks else None
        
        # Set task and executor
        if isinstance(first_task, dict) and "task" in first_task and "executor" in first_task:
            current_executor = first_task["executor"]
            current_subtask = first_task["task"]
        else:
            # Invalid format, use fallback
            current_executor = "chatter_agent"
            current_subtask = "Tell the user that you couldn't understand their request and ask them to rephrase it"
            tasks = [{"task": current_subtask, "executor": current_executor}]
    
    # Fallback for parsing failures or invalid format
    else:
        print("[Planner] Using fallback - ask for clarification")
        current_executor = "chatter_agent"
        current_subtask = "Tell the user that you couldn't understand their request and ask them to rephrase it"
        tasks = [{"task": current_subtask, "executor": current_executor}]

    return {
        "current_executor": current_executor,
        "current_subtask": current_subtask,
        "tasks": tasks
    }


# Decision function for planner routing
def planner_decision(state: AgentState) -> str:
    current_executor = state.get("current_executor", "exit")
    current_subtask = state.get("current_subtask", "done")
    
    if current_executor == "exit" or current_subtask == "done" or current_subtask == "no_op":
        return "exit"  # all subtasks complete
    elif current_executor == "chatter_agent":
        return "chatter_agent"
    elif current_executor == "tooler_agent":
        return "tooler_agent"
    elif current_executor == "coder_agent":
        return "coder_agent"
    else:
        return "tooler_agent" # fallback
