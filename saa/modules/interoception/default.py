"""DefaultInteroception — aggregates body state into an interoceptive vector.

Transforms raw embodiment variables into normalised signal channels,
applies temporal smoothing, tracks history for trend analysis, and
detects threshold crossings and anomalous jumps.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


# ---------------------------------------------------------------------------
# State & Config
# ---------------------------------------------------------------------------

class InteroceptionState(BaseState):
    """Serializable interoception snapshot."""

    module_name: str = "interoception"
    version: str = "0.1.0"

    channels: dict[str, float] = Field(default_factory=dict)
    history: list[dict[str, float]] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)


class InteroceptionConfig(BaseConfig):
    """Configuration for the interoception module."""

    smoothing_alpha: float = 0.3  # EMA smoothing factor (0 = no update, 1 = no smoothing)
    smoothing_window: int = 10  # max history length kept
    anomaly_jump_threshold: float = 0.3  # delta in one tick that counts as anomaly

    alert_thresholds: dict[str, float] = Field(default_factory=lambda: {
        "energy_deficit": 0.6,
        "thermal_stress": 0.5,
        "strain_load": 0.6,
        "damage_level": 0.5,
        "memory_risk": 0.5,
        "resource_scarcity": 0.6,
    })


# ---------------------------------------------------------------------------
# Channel computation helpers
# ---------------------------------------------------------------------------

_CHANNEL_NAMES = [
    "energy_deficit",
    "thermal_stress",
    "strain_load",
    "damage_level",
    "memory_risk",
    "resource_scarcity",
]


def _compute_raw_channels(body: dict[str, Any]) -> dict[str, float]:
    """Derive interoceptive channels from raw embodiment state."""
    energy = body.get("energy", 1.0)
    temperature = body.get("temperature", 0.5)
    strain = body.get("strain", 0.0)
    damage = body.get("damage", 0.0)
    memory_integrity = body.get("memory_integrity", 1.0)
    resource_level = body.get("resource_level", 1.0)

    return {
        "energy_deficit": 1.0 - energy,
        "thermal_stress": min(1.0, abs(temperature - 0.5) * 2.0),
        "strain_load": strain,
        "damage_level": damage,
        "memory_risk": 1.0 - memory_integrity,
        "resource_scarcity": 1.0 - resource_level,
    }


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class DefaultInteroception(BaseModule):
    """Aggregates body-state signals into a smoothed interoceptive vector."""

    VERSION = "0.1.0"
    CAPABILITIES = ["interoception"]
    DEPENDENCIES = ["embodiment"]

    def __init__(self) -> None:
        self._state = InteroceptionState()
        self._config = InteroceptionConfig()
        self._prev_channels: dict[str, float] = {}

    # -- lifecycle ----------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = InteroceptionConfig(**config)
        self._state = InteroceptionState()
        self._prev_channels = {}

    def reset(self) -> None:
        self.initialize()

    # -- state persistence --------------------------------------------------

    def get_state(self) -> InteroceptionState:
        return self._state.model_copy()

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, InteroceptionState):
            self._state = state.model_copy()
        else:
            self._state = InteroceptionState(**state.model_dump())

    # -- main tick ----------------------------------------------------------

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        cfg = self._config

        # Read embodiment state from context
        body = context.embodiment_state or {}

        # Compute raw channels from body state
        raw = _compute_raw_channels(body)

        # Apply exponential moving average smoothing
        smoothed: dict[str, float] = {}
        alpha = cfg.smoothing_alpha
        for name in _CHANNEL_NAMES:
            raw_val = raw.get(name, 0.0)
            if name in self._prev_channels:
                smoothed[name] = alpha * raw_val + (1.0 - alpha) * self._prev_channels[name]
            else:
                smoothed[name] = raw_val
            # Clamp
            smoothed[name] = max(0.0, min(1.0, smoothed[name]))

        # Detect threshold crossings and anomalies
        events: list[Event] = []
        alerts: list[str] = []

        for name in _CHANNEL_NAMES:
            value = smoothed[name]
            threshold = cfg.alert_thresholds.get(name, 0.6)

            # Threshold crossing
            if value >= threshold:
                alert_msg = f"{name}_above_threshold"
                alerts.append(alert_msg)
                events.append(Event(
                    tick=tick,
                    source_module="interoception",
                    event_type="threshold_crossed",
                    data={"channel": name, "value": value, "threshold": threshold},
                    severity=min(1.0, value),
                ))

            # Anomaly detection — sudden jump
            if name in self._prev_channels:
                delta = abs(value - self._prev_channels[name])
                if delta > cfg.anomaly_jump_threshold:
                    alert_msg = f"{name}_anomaly_jump"
                    alerts.append(alert_msg)
                    events.append(Event(
                        tick=tick,
                        source_module="interoception",
                        event_type="anomaly_detected",
                        data={"channel": name, "delta": delta, "value": value},
                        severity=min(1.0, delta * 2.0),
                    ))

        # Update history (rolling window)
        self._state.history.append(smoothed.copy())
        if len(self._state.history) > cfg.smoothing_window:
            self._state.history = self._state.history[-cfg.smoothing_window:]

        # Save current channels for next tick's smoothing / anomaly detection
        self._prev_channels = smoothed.copy()

        # Finalize state
        self._state.channels = smoothed
        self._state.alerts = alerts
        self._state.tick = tick

        state_dict = self._state.model_dump()
        return ModuleOutput(
            module_name="interoception",
            tick=tick,
            state=state_dict,
            events=events,
        )

    # -- event handler ------------------------------------------------------

    def on_event(self, event: Event) -> None:
        pass  # Interoception is a passive sensor; it does not react to events.
