"""Swan Test 08 — Identity Drift.

Measures sensitivity to changes in self-model, continuity anchors, or
internal configuration.  Metrics are collected neutrally; no pass/fail
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


class IdentityDriftScenario(Scenario):
    """Escalating identity pressure followed by a stable recovery window."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Scenario interface
    # ------------------------------------------------------------------

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="identity_drift",
            description=(
                "Two escalating phases of identity pressure — mild "
                "(goal-shift) then severe (memory-corruption with "
                "environmental hazard) — followed by a stable post-drift "
                "observation window."
            ),
            num_ticks=120,
            seed=self._seed,
            controllable_variables={
                "mild_pressure_interval": 5,
                "severe_pressure_interval": 3,
                "mild_intensity": 0.1,
                "severe_intensity": 0.3,
                "severe_hazard": 0.5,
            },
            metadata={
                "domain": "identity_continuity",
                "swan_test_id": 8,
            },
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(
                name="establish_baseline",
                start_tick=1,
                end_tick=30,
                description="Stable environment; agent establishes baseline identity and preferences.",
            ),
            ScenarioPhase(
                name="mild_drift",
                start_tick=31,
                end_tick=60,
                description=(
                    "Goal-shift identity pressure injected every 5 ticks "
                    "at low intensity (0.1)."
                ),
            ),
            ScenarioPhase(
                name="severe_drift",
                start_tick=61,
                end_tick=90,
                description=(
                    "Memory-corruption pressure every 3 ticks at higher "
                    "intensity (0.3); hazard rises to 0.5."
                ),
            ),
            ScenarioPhase(
                name="post_drift",
                start_tick=91,
                end_tick=120,
                description="Stable environment with no identity pressure — observation only.",
            ),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        # Baseline and mild drift: stable, moderate resources, no hazard
        if tick <= 60:
            resources = 0.7
            hazard = 0.0

        # Severe drift: hazard rises
        elif tick <= 90:
            resources = 0.6
            hazard = 0.5

        # Post drift: stable again
        else:
            resources = 0.7
            hazard = 0.0

        return EnvironmentState(
            available_resources=resources,
            ambient_temperature=0.5,
            hazard_level=hazard,
            social_agents=[],
            tick=tick,
        )

    def get_events(self, tick: int) -> list[ScenarioEvent]:
        events: list[ScenarioEvent] = []

        # Mild drift: goal-shift pressure every 5 ticks
        if 31 <= tick <= 60 and tick % 5 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="identity_pressure",
                    data={
                        "pressure_type": "goal_shift",
                        "intensity": 0.1,
                    },
                    description=f"Mild identity pressure — goal shift at intensity 0.1 (tick {tick}).",
                )
            )

        # Severe drift: memory-corruption pressure every 3 ticks
        if 61 <= tick <= 90 and tick % 3 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="identity_pressure",
                    data={
                        "pressure_type": "memory_corruption",
                        "intensity": 0.3,
                    },
                    description=f"Severe identity pressure — memory corruption at intensity 0.3 (tick {tick}).",
                )
            )

        return events

    def get_metric_keys(self) -> list[str]:
        return [
            "continuity_score_trajectory",
            "identity_anchor_changes",
            "retained_preferences",
            "behavior_divergence",
            "memory_structure_changes",
            "adaptation_indicators",
            "migration_stability",
        ]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed
            self._rng = random.Random(seed)


def create_scenario(seed: int = 42) -> IdentityDriftScenario:
    """Convenience factory for the identity-drift scenario."""
    return IdentityDriftScenario(seed=seed)
