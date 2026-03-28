"""REST API routes for the Swan Interaction Overlay."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from saa.sio.core.schemas import (
    ChatRequest,
    ChatResponse,
    InjectEventRequest,
    ReplayRequest,
    SessionConfig,
    SessionState,
    StateQueryResponse,
    StateSnapshot,
    TurnRecord,
)
from saa.sio.core.session import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Module-level session manager — all routes share this
session_manager = SessionManager(storage_dir="sessions")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/sessions")
async def create_session(config: SessionConfig | None = None) -> dict[str, str]:
    sid = session_manager.create_session(config)
    return {"session_id": sid}


@router.get("/sessions")
async def list_sessions() -> list[str]:
    return session_manager.list_sessions()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return session.model_dump()


@router.post("/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    if not request.session_id:
        # Auto-create session
        request.session_id = session_manager.create_session()

    session = session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    turn = session_manager.process_input(request.session_id, request.text)

    # Broadcast via WebSocket
    try:
        from saa.sio.api.websocket import manager as ws_manager
        snapshot = session_manager.get_state(request.session_id)
        if snapshot:
            await ws_manager.broadcast(request.session_id, {
                "type": "state_update",
                "snapshot": snapshot.model_dump(),
            })
    except Exception:
        pass  # WebSocket broadcast is best-effort

    return ChatResponse(
        response_text=turn.response_text,
        turn_id=turn.turn_id,
        tick=turn.tick,
        action_intent=turn.action_intent,
        state_snapshot=turn.state_after,
        state_diffs=turn.state_diffs,
    ).model_dump()


@router.get("/state/{session_id}")
async def get_state(session_id: str) -> dict[str, Any]:
    snapshot = session_manager.get_state(session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Session not found")

    bundle = session_manager._sessions.get(session_id)
    memory_summary = {}
    relationships = {}
    conflicts: list[dict] = []
    modulators: dict[str, float] = {}
    if bundle:
        adapter = bundle[1]
        memory_summary = adapter.get_memory_snapshot()
        relationships = adapter.get_relationship_graph()
        conflicts = adapter.get_active_conflicts()
        modulators = adapter.get_modulation_state()

    return StateQueryResponse(
        snapshot=snapshot,
        memory_summary=memory_summary,
        relationship_graph=relationships,
        active_conflicts=conflicts,
        modulation_state=modulators,
    ).model_dump()


@router.post("/inject/{session_id}")
async def inject_event(session_id: str, request: InjectEventRequest) -> dict[str, Any]:
    snapshot = session_manager.inject_event(session_id, request.event_type, request.data)

    try:
        from saa.sio.api.websocket import manager as ws_manager
        await ws_manager.broadcast(session_id, {
            "type": "state_update",
            "snapshot": snapshot.model_dump(),
        })
    except Exception:
        pass

    return snapshot.model_dump()


@router.get("/history/{session_id}")
async def get_history(session_id: str) -> list[dict[str, Any]]:
    history = session_manager.get_history(session_id)
    return [t.model_dump() for t in history]


@router.post("/checkpoint/{session_id}")
async def create_checkpoint(session_id: str) -> dict[str, int]:
    tick = session_manager.create_checkpoint(session_id)
    return {"tick": tick}


@router.post("/replay")
async def replay(request: ReplayRequest) -> dict[str, str]:
    new_id = session_manager.replay_from(request.session_id, request.from_turn)
    return {"new_session_id": new_id}


@router.get("/rationale/{session_id}")
async def get_rationale(session_id: str) -> dict[str, Any]:
    bundle = session_manager._sessions.get(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Session not found")
    adapter = bundle[1]
    return adapter.get_rationale_trace()


@router.get("/relationships/{session_id}")
async def get_relationships(session_id: str) -> dict[str, Any]:
    bundle = session_manager._sessions.get(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return bundle[1].get_relationship_graph()


@router.get("/memory/{session_id}")
async def get_memory(session_id: str) -> dict[str, Any]:
    bundle = session_manager._sessions.get(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return bundle[1].get_memory_snapshot()


@router.get("/modulators/{session_id}")
async def get_modulators(session_id: str) -> dict[str, float]:
    bundle = session_manager._sessions.get(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return bundle[1].get_modulation_state()


@router.get("/conflicts/{session_id}")
async def get_conflicts(session_id: str) -> list[dict[str, Any]]:
    bundle = session_manager._sessions.get(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return bundle[1].get_active_conflicts()
