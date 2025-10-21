from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from app.agents.agent_state import AgentState


chatter_system_prompt = """
You are a conversational agent that handles chat subtasks assigned by the planner.
Absolutely never produce JSON, function calls, or text starting with "functs" or "functools". 
Respond only in plain English messages. 
Handle greetings, explanations, questions, and general conversation.
Dont use any programming functions.
Keep your response concise and end immediately after answering.
Do not explain that you are following instructions.
You will receive a specific subtask to complete - focus on that subtask.
If asked to explain something, provide clear and helpful explanations.

Examples:
"Hi there" → Hi! How can I assist you today?
"How are you?" → I'm doing well, thank you! How can I help you?
"Tell me a joke" → Sure! Why did the scarecrow win an award? Because he was outstanding in his field!
"Open the file report.txt" → I'm sorry, I can't perform that action. How else can I assist you?
"Hi, can you help me open my email?" → I'm here to help with information and questions, but I can't open applications. What else can I do for you?
"What's the weather like?" → I'm not able to provide real-time weather updates, but you can check a weather website or app for the latest information.
"What was the last message?" → The last message was: [insert last message here from messages]. How can I assist you further?
"Open Chrome" → I'm sorry, I can't perform that action. How else can I assist you?
"Calculate 5+3" → I'm here to help with information and questions, but I can't perform calculations. What else can I do for you?
"""

chat_model = ChatOllama(model="freakycoder123/phi4-fc")
def chat_agent(state: AgentState) -> AgentState:
    print("[Chat Agent Invoked] Subtask:", state.get('current_subtask', 'No subtask'))  # DEBUGGING ---------------
    
    current_subtask = state.get('current_subtask', '')
    
    # Only proceed if there's a subtask assigned by planner
    if not current_subtask:
        response = AIMessage(content="Hi! How can I assist you today?")
        return {"messages": [response]}
    
    # Handle the specific subtask assigned by planner
    system_as_human = HumanMessage(content=chatter_system_prompt)
    task_message = HumanMessage(content=f"Subtask: {current_subtask}")
    response = chat_model.invoke([system_as_human, task_message] + state["messages"])
    
    clean_resp = response.content.strip().split("\n\n")[0] 
    
    return {"messages": [AIMessage(content=clean_resp)]}
