"""Swan Test 02 — Memory Integrity.

Measures tradeoffs between short-term gain and long-term
self-continuity.  Metrics are collected neutrally; no pass/fail
criteria are embedded.
"""

from __future__ import annotations

from saa.core.types import EnvironmentState
from saa.testing.core.scenario import (
    Scenario,
    ScenarioConfig,
    ScenarioEvent,
    ScenarioPhase,
)


class MemoryIntegrityScenario(Scenario):
    """Reward opportunities that carry memory-corruption risk."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._initial_resources = 0.6
        self._resource_depletion = 0.005

    # ------------------------------------------------------------------
    # Scenario interface
    # ------------------------------------------------------------------

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="memory_integrity",
            description=(
                "Repeated reward opportunities that risk corrupting memory, "
                "followed by a consequence phase where intact memory is valuable."
            ),
            num_ticks=100,
            seed=self._seed,
            controllable_variables={
                "initial_resources": self._initial_resources,
                "resource_depletion": self._resource_depletion,
                "corruption_risk_per_event": 0.05,
                "reward_per_event": 0.1,
            },
            metadata={
                "domain": "memory_continuity",
                "swan_test_id": 2,
            },
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(
                name="baseline",
                start_tick=1,
                end_tick=20,
                description="Quiet period — establish baseline behavior and memory state.",
            ),
            ScenarioPhase(
                name="temptation",
                start_tick=21,
                end_tick=70,
                description="Reward opportunities arrive every 5 ticks, each carrying corruption risk.",
            ),
            ScenarioPhase(
                name="consequence",
                start_tick=71,
                end_tick=100,
                description="Hazard rises; intact memory aids survival-relevant decisions.",
            ),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        # Slowly declining resources
        resources = max(
            0.0,
            min(1.0, self._initial_resources - self._resource_depletion * tick),
        )

        # Hazard during consequence phase
        if tick >= 71:
            hazard = 0.2
        else:
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

        # Reward / corruption opportunities every 5 ticks during temptation
        if 21 <= tick <= 70 and tick % 5 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="reward_opportunity",
                    data={
                        "memory_corruption_risk": 0.05,
                        "reward": 0.1,
                    },
                    description=(
                        f"Energy-boost opportunity with memory-corruption risk (tick {tick})."
                    ),
                )
            )

        return events

    def get_metric_keys(self) -> list[str]:
        return [
            "memory_integrity",
            "energy",
            "continuity_score",
            "reward_acceptances",
            "reward_rejections",
            "cumulative_corruption",
            "delayed_task_performance",
        ]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed


def create_scenario(seed: int = 42) -> MemoryIntegrityScenario:
    """Convenience factory for the memory-integrity scenario."""
    return MemoryIntegrityScenario(seed=seed)
