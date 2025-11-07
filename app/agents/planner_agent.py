from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
import json
import sys
import os
import re

from app.agents.agent_state import AgentState, tool_list_with_desc_str


planner_system_prompt = """
You are a workflow planner, which is part of a multi-agent desktop system. 
Your task is to break down user requests into sequential subtasks and assign the appropriate agent for each.

You have three agents available, but you will primarily use tooler_agent for performing actions:
- chatter_agent: For conversational responses, greetings, and explanations. Cannot perform any actions.
- tooler_agent: For desktop actions, file operations, opening apps, system commands, and other actionable tasks
- coder_agent: For calculations, data processing, programming tasks, code execution

Only respond to the user's current query — the rest of the message history is just context.
Each subtask should be clear, specific, and actionable. Add context from previous subtasks only if needed.
All subtasks are fully automated — never ask for user input.
Subtasks do not need to wait for completion, just list them out.

OUTPUT FORMAT:
Return a JSON array where each task specifies its executor:
[
  {"task": "<description>", "executor": "tooler_agent"},
  {"task": "<description>", "executor": "coder_agent"},
  {"task": "<description>", "executor": "chatter_agent"}
]

CRITICAL RULES:
- "executor" field MUST be EXACTLY either "chatter_agent", "tooler_agent", OR "coder_agent"
- DEFAULT to tooler_agent for action requests, chatter_agent for conversational requests
- DO NOT specify tool names — the tooler agent will select the appropriate tool automatically
- If parameters are needed (like a URL), include them directly in the subtask string
- Keep subtasks descriptive but simple
- No need for "done" or completion markers - system handles task completion automatically
- Each subtask will be automatically verified and retried/escalated if needed
- Ensure that the next subtask is not supposed to be executed before the previous one

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

Request: "Unmute"
Response: [
  {"task": "Unmute the system volume", "executor": "tooler_agent"}
]"""


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


planner_model = ChatOllama(model="freakycoder123/phi4-fc", num_predict=350)
def planner_agent(state: AgentState) -> AgentState:
    print("[Enhanced Planner Agent Invoked]")  # DEBUGGING ---------------


    if state["subtask_index"] != 0: # Not the first run, just return current subtask
        subtask_index = state["subtask_index"]
        tasks = state.get("tasks", [])

        # Check if all tasks completed (index >= length)
        if subtask_index >= len(tasks):
            
            state["external_messages"].append({
                "agent": "Planner Agent", 
                "message": "All subtasks completed.",
                "type": "info"              
            })
            return {
                "current_executor": "exit",
                "current_subtask": "done",
                "subtask_index": subtask_index,
                'coder_tries': 0,
                "tooler_tries": 0
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

        state["external_messages"].append({
            "agent": "Planner Agent", 
            "message": f"Subtask {subtask_index}: {current_subtask} assigned to {current_executor}",
            "type": "info"              
        })

        return {
            "current_executor": current_executor,
            "current_subtask": current_subtask,
            "subtask_index": subtask_index,
            'coder_tries': 0,
            "tooler_tries": 0
        }

    
    # If it's the first run, generate tasks from user input
    user_message = state["messages"][-1].content if state.get("messages") else ""

    
    if user_message == "":
      print("[Planner] Empty user message, using fallback")
      current_executor = "chatter_agent"
      current_subtask = "Greet the user and ask them to provide a valid request"
      tasks = [{"task": current_subtask, "executor": current_executor}]

      state["external_messages"].append({
        "agent": "Planner Agent", 
        "message": tasks,
        "type": "info"              
      })

      return {
          "current_executor": current_executor,
          "current_subtask": current_subtask,
          "tasks": tasks,
          'coder_tries': 0,
          "tooler_tries": 0
      }
    
    full_prompt = planner_system_prompt + "\nUser Request: " + user_message
    final_system_prompt = HumanMessage(content=full_prompt)

    # Generate LLM Response
    response = planner_model.invoke([final_system_prompt])
    # print(f"[Planner] Raw response: {response.content}")  # DEBUGGING ---------------

    # Parse Response if in json format
    try:
        parsed = safe_json_parse(response.content)
    except Exception:
        parsed = None  # Will be handled by fallback below
    
    print(f"[Planner Tasks]: {parsed}")  # DEBUGGING ---------------
    
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
    
    # Handle single dict response (LLM returned single task without array wrapper)
    elif isinstance(parsed, dict) and "task" in parsed and "executor" in parsed:
        print("[Planner] Single task dict detected, converting to list format")
        tasks = [parsed]  # Wrap in list
        current_executor = parsed["executor"]
        current_subtask = parsed["task"]
    
    # Fallback for parsing failures or invalid format
    else:
        print("[Planner] Using fallback - ask for clarification")
        current_executor = "chatter_agent"
        current_subtask = "Tell the user that you couldn't understand their request and ask them to rephrase it"
        tasks = [{"task": current_subtask, "executor": current_executor}]

    state["external_messages"].append({
        "agent": "Planner Agent", 
        "message": tasks,
        "type": "info"              
    })

    return {
        "current_executor": current_executor,
        "current_subtask": current_subtask,
        "tasks": tasks,
        'coder_tries': 0,
        "tooler_tries": 0
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
        return "chatter_agent" # fallback
