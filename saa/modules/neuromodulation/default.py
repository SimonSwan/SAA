"""DefaultNeuromodulation — eight synthetic modulators that alter system-wide behavior.

Each modulator is maintained in [0.0, 1.0] and drifts toward its baseline via
exponential decay.  Inputs from embodiment, interoception, homeostasis, and
social modules drive accumulation.  Parameter shifts are computed every tick to
influence downstream modules (planning depth, exploration, vigilance, etc.).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASELINE: dict[str, float] = {
    "reward_drive": 0.5,
    "stress_load": 0.2,
    "trust_level": 0.5,
    "baseline_stability": 0.7,
    "damage_salience": 0.3,
    "curiosity_drive": 0.5,
    "grief_persistence": 0.0,
    "social_dependency": 0.3,
}

_DECAY_RATES: dict[str, float] = {
    "reward_drive": 0.08,
    "stress_load": 0.03,
    "trust_level": 0.02,
    "baseline_stability": 0.04,
    "damage_salience": 0.015,
    "curiosity_drive": 0.06,
    "grief_persistence": 0.005,
    "social_dependency": 0.03,
}

_ACCUMULATION_RATES: dict[str, float] = {
    "reward_drive": 0.10,
    "stress_load": 0.12,
    "trust_level": 0.06,
    "baseline_stability": 0.05,
    "damage_salience": 0.15,
    "curiosity_drive": 0.08,
    "grief_persistence": 0.10,
    "social_dependency": 0.06,
}


# ---------------------------------------------------------------------------
# State & Config
# ---------------------------------------------------------------------------

class NeuromodulationState(BaseState):
    """Serializable snapshot of all modulator values and parameter shifts."""

    module_name: str = "neuromodulation"
    version: str = "0.1.0"

    modulators: dict[str, float] = Field(default_factory=lambda: dict(_BASELINE))
    parameter_shifts: dict[str, float] = Field(default_factory=dict)


class NeuromodulationConfig(BaseConfig):
    """Configuration knobs for the neuromodulation module."""

    decay_rates: dict[str, float] = Field(default_factory=lambda: dict(_DECAY_RATES))
    accumulation_rates: dict[str, float] = Field(default_factory=lambda: dict(_ACCUMULATION_RATES))
    baseline_values: dict[str, float] = Field(default_factory=lambda: dict(_BASELINE))


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class DefaultNeuromodulation(BaseModule):
    """Eight synthetic modulators that alter system-wide behavior."""

    VERSION = "0.1.0"
    CAPABILITIES = ["neuromodulation"]
    DEPENDENCIES = ["embodiment"]

    def __init__(self) -> None:
        self._state = NeuromodulationState()
        self._config = NeuromodulationConfig()

    # -- lifecycle ----------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = NeuromodulationConfig(**config)
        self._state = NeuromodulationState(
            modulators=dict(self._config.baseline_values),
        )

    def reset(self) -> None:
        self.initialize()

    # -- state persistence --------------------------------------------------

    def get_state(self) -> NeuromodulationState:
        return self._state.model_copy()

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, NeuromodulationState):
            self._state = state.model_copy()
        else:
            self._state = NeuromodulationState(**state.model_dump())

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _decay_toward_baseline(self, name: str, dt: float) -> None:
        """Exponentially decay a modulator toward its baseline."""
        current = self._state.modulators[name]
        baseline = self._config.baseline_values[name]
        rate = self._config.decay_rates[name]
        diff = baseline - current
        self._state.modulators[name] = self._clamp(current + diff * rate * dt)

    def _accumulate(self, name: str, amount: float) -> None:
        """Push a modulator upward (or downward if amount is negative)."""
        rate = self._config.accumulation_rates[name]
        self._state.modulators[name] = self._clamp(
            self._state.modulators[name] + amount * rate
        )

    # -- main tick ----------------------------------------------------------

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        s = self._state
        s.tick = tick
        dt = context.dt
        m = s.modulators

        # Read upstream context
        embodiment = context.embodiment_state or {}
        intero = context.interoceptive_vector or {}
        homeo_err = context.homeostatic_error or {}
        social = context.social_state or {}
        events = context.events

        # ---- Decay all modulators toward baseline -------------------------
        for name in list(m.keys()):
            self._decay_toward_baseline(name, dt)

        # ---- Accumulate based on inputs -----------------------------------

        # -- reward_drive: positive outcomes
        for event in events:
            if event.event_type in ("goal_achieved", "exploration_rewarded", "positive_outcome"):
                self._accumulate("reward_drive", 1.0)
            elif event.event_type in ("negative_outcome", "goal_failed"):
                self._accumulate("reward_drive", -0.5)

        # -- stress_load: threats, damage, homeostatic error
        damage = embodiment.get("damage", 0.0)
        strain = embodiment.get("strain", 0.0)
        hazard = context.environment.hazard_level
        total_homeo_error = sum(
            abs(v) for v in homeo_err.values() if isinstance(v, (int, float))
        )
        stress_input = damage * 0.4 + strain * 0.3 + hazard * 0.2 + min(total_homeo_error, 1.0) * 0.1
        if stress_input > 0.2:
            self._accumulate("stress_load", stress_input)

        # -- trust_level: social interactions
        trust_from_social = social.get("total_bond_strength", 0.0)
        if trust_from_social > 0:
            self._accumulate("trust_level", trust_from_social * 0.3)
        for event in events:
            if event.event_type == "trust_broken":
                self._accumulate("trust_level", -2.0)
            elif event.event_type == "attachment_formed":
                self._accumulate("trust_level", 0.5)

        # -- baseline_stability: decreases under sustained stress
        if m["stress_load"] > 0.5:
            self._accumulate("baseline_stability", -(m["stress_load"] - 0.5))

        # -- damage_salience: spikes on damage
        if damage > 0.3:
            self._accumulate("damage_salience", damage)
        for event in events:
            if event.event_type == "damage_critical":
                self._accumulate("damage_salience", 1.5)

        # -- curiosity_drive: suppressed by stress, boosted by novelty
        if m["stress_load"] > 0.5:
            self._accumulate("curiosity_drive", -(m["stress_load"] - 0.5) * 0.5)
        novelty = intero.get("novelty", 0.0)
        if novelty > 0.3:
            self._accumulate("curiosity_drive", novelty * 0.8)
        for event in events:
            if event.event_type == "novel_stimulus":
                self._accumulate("curiosity_drive", 0.6)

        # -- grief_persistence: accumulates on loss
        for event in events:
            if event.event_type in ("separation_stress", "loss_event", "attachment_lost"):
                self._accumulate("grief_persistence", 1.0)

        # -- social_dependency: positive attachment vs self-sufficiency
        attachment_risk = social.get("attachment_risk", 0.0)
        if attachment_risk > 0.3:
            self._accumulate("social_dependency", attachment_risk * 0.5)
        # Self-sufficiency signal: low stress + high baseline_stability
        if m["stress_load"] < 0.2 and m["baseline_stability"] > 0.6:
            self._accumulate("social_dependency", -0.3)

        # ---- Compute parameter shifts -------------------------------------

        shifts: dict[str, float] = {}

        # High stress_load effects
        shifts["planning_depth"] = -m["stress_load"] * 0.5
        shifts["action_urgency"] = m["stress_load"] * 0.6
        shifts["exploration_modifier"] = -m["stress_load"] * 0.4

        # High grief_persistence effects
        shifts["memory_loss_bias"] = m["grief_persistence"] * 0.5
        shifts["social_approach"] = -m["grief_persistence"] * 0.4

        # High curiosity_drive effects
        shifts["exploration_modifier"] = shifts.get("exploration_modifier", 0.0) + m["curiosity_drive"] * 0.5
        shifts["risk_avoidance_modifier"] = -m["curiosity_drive"] * 0.3

        # High damage_salience effects
        shifts["vigilance"] = m["damage_salience"] * 0.6
        shifts["risk_tolerance"] = -m["damage_salience"] * 0.5

        # Low trust_level effects
        trust_deficit = max(0.0, 0.5 - m["trust_level"])
        shifts["social_weighting"] = -trust_deficit * 0.6
        shifts["self_reliance"] = trust_deficit * 0.5

        s.parameter_shifts = {k: round(v, 4) for k, v in shifts.items()}

        # ---- Events for extreme states ------------------------------------

        events_out: list[Event] = []

        if m["stress_load"] > 0.8:
            events_out.append(Event(
                tick=tick,
                source_module="neuromodulation",
                event_type="extreme_stress",
                data={"stress_load": round(m["stress_load"], 4)},
                severity=0.85,
            ))
        if m["grief_persistence"] > 0.6:
            events_out.append(Event(
                tick=tick,
                source_module="neuromodulation",
                event_type="grief_elevated",
                data={"grief_persistence": round(m["grief_persistence"], 4)},
                severity=0.7,
            ))
        if m["baseline_stability"] < 0.3:
            events_out.append(Event(
                tick=tick,
                source_module="neuromodulation",
                event_type="stability_compromised",
                data={"baseline_stability": round(m["baseline_stability"], 4)},
                severity=0.8,
            ))
        if m["damage_salience"] > 0.8:
            events_out.append(Event(
                tick=tick,
                source_module="neuromodulation",
                event_type="damage_hypervigilance",
                data={"damage_salience": round(m["damage_salience"], 4)},
                severity=0.6,
            ))
        if m["curiosity_drive"] > 0.85:
            events_out.append(Event(
                tick=tick,
                source_module="neuromodulation",
                event_type="high_curiosity",
                data={"curiosity_drive": round(m["curiosity_drive"], 4)},
                severity=0.3,
            ))

        # Round modulator values for cleanliness
        s.modulators = {k: round(v, 4) for k, v in s.modulators.items()}

        state_dict = s.model_dump()
        return ModuleOutput(
            module_name="neuromodulation",
            tick=tick,
            state=state_dict,
            events=events_out,
        )

    # -- event handler ------------------------------------------------------

    def on_event(self, event: Event) -> None:
        if event.event_type == "damage_critical":
            self._accumulate("damage_salience", 1.0)
            self._accumulate("stress_load", 0.8)
        elif event.event_type == "critical_energy_low":
            self._accumulate("stress_load", 0.5)
        elif event.event_type == "trust_broken":
            self._accumulate("trust_level", -1.5)
            self._accumulate("social_dependency", -0.5)
        elif event.event_type == "separation_stress":
            self._accumulate("grief_persistence", 0.8)
            self._accumulate("social_dependency", 0.3)
