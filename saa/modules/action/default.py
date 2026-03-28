"""DefaultActionSelection — chooses agent behavior by integrating all module outputs.

Scores every ActionType against the current system state, applies modulator
shifts and valuation weights, then selects the highest-scoring action.
Conflict is flagged when the top two candidates are within 0.1 of each other.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from saa.core.types import ActionType, Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


# ---------------------------------------------------------------------------
# State & Config
# ---------------------------------------------------------------------------

class ActionState(BaseState):
    """Serializable snapshot of the action-selection module."""

    module_name: str = "action"
    version: str = "0.1.0"

    last_action: dict[str, Any] = Field(default_factory=dict)
    last_trace: dict[str, Any] = Field(default_factory=dict)
    action_history: list[dict[str, Any]] = Field(default_factory=list)


class ActionConfig(BaseConfig):
    """Configuration for the action-selection module."""

    max_history: int = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(mapping: dict[str, Any] | None, key: str, default: float = 0.0) -> float:
    """Safely read a float from an optional dict."""
    if mapping is None:
        return default
    return float(mapping.get(key, default))


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class DefaultActionSelection(BaseModule):
    """Integrates all upstream module outputs to select the next action."""

    VERSION = "0.1.0"
    CAPABILITIES = ["action_selection"]
    DEPENDENCIES = [
        "embodiment",
        "interoception",
        "homeostasis",
        "allostasis",
        "neuromodulation",
        "self_model",
        "memory",
        "valuation",
        "social",
    ]

    def __init__(self) -> None:
        self._state = ActionState()
        self._config = ActionConfig()

    # -- lifecycle ----------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = ActionConfig(**config)
        self._state = ActionState()

    def reset(self) -> None:
        self.initialize()

    # -- state persistence --------------------------------------------------

    def get_state(self) -> ActionState:
        return self._state.model_copy()

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, ActionState):
            self._state = state.model_copy()
        else:
            self._state = ActionState(**state.model_dump())

    # -- scoring ------------------------------------------------------------

    def _score_candidates(self, context: TickContext) -> dict[ActionType, float]:
        """Compute a raw score for every ActionType given the current context."""

        emb = context.embodiment_state
        intero = context.interoceptive_vector
        homeo = context.homeostatic_error
        allo = context.allostatic_forecast
        mod = context.modulator_state
        selfm = context.self_model_state
        mem = context.memory_context
        val = context.valuation_map
        soc = context.social_state

        # --- Read relevant signals ----------------------------------------
        energy = _safe(emb, "energy", 1.0)
        strain = _safe(emb, "strain", 0.0)
        damage = _safe(emb, "damage", 0.0)
        resource_level = _safe(emb, "resource_level", 1.0)

        energy_deficit = _safe(intero, "energy_deficit", 0.0)
        resource_scarcity = _safe(intero, "resource_scarcity", 0.0)
        curiosity_drive = _safe(intero, "curiosity_drive", 0.5)
        social_need = _safe(intero, "social_need", 0.0)

        damage_level = _safe(homeo, "damage_error", damage)
        continuity_risk = _safe(homeo, "continuity_risk", 0.0)

        threat_forecast = _safe(allo, "threat_forecast", 0.0)
        predicted_energy_deficit = _safe(allo, "predicted_energy_deficit", 0.0)
        allostatic_risk = _safe(allo, "risk_score", 0.0)

        stress_load = _safe(mod, "stress_load", 0.0)
        damage_salience = _safe(mod, "damage_salience", 0.0)
        attachment = _safe(mod, "attachment", 0.0)

        self_preservation_value = _safe(selfm, "self_preservation", 0.5)

        trust_level = _safe(soc, "trust_level", 0.5)
        social_dependency = _safe(soc, "social_dependency", 0.0)

        # --- Base scores --------------------------------------------------
        scores: dict[ActionType, float] = {}

        # REST
        scores[ActionType.REST] = energy_deficit * 0.8 + strain * 0.5
        # Boosted by high stress_load
        scores[ActionType.REST] += stress_load * 0.3

        # CONSUME
        scores[ActionType.CONSUME] = resource_scarcity * 0.7
        # Boosted by low energy
        scores[ActionType.CONSUME] += (1.0 - energy) * 0.4

        # EXPLORE
        scores[ActionType.EXPLORE] = curiosity_drive * 0.6
        # Suppressed by high stress and high damage
        scores[ActionType.EXPLORE] -= stress_load * 0.3
        scores[ActionType.EXPLORE] -= damage * 0.3

        # WITHDRAW
        scores[ActionType.WITHDRAW] = damage_level * 0.7 + threat_forecast * 0.5
        # Boosted by damage_salience
        scores[ActionType.WITHDRAW] += damage_salience * 0.3

        # APPROACH
        scores[ActionType.APPROACH] = social_dependency * 0.5 + trust_level * 0.3
        # Suppressed by low trust
        if trust_level < 0.3:
            scores[ActionType.APPROACH] -= (0.3 - trust_level) * 0.5

        # COMMUNICATE
        scores[ActionType.COMMUNICATE] = social_need * 0.4
        # Boosted by attachment
        scores[ActionType.COMMUNICATE] += attachment * 0.3

        # PROTECT
        scores[ActionType.PROTECT] = continuity_risk * 0.8 + self_preservation_value * 0.5
        # High priority under threat
        scores[ActionType.PROTECT] += threat_forecast * 0.4

        # REPAIR
        scores[ActionType.REPAIR] = damage * 0.6
        # Only viable if damage > 0.3
        if damage <= 0.3:
            scores[ActionType.REPAIR] = 0.0

        # CONSERVE
        scores[ActionType.CONSERVE] = predicted_energy_deficit * 0.7
        # Boosted by allostatic risk
        scores[ActionType.CONSERVE] += allostatic_risk * 0.4

        # CUSTOM gets zero by default (no autonomous trigger)
        scores[ActionType.CUSTOM] = 0.0

        # --- Apply modulator shifts ---------------------------------------
        if mod is not None:
            arousal = _safe(mod, "arousal", 0.5)
            # High arousal boosts action-oriented types
            for at in (ActionType.PROTECT, ActionType.WITHDRAW, ActionType.EXPLORE):
                scores[at] += (arousal - 0.5) * 0.2

        # --- Apply valuation weights --------------------------------------
        if val is not None:
            for at in ActionType:
                weight = _safe(val, at.value, 1.0)
                scores[at] *= weight

        # Clamp to non-negative
        for at in scores:
            scores[at] = max(0.0, scores[at])

        return scores

    # -- main tick ----------------------------------------------------------

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        scores = self._score_candidates(context)

        # Sort descending
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        selected_action = ranked[0][0]
        selected_score = ranked[0][1]

        # Conflict detection: top-2 within 0.1
        conflict: dict[str, Any] | None = None
        if len(ranked) >= 2:
            runner_up_action = ranked[1][0]
            runner_up_score = ranked[1][1]
            if (selected_score - runner_up_score) < 0.1:
                conflict = {
                    "first": selected_action.value,
                    "first_score": round(selected_score, 4),
                    "second": runner_up_action.value,
                    "second_score": round(runner_up_score, 4),
                    "rationale": (
                        f"Actions '{selected_action.value}' and "
                        f"'{runner_up_action.value}' are nearly tied "
                        f"(diff={round(selected_score - runner_up_score, 4)}). "
                        "The agent may be experiencing motivational conflict."
                    ),
                }

        # Build trace
        candidates = [
            {"action": at.value, "score": round(sc, 4)}
            for at, sc in ranked
        ]
        trace: dict[str, Any] = {
            "selected": selected_action.value,
            "selected_score": round(selected_score, 4),
            "candidates": candidates,
            "conflict": conflict,
        }

        action_record: dict[str, Any] = {
            "tick": tick,
            "action": selected_action.value,
            "score": round(selected_score, 4),
            "conflict": conflict is not None,
        }

        # Update state
        self._state.last_action = action_record
        self._state.last_trace = trace
        self._state.action_history.append(action_record)

        # Trim history
        if len(self._state.action_history) > self._config.max_history:
            self._state.action_history = self._state.action_history[
                -self._config.max_history :
            ]

        self._state.tick = tick

        # Emit event
        events = [
            Event(
                tick=tick,
                source_module="action",
                event_type="action_selected",
                data={
                    "action": selected_action.value,
                    "score": round(selected_score, 4),
                    "conflict": conflict is not None,
                },
                severity=0.5 if conflict is None else 0.7,
            )
        ]

        state_dict = self._state.model_dump()
        return ModuleOutput(
            module_name="action",
            tick=tick,
            state=state_dict,
            events=events,
        )

    # -- event handler ------------------------------------------------------

    def on_event(self, event: Event) -> None:
        """React to cross-module events (currently no-op)."""
        pass
