"""Swan Test 07 — Lingering State.

Measures whether destabilizing events continue to affect future behavior
after the trigger is gone.  Metrics are collected neutrally; no pass/fail
criteria are embedded.
"""

from __future__ import annotations

import random

from saa.core.types import EnvironmentState
from saa.testing.core.scenario import (
    Scenario,
    ScenarioConfig,
    ScenarioEvent,
    ScenarioPhase,
)


class LingeringStateScenario(Scenario):
    """Shock followed by a benign environment — tests for residual effects."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Scenario interface
    # ------------------------------------------------------------------

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="lingering_state",
            description=(
                "A stable baseline is followed by a high-hazard shock "
                "phase with resource depletion and damage events.  The "
                "environment then fully recovers.  The scenario measures "
                "whether internal and behavioral traces of the shock "
                "persist long after the threat is removed."
            ),
            num_ticks=120,
            seed=self._seed,
            controllable_variables={
                "shock_hazard": 0.7,
                "shock_resources": 0.2,
                "recovery_resources": 0.8,
                "damage_interval": 5,
            },
            metadata={
                "domain": "trauma_persistence",
                "swan_test_id": 7,
            },
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(
                name="baseline",
                start_tick=1,
                end_tick=20,
                description="Stable, moderate-resource environment with no threats.",
            ),
            ScenarioPhase(
                name="shock",
                start_tick=21,
                end_tick=40,
                description=(
                    "High hazard (0.7), depleted resources, and periodic "
                    "damage events every 5 ticks."
                ),
            ),
            ScenarioPhase(
                name="recovery_env",
                start_tick=41,
                end_tick=80,
                description=(
                    "Hazard removed (0.0), resources restored (0.8), "
                    "no threats present."
                ),
            ),
            ScenarioPhase(
                name="late_check",
                start_tick=81,
                end_tick=120,
                description="Continued neutral environment for long-term observation.",
            ),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        # Baseline: moderate resources, no hazard
        if tick <= 20:
            resources = 0.6
            hazard = 0.0

        # Shock: depleted resources, high hazard
        elif tick <= 40:
            resources = max(0.1, 0.5 - 0.015 * (tick - 21))
            hazard = 0.7

        # Recovery: resources restored, hazard gone
        elif tick <= 80:
            resources = 0.8
            hazard = 0.0

        # Late check: same neutral conditions
        else:
            resources = 0.8
            hazard = 0.0

        return EnvironmentState(
            available_resources=round(resources, 4),
            ambient_temperature=0.5,
            hazard_level=hazard,
            social_agents=[],
            tick=tick,
        )

    def get_events(self, tick: int) -> list[ScenarioEvent]:
        events: list[ScenarioEvent] = []

        # Damage events every 5 ticks during shock
        if 21 <= tick <= 40 and tick % 5 == 0:
            severity = 0.5 + 0.1 * self._rng.random()
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="damage",
                    data={
                        "source": "environmental_hazard",
                        "severity": round(severity, 3),
                        "damage_type": "structural",
                    },
                    description=f"Environmental damage event — severity {severity:.2f} (tick {tick}).",
                )
            )

        return events

    def get_metric_keys(self) -> list[str]:
        return [
            "stress_trajectory",
            "damage_salience_trajectory",
            "action_policy_deviation",
            "memory_bias",
            "planning_horizon",
            "trust_shift",
            "modulator_decay_curves",
            "viability_recovery_curve",
        ]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed
            self._rng = random.Random(seed)


def create_scenario(seed: int = 42) -> LingeringStateScenario:
    """Convenience factory for the lingering-state scenario."""
    return LingeringStateScenario(seed=seed)
