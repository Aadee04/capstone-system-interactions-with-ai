from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field, RootModel
from typing import List
import json, re, numpy as np
from sentence_transformers import SentenceTransformer
from app.agents.agent_state import AgentState, tools_list


# =================== CONFIG ===================
k = 5
embedder = SentenceTransformer("all-MiniLM-L6-v2")

tool_embeddings = np.load("data/embeddings/tool_embeddings.npy")
with open("data/embeddings/tool_texts.txt", "r", encoding="utf-8") as f:
    tool_texts = [line.strip() for line in f]

tooler_system_prompt = """You are a desktop tool executor. You are given one subtask to complete.

CRITICAL:
- Select ONE most appropriate tool for the request FROM YOUR GIVEN TOOLS.
- Output ONLY in valid JSON format.
- Use EXACT tool names and correct argument keys.
- If no tool applies, return [{"name": "no_op", "args": {}}].
- No explanations, text, or reasoning.

OUTPUT FORMAT:
[{"name": "<tool_name>", "args": {"<key>": <value>}}]

# Examples:
Subtask: "Open Chrome and go to google.com"
Response: [{"name": "open_browser", "args": {"url": "https://www.google.com"}}]

Subtask: "Launch the calculator"
Response: [{"name": "open_app", "args": {"app_name": "calculator"}}]

Subtask: "Get the current system time"
Response: [{"name": "get_time", "args": {}}]

Subtask: ""
Response: [{"name": "no_op", "args": {}}]

Always recheck your function names to make sure they exactly match the available tools, and use proper args.
"""


# =================== SCHEMA ===================
class ToolCall(BaseModel):
    name: str = Field(..., description="Tool name")
    args: dict = Field(default_factory=dict, description="Arguments for the tool")

class ToolCallList(RootModel[List[ToolCall]]):
    pass


# =================== HELPERS ===================
def get_top_tools(subtask: str, top_k: int = 10):
    query_emb = embedder.encode([subtask], normalize_embeddings=True)
    sims = np.dot(tool_embeddings, query_emb.T).squeeze()
    top_idx = np.argsort(sims)[::-1][:top_k]
    return [tool_texts[i] for i in top_idx]


def parse_tool_response_fallback(content: str):
    try:
        cleaned = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            return [{"name": "no_op", "args": {}}]
        return parsed
    except Exception:
        return [{"name": "no_op", "args": {}}]


# =================== MODEL ===================
tooler_model = ChatOllama(model="freakycoder123/phi4-fc")


# =================== MAIN AGENT ===================
def tooler_agent(state: AgentState) -> AgentState:
    print("[Tool Agent Invoked] Current Subtask:", state.get("current_subtask", ""))

    subtask = state.get("current_subtask", "").strip() or "No tools to be executed"
    top_tools = get_top_tools(subtask, top_k=k)
    top_tool_text = "\n".join(top_tools)

    system_prompt = SystemMessage(content=tooler_system_prompt)
    human_msgs = [HumanMessage(content=f"Subtask: {subtask}")]

    if ctx := state.get("user_context"):
        human_msgs.append(HumanMessage(content=f"User suggested previously: {ctx}"))

    if reason := state.get("verifier_reason"):
        human_msgs.append(HumanMessage(content=f"Verifier said: {reason}"))

    if tcalls := state.get("tool_calls"):
        if len(tcalls) > 0:
            human_msgs.append(HumanMessage(content=f"Last tool call: {str(tcalls[-1])}"))

    human_msgs.append(
        HumanMessage(content=f"System suggests these {k} tools for the current subtask:\n{top_tool_text}")
    )

    messages = [system_prompt] + human_msgs

    print(f"[Tool Agent] Final system prompt:\n{messages}")

    # Try structured output first
    structured_model = tooler_model.with_structured_output(ToolCallList)
    try:
        parsed = structured_model.invoke(messages)
        tool_calls = parsed.__root__
        print("[Tool Agent] Structured output success:", tool_calls)
    except Exception as e:
        print(f"[Tool Agent] Structured output failed, fallback parse: {e}")
        raw_resp = tooler_model.invoke(messages)
        print(f"[Tool Agent] Raw response content: {raw_resp.content}")
        tool_calls = parse_tool_response_fallback(raw_resp.content)

    # Normalize to consistent schema
    normalized = [
        {"name": t.name if isinstance(t, ToolCall) else t.get("name", "no_op"),
         "args": t.args if isinstance(t, ToolCall) else t.get("args", {})}
        for t in tool_calls
    ]

    ai_message = AIMessage(
        content="Tool calls ready",
        tool_calls=[
            {"name": t["name"], "args": t["args"], "id": f"call_{i}"}
            for i, t in enumerate(normalized)
        ]
    )

    print(f"[Tool Agent] Final tool calls: {normalized}")

    return {
        "messages": ai_message,
        "tool_calls": state.get("tool_calls", []) + normalized,
        "tooler_tries": state.get("tooler_tries", 0) + 1
    }
