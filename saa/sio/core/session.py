"""Session Manager — manages SIO sessions with persistence, checkpointing,
replay, and branching.

Each session wraps a full SwanCoreAdapter, ConversationalMediator,
LanguageRenderer, InteractionAttribution, and policy layer.
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
from saa.sio.core.policy import (
    InteractionAttribution,
    compute_state_diffs,
    select_interaction_action,
)


# Type alias for the per-session bundle stored in memory.
_SessionBundle = tuple[
    SessionState, SwanCoreAdapter, ConversationalMediator,
    LanguageRenderer, InteractionAttribution, StateSnapshot | None,
]


class SessionManager:
    """Creates, drives, and persists SIO sessions.

    Each session maintains:
    - SwanCoreAdapter: wraps the SAA engine
    - ConversationalMediator: parses user text
    - LanguageRenderer: generates state-grounded responses
    - InteractionAttribution: tracks cumulative interaction costs
    - first_state: initial StateSnapshot for trajectory comparison
    """

    def __init__(self, storage_dir: str = "sessions") -> None:
        self._storage_dir = Path(storage_dir)
        self._sessions: dict[str, _SessionBundle] = {}

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, config: SessionConfig | None = None) -> str:
        if config is None:
            config = SessionConfig()

        session_id = config.session_id or str(uuid.uuid4())
        config.session_id = session_id

        adapter = SwanCoreAdapter(seed=config.seed)
        adapter.initialize(
            {"module_configs": config.module_configs} if config.module_configs else None
        )

        mediator = ConversationalMediator()
        renderer = LanguageRenderer()
        attribution = InteractionAttribution()

        state = SessionState(
            session_id=session_id,
            config=config,
            module_versions=adapter.get_module_versions(),
        )

        first_state = adapter.get_state_snapshot()
        self._sessions[session_id] = (state, adapter, mediator, renderer, attribution, first_state)
        return session_id

    def get_session(self, session_id: str) -> SessionState | None:
        bundle = self._sessions.get(session_id)
        return bundle[0] if bundle else None

    # ------------------------------------------------------------------
    # Input processing — full pipeline
    # ------------------------------------------------------------------

    def process_input(self, session_id: str, text: str) -> TurnRecord:
        """Run the full SIO pipeline for a single user input.

        1. Mediator parses text
        2. Capture state before
        3. Adapter processes interaction (one engine tick)
        4. Capture state after
        5. Compute state diffs
        6. Record attribution (interaction cost)
        7. Policy selects conversational action based on state
        8. Renderer produces state-grounded response
        9. Build and store TurnRecord
        """
        session_state, adapter, mediator, renderer, attribution, first_state = (
            self._get_bundle(session_id)
        )

        # 1. Parse
        interaction = mediator.parse(text)

        # 2. Snapshot before
        state_before = adapter.get_state_snapshot()

        # 3. Process through engine
        context, _engine_action = adapter.process_interaction(interaction)

        # 4. Snapshot after
        state_after = adapter.get_state_snapshot()

        # 5. Compute diffs
        state_diffs = compute_state_diffs(state_before, state_after)

        # 6. Record attribution
        attr_entry = attribution.record(interaction, state_before, state_after)

        # 7. Policy selects conversational action
        action_intent = select_interaction_action(interaction, state_after, attribution)

        # 8. Render response
        response_text = renderer.render(
            action_intent=action_intent,
            state=state_after,
            interaction=interaction,
            diffs=state_diffs,
            attribution=attribution,
            first_state=first_state,
        )

        # 9. Build TurnRecord
        turn_id = len(session_state.turns)
        tick = state_after.tick

        memory_snapshot = adapter.get_memory_snapshot()
        relationship_graph = adapter.get_relationship_graph()
        rationale_trace = adapter.get_rationale_trace()
        rationale_trace["attribution"] = attr_entry
        rationale_trace["pressure"] = action_intent.internal_influences.get("pressure", 0)

        memory_updates: list[dict[str, Any]] = []
        if memory_snapshot.get("last_encoded_tick") == tick:
            memory_updates.append({
                "type": "episode_encoded",
                "tick": tick,
                "episodic_count": memory_snapshot.get("episodic_count", 0),
            })

        relationship_updates = [
            {"agent": agent, **data}
            for agent, data in relationship_graph.items()
        ]

        events_emitted = [
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

        session_state.turns.append(turn)
        session_state.current_tick = tick

        return turn

    # ------------------------------------------------------------------
    # Event injection
    # ------------------------------------------------------------------

    def inject_event(self, session_id: str, event_type: str, data: dict) -> StateSnapshot:
        _state, adapter, _m, _r, _a, _f = self._get_bundle(session_id)
        adapter.inject_event(event_type, data)
        return adapter.get_state_snapshot()

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_state(self, session_id: str) -> StateSnapshot:
        _state, adapter, _m, _r, _a, _f = self._get_bundle(session_id)
        return adapter.get_state_snapshot()

    def get_history(self, session_id: str) -> list[TurnRecord]:
        state, _a, _m, _r, _attr, _f = self._get_bundle(session_id)
        return list(state.turns)

    def get_attribution(self, session_id: str) -> dict[str, Any]:
        _state, _a, _m, _r, attribution, _f = self._get_bundle(session_id)
        return attribution.get_summary()

    # ------------------------------------------------------------------
    # Checkpointing and replay
    # ------------------------------------------------------------------

    def create_checkpoint(self, session_id: str) -> int:
        session_state, adapter, _m, _r, _a, _f = self._get_bundle(session_id)
        tick = session_state.current_tick
        session_state.checkpoints[tick] = adapter.get_full_state()
        return tick

    def replay_from(self, session_id: str, from_turn: int) -> str:
        session_state, _a, _m, _r, _attr, _f = self._get_bundle(session_id)

        checkpoint_state: dict[str, Any] | None = None
        for tick in sorted(session_state.checkpoints.keys(), reverse=True):
            if tick <= from_turn:
                checkpoint_state = session_state.checkpoints[tick]
                break

        new_config = session_state.config.model_copy(deep=True)
        new_config.session_id = ""
        new_session_id = self.create_session(new_config)
        new_state, new_adapter, _nm, _nr, _na, _nf = self._get_bundle(new_session_id)

        if checkpoint_state is not None:
            new_adapter.set_full_state(checkpoint_state)

        new_state.turns = [t.model_copy(deep=True) for t in session_state.turns[:from_turn]]
        new_state.current_tick = (
            session_state.turns[from_turn - 1].tick
            if from_turn > 0 and session_state.turns else 0
        )
        new_state.scenario_events.append({
            "type": "branch",
            "source_session": session_id,
            "from_turn": from_turn,
        })

        return new_session_id

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_session(self, session_id: str) -> None:
        session_state = self._get_bundle(session_id)[0]
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        path = self._storage_dir / f"{session_id}.json"
        path.write_text(json.dumps(session_state.model_dump(mode="json"), indent=2, default=str))

    def load_session(self, session_id: str) -> SessionState | None:
        path = self._storage_dir / f"{session_id}.json"
        if not path.exists():
            return None

        raw = json.loads(path.read_text())
        session_state = SessionState(**raw)

        adapter = SwanCoreAdapter(seed=session_state.config.seed)
        adapter.initialize(
            {"module_configs": session_state.config.module_configs}
            if session_state.config.module_configs else None
        )
        if session_state.checkpoints:
            latest_tick = max(session_state.checkpoints.keys())
            adapter.set_full_state(session_state.checkpoints[latest_tick])

        mediator = ConversationalMediator()
        renderer = LanguageRenderer()
        attribution = InteractionAttribution()
        first_state = adapter.get_state_snapshot()

        self._sessions[session_id] = (session_state, adapter, mediator, renderer, attribution, first_state)
        return session_state

    def list_sessions(self) -> list[str]:
        session_ids = set(self._sessions.keys())
        if self._storage_dir.exists():
            for p in self._storage_dir.glob("*.json"):
                session_ids.add(p.stem)
        return sorted(session_ids)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_bundle(self, session_id: str) -> _SessionBundle:
        bundle = self._sessions.get(session_id)
        if bundle is None:
            raise KeyError(f"Session '{session_id}' not found")
        return bundle
