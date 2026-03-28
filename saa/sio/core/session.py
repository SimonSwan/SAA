"""Session Manager — manages SIO sessions with persistence, checkpointing,
replay, and branching.

Each session wraps a full SwanCoreAdapter, ConversationalMediator,
LanguageRenderer, InteractionAttribution, and policy layer.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
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
    StanceType,
)
from saa.sio.core.adapter import SwanCoreAdapter
from saa.sio.core.mediator import ConversationalMediator
from saa.sio.core.renderer import LanguageRenderer
from saa.sio.core.policy import (
    InteractionAttribution,
    compute_state_diffs,
    select_interaction_action,
    compute_trust_factor,
    compute_pressure,
)
from saa.sio.core.appraisal import (
    AppraisalEngine, AffectSynthesizer, StanceEngine,
    NarrativeSynthesizer, TrendProjector,
)


@dataclass
class _SessionComponents:
    state: SessionState
    adapter: SwanCoreAdapter
    mediator: ConversationalMediator
    renderer: LanguageRenderer
    attribution: InteractionAttribution
    first_state: StateSnapshot | None
    appraisal_engine: AppraisalEngine
    affect_synth: AffectSynthesizer
    stance_engine: StanceEngine
    narrative_synth: NarrativeSynthesizer
    trend_projector: TrendProjector


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
        self._sessions: dict[str, _SessionComponents] = {}

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
        appraisal_engine = AppraisalEngine()
        affect_synth = AffectSynthesizer()
        stance_engine = StanceEngine()
        narrative_synth = NarrativeSynthesizer()
        trend_projector = TrendProjector()

        self._sessions[session_id] = _SessionComponents(
            state=state,
            adapter=adapter,
            mediator=mediator,
            renderer=renderer,
            attribution=attribution,
            first_state=first_state,
            appraisal_engine=appraisal_engine,
            affect_synth=affect_synth,
            stance_engine=stance_engine,
            narrative_synth=narrative_synth,
            trend_projector=trend_projector,
        )
        return session_id

    def get_session(self, session_id: str) -> SessionState | None:
        bundle = self._sessions.get(session_id)
        return bundle.state if bundle else None

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
        bundle = self._get_bundle(session_id)

        # 1. Parse
        interaction = bundle.mediator.parse(text)

        # 2. Snapshot before
        state_before = bundle.adapter.get_state_snapshot()

        # 3. Process through engine
        context, _engine_action = bundle.adapter.process_interaction(interaction)

        # 4. Snapshot after
        state_after = bundle.adapter.get_state_snapshot()

        # 5. Compute diffs
        state_diffs = compute_state_diffs(state_before, state_after)

        # 6. Record attribution
        attr_entry = bundle.attribution.record(interaction, state_before, state_after)

        # 6a. Appraisal
        turn_id = len(bundle.state.turns)
        appraisal = bundle.appraisal_engine.appraise(interaction, state_before, state_after, bundle.attribution)

        # 6b. Affect synthesis
        affect = bundle.affect_synth.update(appraisal, state_after, bundle.attribution, bundle.appraisal_engine.history)

        # 6b2. Interaction-driven stress update
        pressure = compute_pressure(state_after)
        trust = compute_trust_factor(state_after, interaction.target or "user")
        trust_before = compute_trust_factor(state_before, interaction.target or "user")
        current_stress = state_after.modulators.get("stress_load", 0.2)

        # Accumulation: negative interactions add stress
        intent = appraisal.perceived_intent.value
        is_negative = intent in ("demanding", "manipulative", "deceptive", "contradictory")
        is_positive = intent in ("supportive", "cooperative")

        stress_accum = 0.0
        if is_negative:
            stress_accum = (
                0.25 * max(0.0, trust_before - trust)
                + 0.10 * (1.0 if state_after.active_conflicts else 0.0)
                + 0.05
            )

        # Decay toward baseline — always active, faster with support
        baseline = 0.2
        above_baseline = max(0.0, current_stress - baseline)
        if is_positive:
            decay = above_baseline * 0.15  # 15% decay per supportive turn
        elif is_negative:
            decay = 0.0  # no decay during negative interactions
        else:
            decay = above_baseline * 0.05  # natural decay

        stress_delta = stress_accum - decay
        stress_delta = max(-0.06, min(0.08, stress_delta))
        bundle.adapter.update_stress(stress_delta)
        state_after = bundle.adapter.get_state_snapshot()
        state_diffs = compute_state_diffs(state_before, state_after)

        # 6c. Stance computation
        pressure = compute_pressure(state_after)
        stance = bundle.stance_engine.compute(affect, trust, pressure, bundle.attribution, turn_id)

        # 6d. Narrative
        narrative = bundle.narrative_synth.synthesize(
            bundle.appraisal_engine.history, affect, stance, bundle.attribution,
            state_after, bundle.first_state, bundle.stance_engine.history,
        )

        # 6e. Trend projection
        projection = bundle.trend_projector.project(bundle.state.turns, state_after)

        # 7. Policy selects conversational action
        action_intent = select_interaction_action(interaction, state_after, bundle.attribution, stance)

        # 8. Render response
        response_text = bundle.renderer.render(
            action_intent=action_intent,
            state=state_after,
            interaction=interaction,
            diffs=state_diffs,
            attribution=bundle.attribution,
            first_state=bundle.first_state,
            affect=affect,
            stance=stance,
            narrative=narrative,
            projection=projection,
        )

        # 9. Build TurnRecord
        tick = state_after.tick

        memory_snapshot = bundle.adapter.get_memory_snapshot()
        relationship_graph = bundle.adapter.get_relationship_graph()
        rationale_trace = bundle.adapter.get_rationale_trace()
        rationale_trace["attribution"] = attr_entry
        rationale_trace["pressure"] = action_intent.internal_influences.get("pressure", 0)
        rationale_trace["appraisal"] = appraisal.model_dump()
        rationale_trace["affect"] = affect.model_dump()
        rationale_trace["stance"] = stance.value
        rationale_trace["narrative"] = narrative
        rationale_trace["projection"] = projection.model_dump()

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

        bundle.state.turns.append(turn)
        bundle.state.current_tick = tick

        return turn

    # ------------------------------------------------------------------
    # Event injection
    # ------------------------------------------------------------------

    def inject_event(self, session_id: str, event_type: str, data: dict) -> StateSnapshot:
        bundle = self._get_bundle(session_id)
        bundle.adapter.inject_event(event_type, data)
        return bundle.adapter.get_state_snapshot()

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_state(self, session_id: str) -> StateSnapshot:
        bundle = self._get_bundle(session_id)
        return bundle.adapter.get_state_snapshot()

    def get_history(self, session_id: str) -> list[TurnRecord]:
        bundle = self._get_bundle(session_id)
        return list(bundle.state.turns)

    def get_attribution(self, session_id: str) -> dict[str, Any]:
        bundle = self._get_bundle(session_id)
        return bundle.attribution.get_summary()

    # ------------------------------------------------------------------
    # Checkpointing and replay
    # ------------------------------------------------------------------

    def create_checkpoint(self, session_id: str) -> int:
        bundle = self._get_bundle(session_id)
        tick = bundle.state.current_tick
        bundle.state.checkpoints[tick] = bundle.adapter.get_full_state()
        return tick

    def replay_from(self, session_id: str, from_turn: int) -> str:
        bundle = self._get_bundle(session_id)

        checkpoint_state: dict[str, Any] | None = None
        for tick in sorted(bundle.state.checkpoints.keys(), reverse=True):
            if tick <= from_turn:
                checkpoint_state = bundle.state.checkpoints[tick]
                break

        new_config = bundle.state.config.model_copy(deep=True)
        new_config.session_id = ""
        new_session_id = self.create_session(new_config)
        new_bundle = self._get_bundle(new_session_id)

        if checkpoint_state is not None:
            new_bundle.adapter.set_full_state(checkpoint_state)

        new_bundle.state.turns = [t.model_copy(deep=True) for t in bundle.state.turns[:from_turn]]
        new_bundle.state.current_tick = (
            bundle.state.turns[from_turn - 1].tick
            if from_turn > 0 and bundle.state.turns else 0
        )
        new_bundle.state.scenario_events.append({
            "type": "branch",
            "source_session": session_id,
            "from_turn": from_turn,
        })

        return new_session_id

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_session(self, session_id: str) -> None:
        session_state = self._get_bundle(session_id).state
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

        self._sessions[session_id] = _SessionComponents(
            state=session_state,
            adapter=adapter,
            mediator=mediator,
            renderer=renderer,
            attribution=attribution,
            first_state=first_state,
            appraisal_engine=AppraisalEngine(),
            affect_synth=AffectSynthesizer(),
            stance_engine=StanceEngine(),
            narrative_synth=NarrativeSynthesizer(),
            trend_projector=TrendProjector(),
        )
        return session_state

    def list_sessions(self) -> list[str]:
        session_ids = set(self._sessions.keys())
        if self._storage_dir.exists():
            for p in self._storage_dir.glob("*.json"):
                session_ids.add(p.stem)
        return sorted(session_ids)

    # ------------------------------------------------------------------
    # Appraisal queries
    # ------------------------------------------------------------------

    def get_appraisal_history(self, session_id: str) -> list[dict[str, Any]]:
        bundle = self._get_bundle(session_id)
        return [a.model_dump() for a in bundle.appraisal_engine.history]

    def get_affect(self, session_id: str) -> dict[str, Any]:
        bundle = self._get_bundle(session_id)
        return bundle.affect_synth.state.model_dump()

    def get_stance(self, session_id: str) -> dict[str, Any]:
        bundle = self._get_bundle(session_id)
        return {"current": bundle.stance_engine.current.value, "history": bundle.stance_engine.history}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_bundle(self, session_id: str) -> _SessionComponents:
        bundle = self._sessions.get(session_id)
        if bundle is None:
            raise KeyError(f"Session '{session_id}' not found")
        return bundle
