from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
import json
from agents.agent_state import AgentState, tool_list_with_desc_str
import re

available_tools_str = "\n".join(
    f"{name}: {desc}" 
    for name, desc in tool_list_with_desc_str
    if name != "run_python"
)

planner_system_prompt = """
You are a workflow planner. Break down complex user requests into sequential subtasks.
Your output will be given to either a tooler agent (for desktop actions) or a coder agent (for calculations, data processing, or programming tasks).
Only respond to the last user message — the rest of the conversation is just context.
Each subtask should be clear, specific, and actionable. Add context from previous subtasks only if needed.
All subtasks are fully automated — never ask for user input.
Don't wait for tasks to complete, just list them out.

Available tools in tooler for context: """ + available_tools_str + """

Coder generates Python code using run_python tool.
If any request is purely conversational or vague, respond with a single subtask "done" and "exit" as current_executor.

IMPORTANT: You can now specify different executors for different subtasks using the enhanced format below.

Output format options:

1. SIMPLE FORMAT (all tasks use same executor):
{
  "tasks": ["<description of the subtask>", ...],
  "current_executor": "tooler_agent"
}

2. ENHANCED FORMAT (different executors per task):
{
  "tasks": [
    {"task": "<description>", "executor": "tooler_agent"},
    {"task": "<description>", "executor": "coder_agent"},
    ...
  ],
  "current_executor": "tooler_agent"
}

CRITICAL RULES:
- "current_executor" field MUST be EXACTLY either "tooler_agent" OR "coder_agent" (nothing else)
- Use "tooler_agent" for desktop actions (opening apps, browsers, files, system operations)
- Use "coder_agent" for calculations, data processing, programming tasks, or when tools are insufficient
- DEFAULT to tooler_agent unless the task explicitly requires coding/calculations
- DO NOT specify tool names — the tooler agent will select the appropriate tool automatically
- Always end the list with a final subtask "done"
- If parameters are needed (like a URL), include them directly in the subtask string.
- Keep subtasks descriptive but simple. Use enhanced format when mixing tool and code tasks.

Examples:

Request: "Open Chrome"
Response: {"tasks": ["Open Chrome browser", "done"], "current_executor": "tooler_agent"}

Request: "Calculate 5+3"
Response: {"tasks": ["Calculate sum of 5+3", "done"], "current_executor": "coder_agent"}

Request: "Open the file report.txt, and then open Chrome"
Response: {"tasks": ["Open the file report.txt", "Open Chrome browser", "done"], "current_executor": "tooler_agent"}

Request: "Open task manager using code, then calculate 12*7"
Response: {"tasks": ["Open task manager using code", "Calculate 12*7", "done"], "current_executor": "coder_agent"}

Request: "Hi, who are you?"
Response: {"tasks": ["done"], "current_executor": "exit"}

Request: "Hello, can you help me open my email?"
Response: {"tasks": ["Open default email", "done"], "current_executor": "tooler_agent"}

Request: "Do nothing"
Response: {"tasks": ["done"], "current_executor": "exit"}

Request: "Open Miniclip.com and Gmail.com in Chrome, then calculate the sum of 45 and 32"
Response: {
  "tasks": [
    {"task": "Open Chrome browser and go to https://www.miniclip.com", "executor": "tooler_agent"},
    {"task": "Open Chrome browser and go to https://mail.google.com", "executor": "tooler_agent"},
    {"task": "Calculate sum of 45 and 32", "executor": "coder_agent"},
    "done"
  ],
  "current_executor": "tooler_agent"
}

Request: "Search Google for cute cats"
Response: {"tasks": ["Open Chrome browser and go to https://www.google.com/search?q=cute+cats", "done"], "current_executor": "tooler_agent"}

Request: "Open calculator thrice"
Response: {"tasks": ["Open the calculator", "Open the calculator", "Open the calculator", "done"], "current_executor": "tooler_agent"}

Request: "Write Python code to print 'Hello World'"
Response: {"tasks": ["Write Python code that prints 'Hello World'", "done"], "current_executor": "coder_agent"}

Request: "Plot a bar chart comparing sales data of January and February"
Response: {"tasks": ["Write Python code to plot a bar chart comparing January and February sales data", "done"], "current_executor": "coder_agent"}

Request: "Find the average of [23, 45, 67, 89]"
Response: {"tasks": ["Write code to calculate the average of [23, 45, 67, 89]", "done"], "current_executor": "coder_agent"}

Request: "Open Chrome, go to YouTube, and then open Notepad"
Response: {"tasks": ["Open Chrome browser and go to https://www.youtube.com", "Open Notepad", "done"], "current_executor": "tooler_agent"}

Request: "Restart the computer"
Response: {"tasks": ["Restart the computer", "done"], "current_executor": "tooler_agent"}

Request: "Check today's date and create a new file named report_<date>.txt"
Response: {"tasks": ["Check current date", "Create a new file named report_<date>.txt", "done"], "current_executor": "tooler_agent"}

Request: "Explain what recursion is"
Response: {"tasks": ["done"], "current_executor": "exit"}

Request: "Generate a Python script that downloads an image from a URL"
Response: {"tasks": ["Write Python code to download an image from a given URL", "done"], "current_executor": "coder_agent"}

Request: "Search Wikipedia for Quantum Computing"
Response: {"tasks": ["Search Wikipedia for 'Quantum Computing'", "done"], "current_executor": "tooler_agent"}

Request: "Convert Celsius to Fahrenheit using Python"
Response: {"tasks": ["Write Python code to convert Celsius to Fahrenheit", "done"], "current_executor": "coder_agent"}

Request: "Open YouTube and play lo-fi beats"
Response: {"tasks": ["Open Chrome browser and go to https://www.youtube.com/results?search_query=lofi+beats", "done"], "current_executor": "tooler_agent"}

Request: "Good morning"
Response: {"tasks": ["done"], "current_executor": "exit"}

Request: "Check system time, then open calculator"
Response: {"tasks": ["Get current system time", "Open calculator", "done"], "current_executor": "tooler_agent"}

Request: "Open the Downloads folder and delete temp.txt"
Response: {"tasks": ["Open Downloads folder", "Delete file temp.txt", "done"], "current_executor": "tooler_agent"}

Request: "Write a Python function to sort a list in ascending order"
Response: {"tasks": ["Write Python function to sort a list in ascending order", "done"], "current_executor": "coder_agent"}

Request: "Ping google.com"
Response: {"tasks": ["Ping google.com", "done"], "current_executor": "tooler_agent"}

Request: "Create a folder named 'Projects' and move report.pdf into it"
Response: {"tasks": ["Create folder named 'Projects'", "Move report.pdf into 'Projects'", "done"], "current_executor": "tooler_agent"}

Request: "Open notepad, write a hello world program, and calculate 15*23"
Response: {
  "tasks": [
    {"task": "Open Notepad", "executor": "tooler_agent"},
    {"task": "Write hello world program in Python", "executor": "coder_agent"},
    {"task": "Calculate 15*23", "executor": "coder_agent"},
    "done"
  ],
  "current_executor": "tooler_agent"
}

Request: "Open task manager and kill any chrome processes"
Response: {"tasks": ["Open task manager", "Kill Chrome processes", "done"], "current_executor": "tooler_agent"}
"""


