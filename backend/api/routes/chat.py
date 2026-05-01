import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from backend.agents.graph import urban_graph
from backend.session_manager import (
    create_session,
    get_session,
    append_message,
    get_history,
    update_session_meta,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ── Request / Response Models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    language: str = "en"  # preferred UI language (does not restrict answer language)


class ChatResponse(BaseModel):
    session_id: str
    response: str
    agent_thoughts: list[str]
    active_laws: list[str]
    suppressed_laws: list[str]
    compliance_notes: list[str]
    calculation_result: dict | None


class NewSessionResponse(BaseModel):
    session_id: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/session", response_model=NewSessionResponse)
async def new_session():
    """Create a new conversation session."""
    session_id = await create_session()
    return NewSessionResponse(session_id=session_id)


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Main chat endpoint.
    - Creates a session if session_id is not provided.
    - Runs the LangGraph pipeline.
    - Persists the turn to SQLite.
    """
    # Ensure session exists
    if req.session_id:
        session = await get_session(req.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found. Create a new one.")
        session_id = req.session_id
    else:
        session_id = await create_session()

    # Fetch conversation history for context
    history = await get_history(session_id)

    # Build initial state
    initial_state = {
        "query": req.message,
        "session_id": session_id,
        "conversation_history": history,
        "language": req.language,
        "context_type": "general",
        "requires_calculation": False,
        "detected_topics": [],
        "retrieved_chunks": [],
        "active_laws": [],
        "suppressed_laws": [],
        "suppression_reasons": [],
        "calculation_result": None,
        "compliance_notes": [],
        "final_response": "",
        "agent_thoughts": [],
    }

    # Run LangGraph — run in thread to avoid blocking asyncio event loop
    final_state = await asyncio.get_event_loop().run_in_executor(
        None, urban_graph.invoke, initial_state
    )

    response_text = final_state.get("final_response", "")

    # Persist turn
    await append_message(session_id, "user", req.message)
    await append_message(session_id, "assistant", response_text)
    await update_session_meta(
        session_id,
        final_state.get("language", req.language),
        final_state.get("context_type", "general"),
    )

    return ChatResponse(
        session_id=session_id,
        response=response_text,
        agent_thoughts=final_state.get("agent_thoughts", []),
        active_laws=final_state.get("active_laws", []),
        suppressed_laws=final_state.get("suppressed_laws", []),
        compliance_notes=final_state.get("compliance_notes", []),
        calculation_result=final_state.get("calculation_result"),
    )


@router.get("/sessions")
async def list_sessions():
    """List all sessions ordered by most recently updated."""
    from backend.session_manager import list_sessions as _list_sessions
    return {"sessions": await _list_sessions()}


@router.get("/history/{session_id}")
async def get_session_history(session_id: str):
    """Get the full message history for a specific session."""
    from backend.session_manager import get_session as _get_session
    session = await _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session_id": session["session_id"], "history": session["history"]}


@router.delete("/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation history for a session."""
    from backend.session_manager import delete_session
    await delete_session(session_id)
    return {"message": "Session deleted."}
