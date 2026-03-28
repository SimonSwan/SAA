"""Default allostasis implementation — forecasts future internal state using trend extrapolation."""

from __future__ import annotations

from collections import deque
from typing import Any

from pydantic import BaseModel, Field

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseModule, BaseConfig, BaseState


class AllostasisState(BaseState):
    """Serializable state for the allostasis module."""

    module_name: str = "allostasis"
    version: str = "0.1.0"
    forecasts: dict[str, float] = Field(default_factory=dict)
    risk_scores: dict[str, float] = Field(default_factory=dict)
    anticipatory_actions: list[str] = Field(default_factory=list)


class AllostasisConfig(BaseConfig):
    """Configuration for the allostasis module."""

    horizon_ticks: int = 10
    risk_threshold: float = 0.6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _linear_regression(ys: list[float]) -> tuple[float, float]:
    """Return (slope, intercept) for y-values at x = 0, 1, ..., n-1."""
    n = len(ys)
    if n < 2:
        return 0.0, (ys[0] if ys else 0.0)
    x_mean = (n - 1) / 2.0
    y_mean = sum(ys) / n
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(ys))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0, y_mean
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept


def _extrapolate(ys: list[float], horizon: int) -> float:
    """Extrapolate the next *horizon* steps and return the predicted value."""
    slope, intercept = _linear_regression(ys)
    future_x = len(ys) - 1 + horizon
    return slope * future_x + intercept


# Critical thresholds per channel — values at or beyond these indicate crisis.
_CRITICAL_THRESHOLDS: dict[str, tuple[float, str]] = {
    "energy_deficit": (0.8, "high"),    # crisis when value goes HIGH
    "damage":         (0.8, "high"),
    "temperature":    (0.9, "high"),
    "fatigue":        (0.8, "high"),
    "hunger":         (0.9, "high"),
    "pain":           (0.8, "high"),
}

_DEFAULT_THRESHOLD = (0.8, "high")


def _risk_score(ys: list[float], horizon: int, channel: str) -> float:
    """Compute a 0-1 risk score for *channel* over *horizon* ticks.

    Risk is the ratio of the predicted value to its critical threshold,
    clamped to [0, 1].
    """
    predicted = _extrapolate(ys, horizon)
    threshold_val, direction = _CRITICAL_THRESHOLDS.get(channel, _DEFAULT_THRESHOLD)
    if direction == "high":
        return max(0.0, min(1.0, predicted / threshold_val)) if threshold_val else 0.0
    # If we ever add "low"-direction channels:
    return max(0.0, min(1.0, (1.0 - predicted) / (1.0 - threshold_val))) if threshold_val < 1.0 else 0.0


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

_HISTORY_LENGTH = 50  # how many past ticks to keep per channel


class DefaultAllostasis(BaseModule):
    """Anticipatory regulation through predictive modelling of internal state."""

    VERSION = "0.1.0"
    CAPABILITIES = ["forecast", "risk_assessment", "anticipatory_action"]
    DEPENDENCIES = ["interoception", "homeostasis"]

    def __init__(self) -> None:
        self._config = AllostasisConfig()
        self._state = AllostasisState()
        # channel_name -> deque of recent values
        self._history: dict[str, deque[float]] = {}

    # ------------------------------------------------------------------
    # BaseModule interface
    # ------------------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = AllostasisConfig(**config)
        self._state = AllostasisState()
        self._history = {}

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        self._state.tick = tick

        # ---- 1. Ingest interoceptive data --------------------------------
        intero = context.interoceptive_vector or {}
        homeo_err = context.homeostatic_error or {}

        for channel, value in intero.items():
            if not isinstance(value, (int, float)):
                continue
            if channel not in self._history:
                self._history[channel] = deque(maxlen=_HISTORY_LENGTH)
            self._history[channel].append(float(value))

        # ---- 2. Forecast & risk per channel ------------------------------
        forecasts: dict[str, float] = {}
        risk_scores: dict[str, float] = {}

        for channel, history in self._history.items():
            if len(history) < 2:
                forecasts[channel] = float(history[-1]) if history else 0.0
                risk_scores[channel] = 0.0
                continue
            ys = list(history)
            forecasts[channel] = _extrapolate(ys, self._config.horizon_ticks)
            risk_scores[channel] = _risk_score(ys, self._config.horizon_ticks, channel)

        self._state.forecasts = forecasts
        self._state.risk_scores = risk_scores

        # ---- 3. Anticipatory actions -------------------------------------
        actions: list[str] = []
        if risk_scores.get("energy_deficit", 0.0) > self._config.risk_threshold:
            actions.append("conserve")
        if risk_scores.get("damage", 0.0) > self._config.risk_threshold:
            actions.append("withdraw")
        if risk_scores.get("fatigue", 0.0) > self._config.risk_threshold:
            actions.append("rest")
        if risk_scores.get("hunger", 0.0) > self._config.risk_threshold:
            actions.append("consume")
        self._state.anticipatory_actions = actions

        # ---- 4. Events ---------------------------------------------------
        events: list[Event] = []
        crisis_channels = {
            ch: score
            for ch, score in risk_scores.items()
            if score > self._config.risk_threshold
        }
        if crisis_channels:
            events.append(
                Event(
                    tick=tick,
                    source_module="allostasis",
                    event_type="predicted_crisis",
                    data={
                        "risk_scores": crisis_channels,
                        "anticipatory_actions": actions,
                        "horizon_ticks": self._config.horizon_ticks,
                    },
                    severity=max(crisis_channels.values()),
                )
            )

        # ---- 5. Publish forecast into context ----------------------------
        output_state = self._state.model_dump()
        return ModuleOutput(
            module_name="allostasis",
            tick=tick,
            state=output_state,
            events=events,
        )

    def get_state(self) -> AllostasisState:
        return self._state.model_copy(deep=True)

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, AllostasisState):
            self._state = state.model_copy(deep=True)
        else:
            self._state = AllostasisState(**state.model_dump())

    def reset(self) -> None:
        self._state = AllostasisState()
        self._history.clear()
