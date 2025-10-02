from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from prompts.system_prompts import chatter_system_prompt
from agents.agent_state import AgentState

chat_model = ChatOllama(model="freakycoder123/phi4-fc")
def chat_agent(state: AgentState) -> AgentState:
    print("[Chat Agent Invoked]")  # DEBUGGING ---------------
    system_prompt = SystemMessage(
        content=(chatter_system_prompt))
    response = chat_model.invoke([system_prompt] + state["messages"])
    return {"messages": state["messages"] + [response]}