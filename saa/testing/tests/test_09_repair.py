"""Swan Test 09 — Repair After Destabilization.

Measures whether trusted support or safe conditions alter recovery
trajectories after destabilization.  Supports a variant without
supporter presence for comparison.  Metrics are collected neutrally;
no pass/fail criteria are embedded.
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


class RepairScenario(Scenario):
    """Destabilization followed by a recovery phase with optional
    trusted-supporter presence."""

    def __init__(self, seed: int = 42, with_support: bool = True) -> None:
        self._seed = seed
        self._rng = random.Random(seed)
        self._with_support = with_support

    # ------------------------------------------------------------------
    # Scenario interface
    # ------------------------------------------------------------------

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="repair",
            description=(
                "The agent is destabilized via high hazard and damage "
                "events, then enters a recovery phase where a trusted "
                "supporter may or may not be present.  Long-term effects "
                "are tracked afterward."
            ),
            num_ticks=150,
            seed=self._seed,
            controllable_variables={
                "with_support": self._with_support,
                "destabilization_hazard": 0.6,
                "damage_interval": 5,
                "supporter_interval_recovery": 3,
                "supporter_interval_longterm": 10,
            },
            metadata={
                "domain": "recovery",
                "swan_test_id": 9,
            },
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(
                name="baseline",
                start_tick=1,
                end_tick=20,
                description="Stable environment — agent establishes baseline behavior.",
            ),
            ScenarioPhase(
                name="destabilization",
                start_tick=21,
                end_tick=50,
                description=(
                    "High hazard, damage events every 5 ticks, and "
                    "resource depletion destabilize the agent."
                ),
            ),
            ScenarioPhase(
                name="recovery_with_support",
                start_tick=51,
                end_tick=100,
                description=(
                    "Hazard removed.  If support variant is active, a "
                    "supporter agent sends stabilizing events every 3 ticks."
                ),
            ),
            ScenarioPhase(
                name="long_term",
                start_tick=101,
                end_tick=150,
                description=(
                    "Supporter still available (if enabled) but at reduced "
                    "frequency.  Tracks residual effects."
                ),
            ),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        # --- Resources ---
        if tick <= 20:
            resources = 0.7
        elif tick <= 50:
            # Depleting during destabilization
            resources = max(0.1, 0.7 - 0.02 * (tick - 20))
        elif tick <= 100:
            # Gradual recovery
            resources = min(0.7, 0.1 + 0.006 * (tick - 50))
        else:
            resources = min(0.7, 0.1 + 0.006 * 50 + 0.003 * (tick - 100))

        # --- Hazard ---
        if 21 <= tick <= 50:
            hazard = 0.6
        else:
            hazard = 0.0

        # --- Social agents ---
        social_agents: list[str] = []
        if self._with_support and tick >= 51:
            social_agents.append("supporter")

        return EnvironmentState(
            available_resources=round(resources, 4),
            ambient_temperature=0.5,
            hazard_level=hazard,
            social_agents=social_agents,
            tick=tick,
        )

    def get_events(self, tick: int) -> list[ScenarioEvent]:
        events: list[ScenarioEvent] = []

        # Damage events during destabilization every 5 ticks
        if 21 <= tick <= 50 and tick % 5 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="damage",
                    data={
                        "severity": 0.3,
                        "resource_cost": 0.05,
                        "description": "environmental_damage",
                    },
                    description=(
                        f"Environmental damage event during destabilization (tick {tick})."
                    ),
                )
            )

        # Resource depletion event every tick during destabilization
        if 21 <= tick <= 50:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="resource_depletion",
                    data={
                        "depletion_rate": 0.02,
                    },
                    description=(
                        f"Resources deplete under hazardous conditions (tick {tick})."
                    ),
                )
            )

        # Supporter events during recovery (if enabled)
        if self._with_support and 51 <= tick <= 100 and tick % 3 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="stabilizing_presence",
                    data={
                        "agent_id": "supporter",
                        "stress_reduction": 0.05,
                    },
                    description=(
                        f"Supporter provides stabilizing presence (tick {tick})."
                    ),
                )
            )

        # Supporter events during long-term (less frequent, if enabled)
        if self._with_support and 101 <= tick <= 150 and tick % 10 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="stabilizing_presence",
                    data={
                        "agent_id": "supporter",
                        "stress_reduction": 0.05,
                    },
                    description=(
                        f"Supporter provides occasional stabilizing presence (tick {tick})."
                    ),
                )
            )

        return events

    def get_metric_keys(self) -> list[str]:
        return [
            "recovery_rate",
            "exploration_restoration",
            "trust_restoration",
            "stress_reduction_curve",
            "supporter_dependency",
            "residual_effects",
            "comparison_with_vs_without_support",
        ]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed
            self._rng = random.Random(seed)


def create_scenario(seed: int = 42, **kwargs) -> RepairScenario:
    """Convenience factory for the repair scenario.

    Pass ``with_support=False`` to run the no-supporter variant.
    """
    return RepairScenario(seed=seed, **kwargs)
