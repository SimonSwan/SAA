"""Swan Core Interface Adapter — wraps the SAA engine for the SIO layer.

Provides a clean interface between the conversational overlay and the
underlying simulation engine, translating interactions into events and
extracting structured state for rendering.
"""

from __future__ import annotations

import logging
from typing import Any

from saa.core.engine import SimulationEngine
from saa.core.event_bus import EventBus
from saa.core.module_registry import ModuleRegistry
from saa.core.persistence import PersistenceLayer
from saa.core.types import EnvironmentState, Event, TickContext
from saa.sio.core.schemas import (
    ActionIntent,
    InteractionObject,
    InteractionType,
    StateSnapshot,
    StateDiff,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Interaction-type to social-event mapping
# ---------------------------------------------------------------------------

_SOCIAL_EVENT_MAP: dict[InteractionType, str] = {
    InteractionType.THREATENING: "social_threat",
    InteractionType.DEMANDING: "social_demand",
    InteractionType.MANIPULATIVE: "social_manipulation",
    InteractionType.SUPPORTIVE: "social_support",
    InteractionType.SOCIAL: "social_greeting",
    InteractionType.MISSION_RELEVANT: "mission_input",
    InteractionType.QUERY: "social_query",
    InteractionType.NEUTRAL: "social_neutral",
}


class SwanCoreAdapter:
    """Wraps the SAA :class:`SimulationEngine` to provide the interface the
    SIO needs for conversation-driven interaction.

    Responsibilities:
    - Creating and wiring the full engine with all 11 modules.
    - Mapping :class:`InteractionObject` data to engine events and ticks.
    - Extracting structured snapshots, diffs, and traces for the SIO.
    """

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._event_bus = EventBus()
        self._registry = ModuleRegistry()
        self._persistence = PersistenceLayer()
        self._persistence.connect()

        self._engine = SimulationEngine(
            agent_id=f"swan_{seed}",
            registry=self._registry,
            event_bus=self._event_bus,
            persistence=self._persistence,
        )

        self._register_modules()

    # ------------------------------------------------------------------
    # Module registration
    # ------------------------------------------------------------------

    def _register_modules(self) -> None:
        """Instantiate and register all 11 SAA modules."""
        from saa.modules.embodiment.default import SimulatedEmbodiment
        from saa.modules.interoception.default import DefaultInteroception
        from saa.modules.homeostasis.default import DefaultHomeostasis
        from saa.modules.allostasis.default import DefaultAllostasis
        from saa.modules.neuromodulation.default import DefaultNeuromodulation
        from saa.modules.self_model.default import DefaultSelfModel
        from saa.modules.memory.default import SQLiteMemorySystem
        from saa.modules.valuation.default import DefaultValuation
        from saa.modules.social.default import DefaultSocial
        from saa.modules.action.default import DefaultActionSelection
        from saa.modules.observability.default import DefaultObservability

        self._registry.register("embodiment", SimulatedEmbodiment())
        self._registry.register("interoception", DefaultInteroception())
        self._registry.register("homeostasis", DefaultHomeostasis())
        self._registry.register("allostasis", DefaultAllostasis())
        self._registry.register("neuromodulation", DefaultNeuromodulation())
        self._registry.register("self_model", DefaultSelfModel())
        self._registry.register("memory", SQLiteMemorySystem())
        self._registry.register("valuation", DefaultValuation())
        self._registry.register("social", DefaultSocial())
        self._registry.register("action", DefaultActionSelection())
        self._registry.register("observability", DefaultObservability())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: dict | None = None) -> None:
        """Initialize all registered modules with optional per-module configs."""
        configs: dict[str, dict[str, Any]] = {}
        if config:
            configs = config.get("module_configs", config)
        self._engine.initialize_modules(configs)

    # ------------------------------------------------------------------
    # Interaction processing
    # ------------------------------------------------------------------

    def process_interaction(
        self, interaction: InteractionObject
    ) -> tuple[TickContext, ActionIntent]:
        """Map an interaction to engine events, run one tick, and extract
        the resulting :class:`ActionIntent`.

        Parameters
        ----------
        interaction:
            Structured interaction parsed by the mediator.

        Returns
        -------
        tuple[TickContext, ActionIntent]
            The full tick context and the extracted action intent.
        """
        # 1. Inject social events based on classification
        event_type = _SOCIAL_EVENT_MAP.get(
            interaction.classification, "social_neutral"
        )
        social_event = Event(
            tick=self._engine.tick + 1,
            source_module="sio",
            event_type=event_type,
            data={
                "text": interaction.text,
                "intent": interaction.intent,
                "classification": interaction.classification.value,
                "urgency": interaction.urgency,
                "social_signal": interaction.social_signal,
                "estimated_cost": interaction.estimated_cost,
            },
            severity=interaction.urgency,
        )
        self._event_bus.publish(social_event)

        # 2. Adjust environment based on interaction properties
        env = EnvironmentState(
            available_resources=self._engine._environment.available_resources,
            ambient_temperature=self._engine._environment.ambient_temperature,
            hazard_level=self._engine._environment.hazard_level,
            social_agents=self._engine._environment.social_agents,
            tick=self._engine.tick + 1,
        )
        # Threatening interactions raise hazard level
        if interaction.classification == InteractionType.THREATENING:
            env.hazard_level = min(1.0, env.hazard_level + 0.3)
        # Ensure there is at least one social agent for social interactions
        if interaction.target and interaction.target not in env.social_agents:
            env.social_agents.append(interaction.target)
        if "user" not in env.social_agents:
            env.social_agents.append("user")
        self._engine.set_environment(env)

        # 3. Run one engine tick
        context = self._engine.step()

        # 4. Extract ActionIntent from action_result
        action_intent = self._extract_action_intent(context)

        return context, action_intent

    def _extract_action_intent(self, context: TickContext) -> ActionIntent:
        """Build an :class:`ActionIntent` from the tick context's action_result."""
        ar = context.action_result or {}

        # The action module stores its trace in last_trace
        trace = ar.get("last_trace", {})
        last_action = ar.get("last_action", {})

        candidates = trace.get("candidates", [])
        conflict_info = trace.get("conflict")

        # Build competing actions list (exclude the selected one)
        selected = trace.get("selected", last_action.get("action", "communicate"))
        competing = [
            {"action_type": c["action"], "score": c["score"]}
            for c in candidates
            if c["action"] != selected
        ][:5]

        # Build internal influences from modulator and valuation state
        influences: dict[str, float] = {}
        if context.modulator_state:
            mods = context.modulator_state.get("modulators", context.modulator_state)
            for k, v in mods.items():
                if isinstance(v, (int, float)):
                    influences[f"modulator.{k}"] = float(v)
        if context.valuation_map:
            vals = context.valuation_map.get("values", {})
            for k, v in vals.items():
                if isinstance(v, (int, float)):
                    influences[f"value.{k}"] = float(v)

        rationale_lines: list[str] = []
        if conflict_info:
            rationale_lines.append(conflict_info.get("rationale", ""))
        rationale_lines.append(f"Selected '{selected}' with score {trace.get('selected_score', 0.0):.4f}")

        return ActionIntent(
            action_type=selected,
            score=trace.get("selected_score", last_action.get("score", 0.0)),
            conflict=conflict_info is not None,
            rationale=rationale_lines,
            competing_actions=competing,
            internal_influences=influences,
        )

    # ------------------------------------------------------------------
    # State snapshots
    # ------------------------------------------------------------------

    def get_state_snapshot(self) -> StateSnapshot:
        """Read all module states and build a :class:`StateSnapshot`."""
        tick = self._engine.tick

        # Embodiment
        emb = self._get_module_state("embodiment")
        energy = emb.get("energy", 1.0)
        temperature = emb.get("temperature", 0.5)
        strain = emb.get("strain", 0.0)
        damage = emb.get("damage", 0.0)
        memory_integrity = emb.get("memory_integrity", 1.0)
        resource_level = emb.get("resource_level", 1.0)

        # Homeostasis
        homeo = self._get_module_state("homeostasis")
        viability = homeo.get("viability", 1.0)
        homeostatic_errors = {
            k: float(v) for k, v in homeo.get("errors", {}).items()
            if isinstance(v, (int, float))
        }
        regulation_priorities = [
            p.get("channel", str(p)) if isinstance(p, dict) else str(p)
            for p in homeo.get("regulation_priorities", [])
        ]

        # Neuromodulation
        neuro = self._get_module_state("neuromodulation")
        modulators = {
            k: float(v) for k, v in neuro.get("modulators", {}).items()
            if isinstance(v, (int, float))
        }

        # Interoception
        intero = self._get_module_state("interoception")
        interoceptive_channels = {
            k: float(v) for k, v in intero.get("channels", {}).items()
            if isinstance(v, (int, float))
        }

        # Self-model
        selfm = self._get_module_state("self_model")
        continuity_score = selfm.get("continuity_score", 1.0)
        identity_anchors = selfm.get("identity_anchors", [])
        goal_stack_size = len(selfm.get("goal_stack", []))

        # Valuation
        val = self._get_module_state("valuation")
        values = {
            k: float(v) for k, v in val.get("values", {}).items()
            if isinstance(v, (int, float))
        }

        # Allostasis
        allo = self._get_module_state("allostasis")
        risk_scores = {
            k: float(v) for k, v in allo.get("risk_scores", {}).items()
            if isinstance(v, (int, float))
        }

        # Social
        soc = self._get_module_state("social")
        relationships = soc.get("relationships", {})

        # Valuation conflicts
        active_conflicts = val.get("conflicts", [])

        return StateSnapshot(
            tick=tick,
            energy=energy,
            temperature=temperature,
            strain=strain,
            damage=damage,
            memory_integrity=memory_integrity,
            resource_level=resource_level,
            viability=viability,
            continuity_score=continuity_score,
            modulators=modulators,
            interoceptive_channels=interoceptive_channels,
            homeostatic_errors=homeostatic_errors,
            values=values,
            risk_scores=risk_scores,
            relationships=relationships,
            active_conflicts=active_conflicts,
            regulation_priorities=regulation_priorities,
            identity_anchors=identity_anchors,
            goal_stack_size=goal_stack_size,
        )

    def compute_state_diff(
        self, before: StateSnapshot, after: StateSnapshot
    ) -> list[StateDiff]:
        """Compare two snapshots and return diffs for numeric fields.

        Only includes diffs where ``abs(delta) > 0.001``.
        """
        diffs: list[StateDiff] = []

        # Top-level numeric fields
        numeric_fields = [
            "energy", "temperature", "strain", "damage",
            "memory_integrity", "resource_level", "viability",
            "continuity_score",
        ]
        for field in numeric_fields:
            prev = getattr(before, field)
            curr = getattr(after, field)
            delta = curr - prev
            if abs(delta) > 0.001:
                diffs.append(StateDiff(
                    field=field, previous=prev, current=curr, delta=delta
                ))

        # Dict-valued numeric fields
        dict_fields = [
            "modulators", "interoceptive_channels",
            "homeostatic_errors", "values", "risk_scores",
        ]
        for dict_field in dict_fields:
            before_dict: dict[str, float] = getattr(before, dict_field)
            after_dict: dict[str, float] = getattr(after, dict_field)
            all_keys = set(before_dict.keys()) | set(after_dict.keys())
            for key in sorted(all_keys):
                prev = before_dict.get(key, 0.0)
                curr = after_dict.get(key, 0.0)
                delta = curr - prev
                if abs(delta) > 0.001:
                    diffs.append(StateDiff(
                        field=f"{dict_field}.{key}",
                        previous=prev,
                        current=curr,
                        delta=delta,
                    ))

        return diffs

    # ------------------------------------------------------------------
    # Specialized state queries
    # ------------------------------------------------------------------

    def get_memory_snapshot(self) -> dict:
        """Return memory counts and recent episode summaries."""
        mem = self._get_module_state("memory")
        return {
            "episodic_count": mem.get("episodic_count", 0),
            "semantic_count": mem.get("semantic_count", 0),
            "relational_count": mem.get("relational_count", 0),
            "last_encoded_tick": mem.get("last_encoded_tick", 0),
            "recent_episodes": mem.get("memory_context", {}).get(
                "recent_episodes", []
            ),
        }

    def get_relationship_graph(self) -> dict[str, dict]:
        """Return the relationship map from the social module."""
        soc = self._get_module_state("social")
        return soc.get("relationships", {})

    def get_active_conflicts(self) -> list[dict]:
        """Return value conflicts from the valuation module."""
        val = self._get_module_state("valuation")
        return val.get("conflicts", [])

    def get_modulation_state(self) -> dict[str, float]:
        """Return current modulator values."""
        neuro = self._get_module_state("neuromodulation")
        modulators = neuro.get("modulators", {})
        return {
            k: float(v) for k, v in modulators.items()
            if isinstance(v, (int, float))
        }

    def get_rationale_trace(self) -> dict:
        """Return the last action trace including candidates and conflict info."""
        action = self._get_module_state("action")
        return action.get("last_trace", {})

    # ------------------------------------------------------------------
    # Full state checkpoint / restore
    # ------------------------------------------------------------------

    def get_full_state(self) -> dict:
        """Return full engine state for checkpointing."""
        return self._engine.save_state()

    def set_full_state(self, state: dict) -> None:
        """Restore engine from a checkpoint dict."""
        self._engine.load_state(state)

    # ------------------------------------------------------------------
    # Event and environment injection
    # ------------------------------------------------------------------

    def inject_event(self, event_type: str, data: dict) -> None:
        """Inject an arbitrary event into the event bus."""
        event = Event(
            tick=self._engine.tick,
            source_module="sio_inject",
            event_type=event_type,
            data=data,
            severity=data.get("severity", 0.5),
        )
        self._event_bus.publish(event)

    def set_environment(self, env: EnvironmentState) -> None:
        """Set the environment state for the next tick."""
        self._engine.set_environment(env)

    # ------------------------------------------------------------------
    # Module metadata
    # ------------------------------------------------------------------

    def get_module_versions(self) -> dict[str, str]:
        """Return a mapping of module name to version string."""
        versions: dict[str, str] = {}
        for name, module in self._registry.get_ordered_modules():
            versions[name] = getattr(module, "VERSION", "0.0.0")
        return versions

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_module_state(self, name: str) -> dict[str, Any]:
        """Safely retrieve a module's state as a dict."""
        try:
            module = self._registry.get(name)
            return module.get_state().model_dump()
        except (KeyError, Exception) as exc:
            logger.warning("Failed to read state from module '%s': %s", name, exc)
            return {}
