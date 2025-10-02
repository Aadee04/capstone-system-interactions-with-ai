from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from agents.agent_state import AgentState


chatter_system_prompt = """
Absolutely never produce JSON, function calls, or text starting with "functs" or "functools". 
Respond only in plain English messages. 
If the input is empty, greet the user.
Dont use any programming functions.
Keep your response concise and end immediately after answering.
Do not explain that you are following instructions.
You must only respond to the last user message, rest of the conversation is context.

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
    print("[Chat Agent Invoked]")  # DEBUGGING ---------------

    if not state["messages"][-1].content.strip():
        response = AIMessage(content="Hi! How can I assist you today?")
        return {"messages": state["messages"] + [response]}
    
    system_as_human  = HumanMessage(content=(chatter_system_prompt))
    
    response = chat_model.invoke([system_as_human ] + state["messages"])

    clean_resp = response.content.strip().split("\n\n")[0]

    
    return {"messages": state["messages"] + [AIMessage(content=clean_resp)]}
