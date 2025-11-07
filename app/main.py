# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from app.agent import app as agent_app, create_initial_state
from app.modules.embeddings.embeddings_generator import generate_tool_embeddings
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
import threading, uvicorn, time, json
from pydantic import BaseModel 
import json
from uuid import uuid4
from copy import deepcopy

# Simple in-memory snapshot store for paused agent states
SNAPSHOT_STORE: dict[str, dict] = {}
SNAPSHOT_TTL = 300  # seconds

# Type hints for request bodies
class QueryRequest(BaseModel):
    input: str

class ContinueRequest(BaseModel):
    decision: str
    context: str | None = None
    thread_id: str

app = FastAPI(title="LoLLM Assistant Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Backend running successfully!"
    }


@app.post("/query")
async def query_agent(request: QueryRequest):
    """Handle main agent interaction from frontend"""
    user_input = request.input.strip()
    print(f"[Backend] Received query: {user_input}")

    # Create unique thread_id for this conversation
    thread_id = str(uuid4())
    print(f"[Backend] Created thread_id: {thread_id}")

    # Create initial agent state
    state = create_initial_state()
    state["messages"] = [HumanMessage(content=user_input)]
    state["user_query"] = user_input

    # Config with thread_id enables checkpointing
    config = {
        "configurable": {
            "thread_id": thread_id,
            "recursion_limit": 200
        }
    }

    async def event_stream():
        try:
            async for step in agent_app.astream(state, config):
                print("[Backend stream step]:", step.keys())
            
                # Handle interrupts first
                if "__interrupt__" in step:
                    interrupt_obj = step["__interrupt__"]  # this is Interrupt, don't send directly

                    # Build a JSON-serializable dict
                    interrupt_payload = {
                        "type": "user_verifier",
                        "thread_id": thread_id
                    }

                    print("[Backend sending interrupt]:", interrupt_payload)
                    yield f"data: {json.dumps(interrupt_payload)}\n\n"
                    break

                # --- Collect external messages ---
                external_msgs = []
                if "external_messages" in step:
                    external_msgs.extend(step["external_messages"])
                else:
                    for node_name, node_state in step.items():
                        if isinstance(node_state, dict) and "external_messages" in node_state:
                            external_msgs.extend(node_state["external_messages"])

                for msg in external_msgs:
                    print("[Backend sending external message]:", msg)
                    yield f"data: {json.dumps(msg)}\n\n"

                # --- Detect awaiting_user_verification anywhere in the graph ---
                awaiting_flag = False
                for node_name, node_state in step.items():
                    if isinstance(node_state, dict) and node_state.get("awaiting_user_verification"):
                        awaiting_flag = True
                        break

                if awaiting_flag:
                    print(f"[Backend] Paused for user verification, thread_id={thread_id}")
                    # Send thread_id to frontend (lightweight, persisted in checkpointer)
                    yield f"data: {json.dumps({'status': 'awaiting_user', 'thread_id': thread_id})}\n\n"
                    break

        except Exception as e:
            print("[Backend stream error]:", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

 
@app.post("/continue")
async def continue_agent(request: ContinueRequest):
    """Continue the agent after a user_verifier pause."""
    decision = request.decision.strip().lower()
    context = getattr(request, "context", "") or ""
    thread_id = request.thread_id
    print(f"[Continue] Received decision: {decision}, context: {context}, thread_id: {thread_id}")

    if not thread_id:
        return JSONResponse({"error": "Missing thread_id"}, status_code=400)

    config = {
        "configurable": {
            "thread_id": thread_id,
            "recursion_limit": 200
        }
    }

    try:
        # Create resume command with user's decision
        resume_command = Command(
            resume={
                "user_verifier_decision": decision,
                "user_context": context,
                "awaiting_user_verification": False
            }
        )

        print(f"[Continue] Created resume command: {resume_command}")

        async def event_stream():
            try:
                # Resume from checkpoint with user's input
                async for step in agent_app.astream(
                    resume_command,  # Pass command instead of None
                    config=config
                ):
                    print("[Continue stream step]:", step.keys())

                    # Aggregate external messages (global + nested)
                    external_msgs = []
                    if "external_messages" in step:
                        external_msgs.extend(step["external_messages"])
                    else:
                        for node_name, node_state in step.items():
                            if isinstance(node_state, dict) and "external_messages" in node_state:
                                external_msgs.extend(node_state["external_messages"])

                    # Send external messages to frontend
                    for msg in external_msgs:
                        print("[Continue sending external message]:", msg)
                        yield f"data: {json.dumps(msg)}\n\n"

                    # Check if it pauses again for verification
                    awaiting_flag = False
                    for node_name, node_state in step.items():
                        if isinstance(node_state, dict) and node_state.get("awaiting_user_verification"):
                            awaiting_flag = True
                            break

                    if awaiting_flag:
                        print(f"[Continue] Paused again for verification, thread_id={thread_id}")
                        yield f"data: {json.dumps({'status': 'awaiting_user', 'thread_id': thread_id})}\n\n"
                        break

            except Exception as e:
                print("[Continue stream error]:", e)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    except Exception as e:
        print(f"[Continue] Error retrieving/updating state: {e}")
        return JSONResponse({"error": f"Failed to resume: {str(e)}"}, status_code=500)


@app.get("/startup")
def run_embeddings():
    try:
        print("[Startup] Generating embeddings...")
        generate_tool_embeddings()
        print("[Startup] Embeddings generated successfully.")
        return {"status": "success"}
    except Exception as e:
        print(f"[Startup] Failed to generate embeddings: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    threading.Thread(target=run_embeddings, daemon=True).start()
    time.sleep(2)
    print("[System] Starting FastAPI backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
