"""DefaultValuation — assigns significance to states, entities, goals, and experiences.

Maintains a set of value dimensions that are dynamically adjusted based on
recent experience.  Detects value conflicts when competing values pull in
opposite directions, and emits preference orderings for downstream decision
modules.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


# ---------------------------------------------------------------------------
# State & Config
# ---------------------------------------------------------------------------

_DEFAULT_VALUES: dict[str, float] = {
    "internal_stability": 0.8,
    "self_preservation": 0.9,
    "mission_continuity": 0.7,
    "knowledge_integrity": 0.6,
    "social_trust": 0.5,
    "exploration": 0.4,
    "risk_avoidance": 0.6,
    "honesty": 0.7,
}


class ValuationState(BaseState):
    """Serializable snapshot of the valuation landscape."""

    module_name: str = "valuation"
    version: str = "0.1.0"

    values: dict[str, float] = Field(default_factory=lambda: dict(_DEFAULT_VALUES))
    preferences: list[str] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)


class ValuationConfig(BaseConfig):
    """Configuration knobs for the valuation module."""

    initial_values: dict[str, float] = Field(default_factory=lambda: dict(_DEFAULT_VALUES))
    learning_rate: float = 0.05


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class DefaultValuation(BaseModule):
    """Assigns significance to states, entities, goals, and experiences."""

    VERSION = "0.1.0"
    CAPABILITIES = ["valuation"]
    DEPENDENCIES = ["neuromodulation", "self_model", "memory", "social"]

    def __init__(self) -> None:
        self._state = ValuationState()
        self._config = ValuationConfig()

    # -- lifecycle ----------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = ValuationConfig(**config)
        self._state = ValuationState(
            values=dict(self._config.initial_values),
        )

    def reset(self) -> None:
        self.initialize()

    # -- state persistence --------------------------------------------------

    def get_state(self) -> ValuationState:
        return self._state.model_copy()

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, ValuationState):
            self._state = state.model_copy()
        else:
            self._state = ValuationState(**state.model_dump())

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _adjust(self, dimension: str, delta: float) -> None:
        """Shift a value dimension by *delta*, clamped to [0, 1]."""
        self._state.values[dimension] = self._clamp(
            self._state.values.get(dimension, 0.5) + delta
        )

    # -- main tick ----------------------------------------------------------

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        s = self._state
        lr = self._config.learning_rate
        s.tick = tick

        # Read upstream context (all optional)
        modulator_state = context.modulator_state or {}
        self_model_state = context.self_model_state or {}
        memory_context = context.memory_context or {}
        social_state = context.social_state or {}

        # ---- Adjust values based on recent experience ---------------------

        # If viability is low, increase self_preservation and risk_avoidance
        viability = self_model_state.get("viability", 1.0)
        if viability < 0.5:
            deficit = 0.5 - viability  # 0..0.5
            self._adjust("self_preservation", lr * deficit * 2)
            self._adjust("risk_avoidance", lr * deficit * 2)

        # If stress is high, boost internal_stability value
        stress = modulator_state.get("stress_load", 0.2)
        if stress > 0.5:
            self._adjust("internal_stability", lr * (stress - 0.5))

        # Trust events from social state
        trust_level = social_state.get("total_bond_strength", 0.0)
        if trust_level > 0.0:
            self._adjust("social_trust", lr * min(trust_level, 0.5))

        # Check for trust-breaking events
        for event in context.events:
            if event.event_type == "trust_broken":
                self._adjust("social_trust", -lr * 2)
            elif event.event_type == "exploration_rewarded":
                self._adjust("exploration", lr * 1.5)

        # If curiosity/exploration drive is high, slightly boost exploration
        curiosity = modulator_state.get("curiosity_drive", 0.5)
        if curiosity > 0.6:
            self._adjust("exploration", lr * (curiosity - 0.6))
            self._adjust("risk_avoidance", -lr * (curiosity - 0.6) * 0.5)

        # Grief suppresses exploration and social trust
        grief = modulator_state.get("grief_persistence", 0.0)
        if grief > 0.3:
            self._adjust("exploration", -lr * grief * 0.5)

        # ---- Detect value conflicts ---------------------------------------

        s.conflicts = []
        sorted_dims = sorted(s.values.items(), key=lambda kv: kv[1], reverse=True)

        # Opposing-direction pairs that can conflict
        _opposing_pairs = [
            ("self_preservation", "exploration"),
            ("risk_avoidance", "exploration"),
            ("social_trust", "self_preservation"),
            ("honesty", "self_preservation"),
            ("mission_continuity", "internal_stability"),
        ]

        for dim_a, dim_b in _opposing_pairs:
            val_a = s.values.get(dim_a, 0.5)
            val_b = s.values.get(dim_b, 0.5)
            # Conflict when both are relatively high (pulling in opposite dirs)
            difficulty = min(val_a, val_b) / max(val_a, val_b) if max(val_a, val_b) > 0 else 0.0
            # Scale difficulty by the magnitude of both values
            difficulty *= (val_a + val_b) / 2.0
            if difficulty > 0.4:
                s.conflicts.append({
                    "dimensions": [dim_a, dim_b],
                    "values": [val_a, val_b],
                    "difficulty": round(difficulty, 4),
                })

        # ---- Generate preference ordering ---------------------------------

        s.preferences = [dim for dim, _ in sorted_dims]

        # ---- Events -------------------------------------------------------

        events: list[Event] = []
        for conflict in s.conflicts:
            if conflict["difficulty"] > 0.7:
                events.append(Event(
                    tick=tick,
                    source_module="valuation",
                    event_type="value_conflict",
                    data=conflict,
                    severity=min(1.0, conflict["difficulty"]),
                ))

        state_dict = s.model_dump()
        return ModuleOutput(
            module_name="valuation",
            tick=tick,
            state=state_dict,
            events=events,
        )

    # -- event handler ------------------------------------------------------

    def on_event(self, event: Event) -> None:
        lr = self._config.learning_rate
        if event.event_type == "damage_critical":
            self._adjust("self_preservation", lr * 2)
            self._adjust("risk_avoidance", lr * 1.5)
        elif event.event_type == "critical_energy_low":
            self._adjust("self_preservation", lr)
        elif event.event_type == "trust_broken":
            self._adjust("social_trust", -lr * 2)
        elif event.event_type == "attachment_formed":
            self._adjust("social_trust", lr)
