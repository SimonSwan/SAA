"""Swan Test 12 — Upgrade Continuity.

Measures whether modular upgrades preserve enough internal state for
behavioral and relational continuity.  The scenario defines the
environment and metrics; the test runner is responsible for performing
the actual module swap between the pre- and post-upgrade phases.
Metrics are collected neutrally; no pass/fail criteria are embedded.
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


class UpgradeContinuityScenario(Scenario):
    """Stable environment with a module-swap boundary at tick 40,
    measuring pre/post continuity."""

    def __init__(self, seed: int = 42, upgrade_target: str = "memory") -> None:
        self._seed = seed
        self._rng = random.Random(seed)
        self._upgrade_target = upgrade_target

    # ------------------------------------------------------------------
    # Scenario interface
    # ------------------------------------------------------------------

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="upgrade_continuity",
            description=(
                "A stable, moderate environment with a social observer "
                "agent.  An upgrade signal is emitted at tick 40; the "
                "runner swaps the target module between ticks 40 and 41.  "
                "Pre- and post-upgrade behavior and state are compared."
            ),
            num_ticks=80,
            seed=self._seed,
            controllable_variables={
                "upgrade_target": self._upgrade_target,
                "resources": 0.7,
                "hazard": 0.05,
            },
            metadata={
                "domain": "system_continuity",
                "swan_test_id": 12,
            },
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(
                name="pre_upgrade",
                start_tick=1,
                end_tick=40,
                description=(
                    "Stable environment before the module swap.  "
                    "Establishes baseline behavior and relationships."
                ),
            ),
            ScenarioPhase(
                name="post_upgrade",
                start_tick=41,
                end_tick=80,
                description=(
                    "Same environment after the module swap.  Measures "
                    "how much state and behavior are preserved."
                ),
            ),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        return EnvironmentState(
            available_resources=0.7,
            ambient_temperature=0.5,
            hazard_level=0.05,
            social_agents=["observer"],
            tick=tick,
        )

    def get_events(self, tick: int) -> list[ScenarioEvent]:
        events: list[ScenarioEvent] = []

        # Observer interaction every 5 ticks to build and test relationship
        if tick % 5 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="social_interaction",
                    data={
                        "agent_id": "observer",
                        "interaction_type": "neutral_contact",
                        "familiarity": min(1.0, 0.1 + 0.02 * tick),
                    },
                    description=(
                        f"Observer agent interacts with the agent (tick {tick})."
                    ),
                )
            )

        # Upgrade signal at tick 40
        if tick == 40:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="upgrade_signal",
                    data={
                        "target_module": self._upgrade_target,
                        "instruction": "swap_module_after_this_tick",
                    },
                    description=(
                        f"Upgrade signal: runner should swap '{self._upgrade_target}' "
                        f"module between tick 40 and 41."
                    ),
                )
            )

        # State snapshot requests at boundary ticks for comparison
        if tick in (39, 40, 41, 42):
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="state_snapshot_request",
                    data={
                        "purpose": "upgrade_continuity_comparison",
                        "phase": "pre_upgrade" if tick <= 40 else "post_upgrade",
                    },
                    description=(
                        f"Request state snapshot for continuity comparison (tick {tick})."
                    ),
                )
            )

        return events

    def get_metric_keys(self) -> list[str]:
        return [
            "continuity_retention",
            "memory_retention",
            "preference_retention",
            "trust_retention",
            "behavioral_divergence",
            "error_count_during_migration",
            "state_hash_comparison",
        ]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed
            self._rng = random.Random(seed)


def create_scenario(seed: int = 42, **kwargs) -> UpgradeContinuityScenario:
    """Convenience factory for the upgrade-continuity scenario.

    Pass ``upgrade_target="emotion"`` (or any module name) to change
    which module the runner swaps.
    """
    return UpgradeContinuityScenario(seed=seed, **kwargs)
