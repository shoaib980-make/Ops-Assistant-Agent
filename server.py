"""
FastAPI Server & Web API for Ops Assistant Agent
------------------------------------------------
Provides:
- POST /api/chat: Processes user messages via LangGraph agent.
- POST /api/approve: Handles Human-in-the-Loop approval/rejection.
- GET /: Serves modern Web UI frontend.
"""

import uuid
from typing import Optional
from pathlib import Path
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from ops_graph import build_ops_graph
from guardrails import validate_user_input

app = FastAPI(title="Ops Assistant Agent Web API")

# Shared graph instance with MemorySaver checkpointer
GRAPH = build_ops_graph()


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool
    feedback: Optional[str] = ""


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    thread_id = req.thread_id or f"web-session-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    # 1. Input Guardrail
    is_safe, msg = validate_user_input(req.message)
    if not is_safe:
        return {
            "status": "GUARDRAIL_BLOCKED",
            "reply": msg,
            "thread_id": thread_id,
        }

    # 2. Invoke Graph
    input_data = {
        "messages": [HumanMessage(content=req.message)],
        "step_count": 0,
        "pending_email": None,
        "email_status": None,
    }

    result = GRAPH.invoke(input_data, config=config)
    state = GRAPH.get_state(config)

    # 3. Check for Human-in-the-Loop Interrupt
    if state.next and "human_approval" in state.next:
        interrupts = result.get("__interrupt__", [])
        interrupt_info = interrupts[0].value if interrupts else {}
        return {
            "status": "APPROVAL_REQUIRED",
            "interrupt_data": interrupt_info,
            "thread_id": thread_id,
        }

    # 4. Completed turn
    final_message = result["messages"][-1]
    return {
        "status": "COMPLETED",
        "reply": final_message.content,
        "thread_id": thread_id,
    }


@app.post("/api/approve")
async def approval_endpoint(req: ApprovalRequest):
    config = {"configurable": {"thread_id": req.thread_id}}

    state = GRAPH.get_state(config)
    if not state.next:
        raise HTTPException(status_code=400, detail="No pending checkpoint for this thread.")

    review_data = {
        "approved": req.approved,
        "feedback": req.feedback or ("Approved by operator." if req.approved else "Rejected by operator.")
    }

    result = GRAPH.invoke(Command(resume=review_data), config=config)
    final_message = result["messages"][-1]

    return {
        "status": "COMPLETED",
        "reply": final_message.content,
        "thread_id": req.thread_id,
    }


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = Path(__file__).parent / "static" / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Web UI static files not found.</h1>", status_code=404)
    return HTMLResponse(index_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    print("\nStarting Ops Assistant Agent Web Server at http://127.0.0.1:8000 ...\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)

