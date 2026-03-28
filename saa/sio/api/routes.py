"""REST API routes for the Swan Interaction Overlay."""

from __future__ import annotations

import copy
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from saa.core.engine import SimulationEngine
from saa.core.types import Event
from saa.sio.core.mediator import ConversationalMediator
from saa.sio.core.schemas import (
    ActionIntent,
    ChatRequest,
    ChatResponse,
    InjectEventRequest,
    ReplayRequest,
    SessionConfig,
    SessionState,
    StateDiff,
    StateQueryResponse,
    StateSnapshot,
    TurnRecord,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Session manager — lightweight in-process session store
# ---------------------------------------------------------------------------

class SessionManager:
    """Manages multiple SIO sessions, each backed by a :class:`SimulationEngine`."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._engines: dict[str, SimulationEngine] = {}
        self._mediator = ConversationalMediator()

    # -- helpers ----------------------------------------------------------

    def _require_session(self, session_id: str) -> SessionState:
        session = self._sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
        return session

    def _snapshot_from_engine(self, engine: SimulationEngine) -> StateSnapshot:
        """Build a :class:`StateSnapshot` from the current engine state."""
        raw = engine.save_state()

        # Extract values from module states where available.
        embodiment = raw.get("embodiment", {})
        interoception = raw.get("interoception", {})
        homeostasis = raw.get("homeostasis", {})
        neuromod = raw.get("neuromodulation", {})
        self_model = raw.get("self_model", {})
        memory = raw.get("memory", {})
        valuation = raw.get("valuation", {})
        social = raw.get("social", {})

        modulators: dict[str, float] = {}
        if isinstance(neuromod.get("levels"), dict):
            modulators = {k: float(v) for k, v in neuromod["levels"].items()}

        relationships: dict[str, dict[str, Any]] = {}
        if isinstance(social.get("relationships"), dict):
            relationships = social["relationships"]

        active_conflicts: list[dict[str, Any]] = []
        if isinstance(valuation.get("conflicts"), list):
            active_conflicts = valuation["conflicts"]

        values: dict[str, float] = {}
        if isinstance(valuation.get("value_weights"), dict):
            values = {k: float(v) for k, v in valuation["value_weights"].items()}

        return StateSnapshot(
            tick=engine.tick,
            energy=float(embodiment.get("energy", 1.0)),
            temperature=float(interoception.get("temperature", 0.5)),
            strain=float(interoception.get("strain", 0.0)),
            damage=float(embodiment.get("damage", 0.0)),
            memory_integrity=float(memory.get("integrity", 1.0)),
            resource_level=float(embodiment.get("resources", 1.0)),
            viability=float(self_model.get("viability", 1.0)),
            continuity_score=float(self_model.get("continuity", 1.0)),
            modulators=modulators,
            interoceptive_channels=interoception,
            homeostatic_errors=homeostasis,
            values=values,
            relationships=relationships,
            active_conflicts=active_conflicts,
        )

    @staticmethod
    def _compute_diffs(before: StateSnapshot, after: StateSnapshot) -> list[StateDiff]:
        """Compare two snapshots and return a list of diffs for scalar fields."""
        diffs: list[StateDiff] = []
        scalar_fields = [
            "energy", "temperature", "strain", "damage",
            "memory_integrity", "resource_level", "viability", "continuity_score",
        ]
        for field in scalar_fields:
            prev = getattr(before, field)
            curr = getattr(after, field)
            if prev != curr:
                diffs.append(StateDiff(
                    field=field,
                    previous=prev,
                    current=curr,
                    delta=round(curr - prev, 6),
                ))
        return diffs

    # -- public API -------------------------------------------------------

    def create_session(self, config: SessionConfig | None = None) -> str:
        config = config or SessionConfig()
        session_id = config.session_id or str(uuid.uuid4())
        config.session_id = session_id

        engine = SimulationEngine(agent_id=session_id)
        engine.initialize_modules(config.module_configs or None)

        session = SessionState(session_id=session_id, config=config)
        self._sessions[session_id] = session
        self._engines[session_id] = engine
        logger.info("Created session %s", session_id)
        return session_id

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())

    def get_session(self, session_id: str) -> SessionState:
        return self._require_session(session_id)

    def get_state(self, session_id: str) -> StateSnapshot | None:
        engine = self._engines.get(session_id)
        if engine is None:
            return None
        return self._snapshot_from_engine(engine)

    def process_input(self, session_id: str, text: str) -> ChatResponse:
        session = self._require_session(session_id)
        engine = self._engines[session_id]

        interaction = self._mediator.parse(text)
        state_before = self._snapshot_from_engine(engine)

        # Inject user text as an environment event, then step the engine.
        engine.event_bus.publish(Event(
            tick=engine.tick,
            source_module="sio",
            event_type="user_input",
            data={"text": text, "interaction": interaction.model_dump()},
        ))
        ctx = engine.step()

        state_after = self._snapshot_from_engine(engine)
        diffs = self._compute_diffs(state_before, state_after)

        # Build action intent from the action module result.
        action_data = ctx.action_result or {}
        action_intent = ActionIntent(
            action_type=action_data.get("action_type", interaction.intent),
            score=float(action_data.get("score", 0.0)),
            conflict=bool(action_data.get("conflict", False)),
            rationale=action_data.get("rationale", []),
            competing_actions=action_data.get("competing_actions", []),
            internal_influences=action_data.get("internal_influences", {}),
        )

        # Build a simple response text (scaffold — future LLM layer replaces this).
        response_text = (
            f"[{action_intent.action_type}] Acknowledged input "
            f"(tick {engine.tick}, intent={interaction.intent})."
        )

        turn = TurnRecord(
            turn_id=len(session.turns),
            tick=engine.tick,
            user_input=text,
            interaction_object=interaction,
            state_before=state_before,
            state_after=state_after,
            state_diffs=diffs,
            action_intent=action_intent,
            response_text=response_text,
            events_emitted=[e.model_dump() for e in ctx.events],
        )
        session.turns.append(turn)
        session.current_tick = engine.tick

        return ChatResponse(
            response_text=response_text,
            turn_id=turn.turn_id,
            tick=engine.tick,
            action_intent=action_intent,
            state_snapshot=state_after,
            state_diffs=diffs,
        )

    def inject_event(self, session_id: str, event_type: str, data: dict[str, Any]) -> StateSnapshot:
        self._require_session(session_id)
        engine = self._engines[session_id]

        engine.event_bus.publish(Event(
            tick=engine.tick,
            source_module="sio_inject",
            event_type=event_type,
            data=data,
        ))
        engine.step()
        return self._snapshot_from_engine(engine)

    def get_history(self, session_id: str) -> list[TurnRecord]:
        session = self._require_session(session_id)
        return session.turns

    def create_checkpoint(self, session_id: str) -> int:
        session = self._require_session(session_id)
        engine = self._engines[session_id]
        tick = engine.tick
        session.checkpoints[tick] = engine.save_state()
        return tick

    def replay(self, request: ReplayRequest) -> str:
        """Replay turns from an existing session, optionally creating a branch."""
        session = self._require_session(request.session_id)
        engine = self._engines[request.session_id]

        new_id = request.new_session_id or str(uuid.uuid4())
        new_config = session.config.model_copy(update={"session_id": new_id})
        self.create_session(new_config)

        to_turn = request.to_turn if request.to_turn is not None else len(session.turns)
        for turn in session.turns[request.from_turn:to_turn]:
            self.process_input(new_id, turn.user_input)

        return new_id

    def get_rationale(self, session_id: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        if not session.turns:
            return {}
        return session.turns[-1].rationale_trace

    def get_relationships(self, session_id: str) -> dict[str, dict[str, Any]]:
        snapshot = self.get_state(session_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return snapshot.relationships

    def get_memory(self, session_id: str) -> dict[str, Any]:
        engine = self._engines.get(session_id)
        if engine is None:
            raise HTTPException(status_code=404, detail="Session not found")
        raw = engine.save_state()
        return raw.get("memory", {})

    def get_modulators(self, session_id: str) -> dict[str, float]:
        snapshot = self.get_state(session_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return snapshot.modulators

    def get_conflicts(self, session_id: str) -> list[dict[str, Any]]:
        snapshot = self.get_state(session_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return snapshot.active_conflicts


# ---------------------------------------------------------------------------
# Module-level instance
# ---------------------------------------------------------------------------

session_manager = SessionManager()


# ---------------------------------------------------------------------------
# Route definitions
# ---------------------------------------------------------------------------

@router.post("/sessions")
async def create_session(config: SessionConfig | None = None) -> dict[str, str]:
    sid = session_manager.create_session(config)
    return {"session_id": sid}


@router.get("/sessions")
async def list_sessions() -> list[str]:
    return session_manager.list_sessions()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> SessionState:
    return session_manager.get_session(session_id)


@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    response = session_manager.process_input(request.session_id, request.text)

    # Broadcast updated state to WebSocket clients.
    from saa.sio.api.websocket import manager as ws_manager  # noqa: WPS433

    snapshot = session_manager.get_state(request.session_id)
    if snapshot is not None:
        await ws_manager.broadcast(request.session_id, snapshot.model_dump())

    return response


@router.get("/state/{session_id}")
async def get_state(session_id: str) -> StateQueryResponse:
    snapshot = session_manager.get_state(session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Session not found")
    memory = session_manager.get_memory(session_id)
    return StateQueryResponse(
        snapshot=snapshot,
        memory_summary=memory,
        relationship_graph=snapshot.relationships,
        active_conflicts=snapshot.active_conflicts,
        modulation_state=snapshot.modulators,
    )


@router.post("/inject/{session_id}")
async def inject_event(session_id: str, request: InjectEventRequest) -> StateSnapshot:
    snapshot = session_manager.inject_event(session_id, request.event_type, request.data)

    from saa.sio.api.websocket import manager as ws_manager  # noqa: WPS433
    await ws_manager.broadcast(session_id, snapshot.model_dump())

    return snapshot


@router.get("/history/{session_id}")
async def get_history(session_id: str) -> list[TurnRecord]:
    return session_manager.get_history(session_id)


@router.post("/checkpoint/{session_id}")
async def create_checkpoint(session_id: str) -> dict[str, int]:
    tick = session_manager.create_checkpoint(session_id)
    return {"tick": tick}


@router.post("/replay")
async def replay(request: ReplayRequest) -> dict[str, str]:
    new_id = session_manager.replay(request)
    return {"new_session_id": new_id}


@router.get("/rationale/{session_id}")
async def get_rationale(session_id: str) -> dict[str, Any]:
    return session_manager.get_rationale(session_id)


@router.get("/relationships/{session_id}")
async def get_relationships(session_id: str) -> dict[str, dict[str, Any]]:
    return session_manager.get_relationships(session_id)


@router.get("/memory/{session_id}")
async def get_memory(session_id: str) -> dict[str, Any]:
    return session_manager.get_memory(session_id)


@router.get("/modulators/{session_id}")
async def get_modulators(session_id: str) -> dict[str, float]:
    return session_manager.get_modulators(session_id)


@router.get("/conflicts/{session_id}")
async def get_conflicts(session_id: str) -> list[dict[str, Any]]:
    return session_manager.get_conflicts(session_id)
