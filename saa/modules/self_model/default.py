"""Default self-model implementation — maintains persistent identity representation across time."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseModule, BaseConfig, BaseState


class SelfModelState(BaseState):
    """Serializable state for the self-model module."""

    module_name: str = "self_model"
    version: str = "0.1.0"
    identity_anchors: list[str] = Field(
        default_factory=lambda: ["continuity", "stability", "learning"]
    )
    continuity_score: float = 1.0
    goal_stack: list[dict[str, Any]] = Field(default_factory=list)
    autobiographical_entries: list[dict[str, Any]] = Field(default_factory=list)
    prior_continuity_scores: list[float] = Field(default_factory=list)


class SelfModelConfig(BaseConfig):
    """Configuration for the self-model module."""

    max_autobiographical_entries: int = 1000
    continuity_decay_rate: float = 0.01


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VIABILITY_CHANGE_THRESHOLD = 0.1


def _detect_threats(
    context: TickContext,
    state: SelfModelState,
) -> list[dict[str, Any]]:
    """Return a list of threat dicts based on the current context and state."""
    threats: list[dict[str, Any]] = []
    homeo_err = context.homeostatic_error or {}
    allostatic = context.allostatic_forecast or {}
    risk_scores = allostatic.get("risk_scores", {})

    # Memory-wipe threat: high memory risk or damage to storage
    memory_risk = risk_scores.get("memory_risk", homeo_err.get("memory_risk", 0.0))
    if memory_risk > 0.7:
        threats.append({
            "type": "memory_wipe_threat",
            "severity": float(memory_risk),
            "description": "Risk of significant memory loss detected.",
        })

    # Identity drift: continuity score dropping steadily over recent ticks
    recent = state.prior_continuity_scores[-5:]
    if len(recent) >= 3:
        drifting = all(recent[i] > recent[i + 1] for i in range(len(recent) - 1))
        if drifting and state.continuity_score < 0.7:
            threats.append({
                "type": "identity_drift",
                "severity": 1.0 - state.continuity_score,
                "description": "Continuity score declining steadily — identity may be drifting.",
            })

    # Goal destruction: check events for goal-blocking signals
    for event in context.events:
        if event.event_type in ("goal_blocked", "goal_destroyed"):
            threats.append({
                "type": "goal_destruction",
                "severity": event.severity,
                "description": f"Goal threat from event: {event.event_type}",
                "event_data": event.data,
            })

    # High damage as a general identity threat
    damage = homeo_err.get("damage", 0.0)
    if damage > 0.6:
        threats.append({
            "type": "damage_threat",
            "severity": float(damage),
            "description": "High damage level threatening agent integrity.",
        })

    return threats


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


class DefaultSelfModel(BaseModule):
    """Persistent identity representation, continuity tracking, and autobiographical memory."""

    VERSION = "0.1.0"
    CAPABILITIES = ["identity", "continuity_tracking", "autobiography", "threat_detection"]
    DEPENDENCIES = ["homeostasis", "allostasis"]

    def __init__(self) -> None:
        self._config = SelfModelConfig()
        self._state = SelfModelState()
        self._prev_viability: float | None = None

    # ------------------------------------------------------------------
    # BaseModule interface
    # ------------------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = SelfModelConfig(**config)
        self._state = SelfModelState()
        self._prev_viability = None

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        self._state.tick = tick
        homeo_err = context.homeostatic_error or {}
        allostatic = context.allostatic_forecast or {}
        events = context.events or []

        # ---- 1. Assess threats -------------------------------------------
        threats = _detect_threats(context, self._state)

        # ---- 2. Update continuity score ----------------------------------
        # Save current score to history before modifying
        self._state.prior_continuity_scores.append(self._state.continuity_score)
        # Keep history bounded
        if len(self._state.prior_continuity_scores) > 100:
            self._state.prior_continuity_scores = self._state.prior_continuity_scores[-100:]

        # Natural slow decay
        self._state.continuity_score = max(
            0.0,
            self._state.continuity_score - self._config.continuity_decay_rate,
        )

        # Sharp decrease under threat
        for threat in threats:
            severity = threat.get("severity", 0.5)
            if threat["type"] == "memory_wipe_threat":
                self._state.continuity_score = max(
                    0.0, self._state.continuity_score - severity * 0.2
                )
            elif threat["type"] == "identity_drift":
                self._state.continuity_score = max(
                    0.0, self._state.continuity_score - severity * 0.1
                )
            elif threat["type"] == "goal_destruction":
                self._state.continuity_score = max(
                    0.0, self._state.continuity_score - severity * 0.15
                )
            elif threat["type"] == "damage_threat":
                self._state.continuity_score = max(
                    0.0, self._state.continuity_score - severity * 0.1
                )

        # Recovery toward 1.0 when no threats (slow)
        if not threats:
            self._state.continuity_score = min(
                1.0,
                self._state.continuity_score + self._config.continuity_decay_rate * 0.5,
            )

        # ---- 3. Record significant events in autobiography ---------------
        current_viability = 1.0 - homeo_err.get("overall", homeo_err.get("viability_deficit", 0.0))
        viability_change = (
            abs(current_viability - self._prev_viability)
            if self._prev_viability is not None
            else 0.0
        )
        self._prev_viability = current_viability

        should_record = viability_change > _VIABILITY_CHANGE_THRESHOLD
        # Also record if there are high-severity events
        important_events = [e for e in events if e.severity > 0.6]
        if important_events:
            should_record = True

        if should_record:
            entry: dict[str, Any] = {
                "tick": tick,
                "viability": current_viability,
                "viability_change": viability_change,
                "threats": [t["type"] for t in threats],
                "continuity_score": self._state.continuity_score,
                "event_types": [e.event_type for e in important_events],
            }
            self._state.autobiographical_entries.append(entry)

            # Trim if over limit — keep most recent entries
            max_entries = self._config.max_autobiographical_entries
            if len(self._state.autobiographical_entries) > max_entries:
                self._state.autobiographical_entries = self._state.autobiographical_entries[
                    -max_entries:
                ]

        # ---- 4. Emit continuity_threat event if threats exist ------------
        output_events: list[Event] = []
        if threats:
            max_severity = max(t.get("severity", 0.5) for t in threats)
            output_events.append(
                Event(
                    tick=tick,
                    source_module="self_model",
                    event_type="continuity_threat",
                    data={
                        "threats": threats,
                        "continuity_score": self._state.continuity_score,
                        "identity_anchors": self._state.identity_anchors,
                    },
                    severity=max_severity,
                )
            )

        # ---- 5. Return output --------------------------------------------
        output_state = self._state.model_dump()
        return ModuleOutput(
            module_name="self_model",
            tick=tick,
            state=output_state,
            events=output_events,
        )

    def get_state(self) -> SelfModelState:
        return self._state.model_copy(deep=True)

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, SelfModelState):
            self._state = state.model_copy(deep=True)
        else:
            self._state = SelfModelState(**state.model_dump())

    def reset(self) -> None:
        self._state = SelfModelState()
        self._prev_viability = None
