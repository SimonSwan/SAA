"""DefaultHomeostasis — setpoint regulation and viability computation.

Maintains desired operating ranges (setpoints) for each interoceptive
channel and computes per-channel regulation error, an overall viability
score, and a priority-sorted list for downstream regulation / action
selection.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


# ---------------------------------------------------------------------------
# Setpoint type
# ---------------------------------------------------------------------------

# Each setpoint is (low, high, critical_low, critical_high).
# "low" and "high" define the comfortable range;
# "critical_low" and "critical_high" define the survivable range.
SetpointTuple = tuple[float, float, float, float]

DEFAULT_SETPOINTS: dict[str, SetpointTuple] = {
    "energy_deficit":    (0.0, 0.3, 0.0, 0.6),
    "thermal_stress":    (0.0, 0.2, 0.0, 0.5),
    "strain_load":       (0.0, 0.3, 0.0, 0.7),
    "damage_level":      (0.0, 0.1, 0.0, 0.5),
    "memory_risk":       (0.0, 0.1, 0.0, 0.4),
    "resource_scarcity": (0.0, 0.3, 0.0, 0.7),
}


# ---------------------------------------------------------------------------
# State & Config
# ---------------------------------------------------------------------------

class HomeostasisState(BaseState):
    """Serializable homeostasis snapshot."""

    module_name: str = "homeostasis"
    version: str = "0.1.0"

    errors: dict[str, float] = Field(default_factory=dict)
    viability: float = 1.0
    regulation_priorities: list[dict[str, Any]] = Field(default_factory=list)


class HomeostasisConfig(BaseConfig):
    """Configuration for the homeostasis module."""

    setpoints: dict[str, tuple[float, float, float, float]] = Field(
        default_factory=lambda: dict(DEFAULT_SETPOINTS)
    )

    # Weights for the viability aggregation (equal by default).
    channel_weights: dict[str, float] = Field(default_factory=lambda: {
        "energy_deficit": 1.5,
        "thermal_stress": 1.0,
        "strain_load": 1.0,
        "damage_level": 1.5,
        "memory_risk": 1.2,
        "resource_scarcity": 1.0,
    })

    viability_critical_threshold: float = 0.3
    viability_warning_threshold: float = 0.5


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class DefaultHomeostasis(BaseModule):
    """Computes regulation error and viability from the interoceptive vector."""

    VERSION = "0.1.0"
    CAPABILITIES = ["homeostasis"]
    DEPENDENCIES = ["interoception"]

    def __init__(self) -> None:
        self._state = HomeostasisState()
        self._config = HomeostasisConfig()

    # -- lifecycle ----------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = HomeostasisConfig(**config)
        self._state = HomeostasisState()

    def reset(self) -> None:
        self.initialize()

    # -- state persistence --------------------------------------------------

    def get_state(self) -> HomeostasisState:
        return self._state.model_copy()

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, HomeostasisState):
            self._state = state.model_copy()
        else:
            self._state = HomeostasisState(**state.model_dump())

    # -- main tick ----------------------------------------------------------

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        cfg = self._config
        setpoints = cfg.setpoints
        weights = cfg.channel_weights

        # Read interoceptive vector from context
        intero = context.interoceptive_vector or {}

        errors: dict[str, float] = {}
        weighted_error_sum = 0.0
        weight_sum = 0.0

        for channel, (low, high, crit_low, crit_high) in setpoints.items():
            value = intero.get(channel, 0.0)

            # Error: how far outside the comfortable [low, high] range
            error = max(0.0, value - high) + max(0.0, low - value)
            errors[channel] = error

            # Normalise error by the critical range width for viability calc
            critical_range = crit_high - high  # distance from comfort edge to critical edge
            if critical_range > 0:
                normalised_error = min(1.0, error / critical_range)
            else:
                normalised_error = 1.0 if error > 0 else 0.0

            w = weights.get(channel, 1.0)
            weighted_error_sum += normalised_error * w
            weight_sum += w

        # Viability: 1.0 means all channels in comfort zone, 0.0 means all critical
        if weight_sum > 0:
            viability = max(0.0, min(1.0, 1.0 - (weighted_error_sum / weight_sum)))
        else:
            viability = 1.0

        # Regulation priorities — sorted by descending error magnitude
        priorities: list[dict[str, Any]] = []
        for channel in sorted(errors, key=lambda c: errors[c], reverse=True):
            if errors[channel] > 0:
                sp = setpoints[channel]
                priorities.append({
                    "channel": channel,
                    "error": round(errors[channel], 4),
                    "value": round(intero.get(channel, 0.0), 4),
                    "setpoint_high": sp[1],
                    "setpoint_low": sp[0],
                    "critical_high": sp[3],
                })

        # Events
        events: list[Event] = []
        if viability < cfg.viability_critical_threshold:
            events.append(Event(
                tick=tick,
                source_module="homeostasis",
                event_type="viability_critical",
                data={"viability": round(viability, 4), "top_errors": priorities[:3]},
                severity=0.95,
            ))
        elif viability < cfg.viability_warning_threshold:
            events.append(Event(
                tick=tick,
                source_module="homeostasis",
                event_type="viability_warning",
                data={"viability": round(viability, 4), "top_errors": priorities[:3]},
                severity=0.6,
            ))

        # Finalize state
        self._state.errors = {k: round(v, 6) for k, v in errors.items()}
        self._state.viability = round(viability, 4)
        self._state.regulation_priorities = priorities
        self._state.tick = tick

        state_dict = self._state.model_dump()
        return ModuleOutput(
            module_name="homeostasis",
            tick=tick,
            state=state_dict,
            events=events,
        )

    # -- event handler ------------------------------------------------------

    def on_event(self, event: Event) -> None:
        pass  # Homeostasis is reactive only through its update cycle.