def categorize_task(task_description: str) -> str:
    """
    Determine if a task should use tooler or coder based on keywords.
    Returns 'tooler_agent' or 'coder_agent'.
    """
    task_lower = task_description.lower()
    
    # Explicit coding tasks
    coding_keywords = [
        "write code", "python code", "script", "program", "function",
        "calculate", "compute", "math", "sum", "multiply", "divide",
        "plot", "graph", "chart", "data processing", "algorithm",
        "factorial", "fibonacci", "sort", "average", "statistics"
    ]
    
    if any(keyword in task_lower for keyword in coding_keywords):
        return "coder_agent"
    
    # Everything else defaults to tooler (faster, with escalation fallback)
    return "tooler_agent"


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
    print("[Planner Agent Invoked]")  # DEBUGGING ---------------

    if state["subtask_index"] != 0: # Not the first run, just return current subtask
        subtask_index = state["subtask_index"]
        tasks = state.get("tasks", [])

        if subtask_index >= len(tasks) or (
            isinstance(tasks[subtask_index], str) and tasks[subtask_index] == "done"
        ) or (
            isinstance(tasks[subtask_index], dict) and tasks[subtask_index].get("task") == "done"
        ):
            return {
                "current_executor": "exit",
                "current_subtask": "done",
                "subtask_index": subtask_index
            }

        current_task = tasks[subtask_index]
        
        # Handle both simple string format and enhanced dict format
        if isinstance(current_task, dict):
            current_subtask = current_task.get("task", "done")
            current_executor = current_task.get("executor", "tooler_agent")
        else:
            current_subtask = current_task
            current_executor = state.get("current_executor", "tooler_agent")

        return {
            "current_executor": current_executor,
            "current_subtask": current_subtask,
            "subtask_index": subtask_index
        }

    # If it is the first run
    system_prompt = HumanMessage(content=planner_system_prompt)
    response = planner_model.invoke([system_prompt] + state["messages"])
    
    print(f"[Planner] Raw response: {response.content}")  # DEBUGGING ---------------

    try:
        parsed = safe_json_parse(response.content)
    except Exception:
        parsed = {"tasks": ["done"], "current_executor": "exit"}  # fallback
        print("[Planner]: json parsing failed") # DEBUGGING ---------------
    
    print(f"[Planner parsed]: {parsed}")  # DEBUGGING ---------------
    
    if isinstance(parsed, dict):
        tasks = parsed.get("tasks", ["done"])
        current_executor = parsed.get("current_executor", "tooler_agent")
        
        # Handle enhanced format with per-task executors
        if tasks and isinstance(tasks[0], dict) and "task" in tasks[0]:
            # Enhanced format: [{"task": "...", "executor": "..."}, ...]
            response.tasks = tasks
            # Use the executor of the first task, or fallback to default
            if "executor" in tasks[0]:
                response.current_executor = tasks[0]["executor"]
            else:
                response.current_executor = current_executor
            response.subtask = tasks[0].get("task", "done")
        else:
            # Simple format: ["task1", "task2", ...]
            response.tasks = tasks
            response.current_executor = current_executor
            response.subtask = tasks[0] if tasks else "done"
    elif isinstance(parsed, list):
        response.tasks = parsed
        response.current_executor = "tooler_agent"  # default for lists
        response.subtask = parsed[0] if parsed else "done"
    else:
        response.tasks = ["done"]
        response.current_executor = "exit"
        response.subtask = "done"

    return {
        "current_executor": response.current_executor,
        "current_subtask": response.subtask,
        "tasks": response.tasks
    }

# Decision function for planner routing
def planner_decision(state: AgentState) -> str:
    current_executor = state.get("current_executor", "exit")
    current_subtask = state.get("current_subtask", "done")
    
    if current_executor == "exit" or current_subtask == "done" or current_subtask == "no_op":
        return "exit"  # all subtasks complete
    elif current_executor == "tooler_agent":
        return "tooler_agent"
    elif current_executor == "coder_agent":
        return "coder_agent"
    else:
        return "tooler_agent" # fallback