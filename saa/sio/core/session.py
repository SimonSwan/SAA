"""Session Manager — manages SIO sessions with persistence, checkpointing,
replay, and branching.

Each session wraps a full SwanCoreAdapter, ConversationalMediator, and
LanguageRenderer.  Turn history, checkpoints, and configuration are stored
in a :class:`SessionState` that can be serialized to / from JSON on disk.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from saa.sio.core.schemas import (
    SessionConfig,
    SessionState,
    TurnRecord,
    StateSnapshot,
    InteractionObject,
    ActionIntent,
    StateDiff,
)
from saa.sio.core.adapter import SwanCoreAdapter
from saa.sio.core.mediator import ConversationalMediator
from saa.sio.core.renderer import LanguageRenderer


# Type alias for the per-session tuple stored in memory.
_SessionBundle = tuple[SessionState, SwanCoreAdapter, ConversationalMediator, LanguageRenderer]


class SessionManager:
    """Creates, drives, and persists SIO sessions.

    The manager keeps a dict of active sessions mapping *session_id* to a
    bundle of ``(SessionState, SwanCoreAdapter, ConversationalMediator,
    LanguageRenderer)``.
    """

    def __init__(self, storage_dir: str = "sessions") -> None:
        self._storage_dir = Path(storage_dir)
        self._sessions: dict[str, _SessionBundle] = {}

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, config: SessionConfig | None = None) -> str:
        """Create a new session, initialize the adapter, and return the
        *session_id*.
        """
        if config is None:
            config = SessionConfig()

        session_id = config.session_id or str(uuid.uuid4())
        config.session_id = session_id

        # Build the adapter and initialize modules
        adapter = SwanCoreAdapter(seed=config.seed)
        adapter.initialize(
            {"module_configs": config.module_configs} if config.module_configs else None
        )

        mediator = ConversationalMediator()
        renderer = LanguageRenderer()

        state = SessionState(
            session_id=session_id,
            config=config,
            module_versions=adapter.get_module_versions(),
        )

        self._sessions[session_id] = (state, adapter, mediator, renderer)
        return session_id

    def get_session(self, session_id: str) -> SessionState | None:
        """Return the :class:`SessionState` for a session, or ``None``."""
        bundle = self._sessions.get(session_id)
        if bundle is None:
            return None
        return bundle[0]

    # ------------------------------------------------------------------
    # Input processing — full pipeline
    # ------------------------------------------------------------------

    def process_input(self, session_id: str, text: str) -> TurnRecord:
        """Run the full SIO pipeline for a single user input.

        Steps:
        1. Mediator parses text into an InteractionObject.
        2. Capture state snapshot *before*.
        3. Adapter processes the interaction (one engine tick).
        4. Capture state snapshot *after*.
        5. Compute state diffs.
        6. Renderer produces a response string.
        7. Build and store a TurnRecord.
        """
        state, adapter, mediator, renderer = self._get_bundle(session_id)

        # 1. Parse
        interaction: InteractionObject = mediator.parse(text)

        # 2. Snapshot before
        state_before: StateSnapshot = adapter.get_state_snapshot()

        # 3. Process interaction through the engine
        context, action_intent = adapter.process_interaction(interaction)

        # 4. Snapshot after
        state_after: StateSnapshot = adapter.get_state_snapshot()

        # 5. Compute diffs
        state_diffs: list[StateDiff] = adapter.compute_state_diff(
            state_before, state_after
        )

        # 6. Render response
        response_text: str = renderer.render(
            action_intent=action_intent,
            state=state_after,
            interaction_text=text,
        )

        # 7. Build TurnRecord
        turn_id = len(state.turns)
        tick = state_after.tick

        # Collect auxiliary data
        memory_snapshot = adapter.get_memory_snapshot()
        relationship_graph = adapter.get_relationship_graph()
        rationale_trace = adapter.get_rationale_trace()

        # Build memory / relationship update lists from diffs
        memory_updates: list[dict[str, Any]] = []
        if memory_snapshot.get("last_encoded_tick") == tick:
            memory_updates.append({
                "type": "episode_encoded",
                "tick": tick,
                "episodic_count": memory_snapshot.get("episodic_count", 0),
            })

        relationship_updates: list[dict[str, Any]] = [
            {"agent": agent, **data}
            for agent, data in relationship_graph.items()
        ]

        # Events emitted this tick
        events_emitted: list[dict[str, Any]] = [
            {
                "event_type": e.event_type,
                "source_module": e.source_module,
                "severity": e.severity,
                "data": e.data,
            }
            for e in context.events
        ]

        turn = TurnRecord(
            turn_id=turn_id,
            tick=tick,
            user_input=text,
            interaction_object=interaction,
            state_before=state_before,
            state_after=state_after,
            state_diffs=state_diffs,
            action_intent=action_intent,
            response_text=response_text,
            memory_updates=memory_updates,
            relationship_updates=relationship_updates,
            events_emitted=events_emitted,
            rationale_trace=rationale_trace,
        )

        # Store
        state.turns.append(turn)
        state.current_tick = tick

        return turn

    # ------------------------------------------------------------------
    # Event injection
    # ------------------------------------------------------------------

    def inject_event(
        self, session_id: str, event_type: str, data: dict
    ) -> StateSnapshot:
        """Inject an arbitrary event and return the current state snapshot."""
        _state, adapter, _mediator, _renderer = self._get_bundle(session_id)
        adapter.inject_event(event_type, data)
        return adapter.get_state_snapshot()

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_state(self, session_id: str) -> StateSnapshot:
        """Return the current state snapshot for a session."""
        _state, adapter, _mediator, _renderer = self._get_bundle(session_id)
        return adapter.get_state_snapshot()

    def get_history(self, session_id: str) -> list[TurnRecord]:
        """Return the full turn history for a session."""
        state, _adapter, _mediator, _renderer = self._get_bundle(session_id)
        return list(state.turns)

    # ------------------------------------------------------------------
    # Checkpointing and replay
    # ------------------------------------------------------------------

    def create_checkpoint(self, session_id: str) -> int:
        """Save the full adapter state at the current tick and return the
        checkpoint tick number.
        """
        session_state, adapter, _mediator, _renderer = self._get_bundle(session_id)
        tick = session_state.current_tick
        full_state = adapter.get_full_state()
        session_state.checkpoints[tick] = full_state
        return tick

    def replay_from(self, session_id: str, from_turn: int) -> str:
        """Create a new branched session from a checkpoint at *from_turn*
        and return the new session_id.

        The new session inherits the original's configuration, turn history
        up to *from_turn*, and the engine state from the nearest checkpoint
        at or before that turn.
        """
        session_state, _adapter, _mediator, _renderer = self._get_bundle(session_id)

        # Find the nearest checkpoint at or before from_turn
        checkpoint_tick: int | None = None
        checkpoint_state: dict[str, Any] | None = None
        for tick in sorted(session_state.checkpoints.keys(), reverse=True):
            if tick <= from_turn:
                checkpoint_tick = tick
                checkpoint_state = session_state.checkpoints[tick]
                break

        # Create a new session with the same config
        new_config = session_state.config.model_copy(deep=True)
        new_config.session_id = ""  # will be generated
        new_session_id = self.create_session(new_config)

        new_state, new_adapter, _new_med, _new_ren = self._get_bundle(new_session_id)

        # Restore engine state from checkpoint if available
        if checkpoint_state is not None:
            new_adapter.set_full_state(checkpoint_state)

        # Copy turn history up to from_turn
        new_state.turns = [
            t.model_copy(deep=True)
            for t in session_state.turns[:from_turn]
        ]
        new_state.current_tick = (
            session_state.turns[from_turn - 1].tick
            if from_turn > 0 and session_state.turns
            else 0
        )

        # Record the branch origin
        new_state.scenario_events.append({
            "type": "branch",
            "source_session": session_id,
            "from_turn": from_turn,
            "checkpoint_tick": checkpoint_tick,
        })

        return new_session_id

    # ------------------------------------------------------------------
    # Persistence — JSON files
    # ------------------------------------------------------------------

    def save_session(self, session_id: str) -> None:
        """Persist the session state to a JSON file on disk."""
        session_state, _adapter, _mediator, _renderer = self._get_bundle(session_id)

        self._storage_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._storage_dir / f"{session_id}.json"

        data = session_state.model_dump(mode="json")
        file_path.write_text(json.dumps(data, indent=2, default=str))

    def load_session(self, session_id: str) -> SessionState | None:
        """Load a session from a JSON file on disk.

        If the file exists, the session is restored into memory with a
        fresh adapter, mediator, and renderer.  The adapter is initialized
        and, if the session contains a checkpoint matching the current tick,
        the engine state is restored from it.

        Returns ``None`` if the file does not exist.
        """
        file_path = self._storage_dir / f"{session_id}.json"
        if not file_path.exists():
            return None

        raw = json.loads(file_path.read_text())
        session_state = SessionState(**raw)

        # Rebuild the live components
        adapter = SwanCoreAdapter(seed=session_state.config.seed)
        adapter.initialize(
            {"module_configs": session_state.config.module_configs}
            if session_state.config.module_configs
            else None
        )

        # Restore from the latest checkpoint if available
        if session_state.checkpoints:
            latest_tick = max(session_state.checkpoints.keys())
            adapter.set_full_state(session_state.checkpoints[latest_tick])

        mediator = ConversationalMediator()
        renderer = LanguageRenderer()

        self._sessions[session_id] = (session_state, adapter, mediator, renderer)
        return session_state

    def list_sessions(self) -> list[str]:
        """Return a list of all known session IDs.

        Includes both in-memory sessions and sessions found as JSON files
        in the storage directory.
        """
        session_ids = set(self._sessions.keys())

        if self._storage_dir.exists():
            for p in self._storage_dir.glob("*.json"):
                session_ids.add(p.stem)

        return sorted(session_ids)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_bundle(self, session_id: str) -> _SessionBundle:
        """Retrieve the session bundle or raise ``KeyError``."""
        bundle = self._sessions.get(session_id)
        if bundle is None:
            raise KeyError(f"Session '{session_id}' not found")
        return bundle
