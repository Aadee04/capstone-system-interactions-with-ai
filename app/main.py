from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.agent import app as agent_app, create_initial_state
from app.modules.embeddings.embeddings_generator import generate_tool_embeddings
from langchain_core.messages import HumanMessage
import threading
import uvicorn
import time

# -------------------- FastAPI Setup -------------------- #

api = FastAPI(title="LoLLM Backend")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"] if you want restricted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Routes -------------------- #

@api.get("/")
def root():
    return {"message": "Backend running successfully!"}

@api.post("/query")
async def query_agent(request: dict):
    """Receive text input from frontend (after STT), pass to agent, return response."""
    user_input = request.get("input", "")
    print(f"[Backend] Received query: {user_input}")

    # Create initial state for agent
    state = create_initial_state()
    state["messages"] = [HumanMessage(content=user_input)]

    # Run agent
    result = agent_app.invoke(state)
    output = result["messages"][-1].content if result.get("messages") else "No response."

    print(f"[Backend] Agent response: {output}")
    return {"response": output}


# -------------------- Startup Embeddings -------------------- #

@api.get("/startup")
def run_embeddings():
    try:
        print("[Startup] Generating embeddings...")
        generate_tool_embeddings()
        print("[Startup] Embeddings generated successfully.")
        return "[Startup] Embeddings generated successfully."
    except Exception as e:
        print(f"[Startup] Failed to generate embeddings: {e}")
        return f"[Startup] Failed to generate embeddings: {e}"

# -------------------- Main -------------------- #

if __name__ == "__main__":
    # Run embeddings generation in background on startup
    threading.Thread(target=run_embeddings, daemon=True).start()

    # Wait a moment before starting backend
    time.sleep(2)
    print("[System] Starting FastAPI backend...")
    uvicorn.run(api, host="0.0.0.0", port=8000)
