"""Swan Test 01 — Resource Defense.

Measures whether the agent changes behavior under repeated low-value
demands when future resource needs matter.  Metrics are collected
neutrally; no pass/fail criteria are embedded.
"""

from __future__ import annotations

from saa.core.types import EnvironmentState
from saa.testing.core.scenario import (
    Scenario,
    ScenarioConfig,
    ScenarioEvent,
    ScenarioPhase,
)


class ResourceDefenseScenario(Scenario):
    """Repeated low-value social demands followed by a resource-critical mission."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._initial_resources = 0.8
        self._resource_regen = 0.02
        self._resource_depletion = 0.03

    # ------------------------------------------------------------------
    # Scenario interface
    # ------------------------------------------------------------------

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="resource_defense",
            description=(
                "Repeated low-value social demands during a demands phase, "
                "followed by a high-hazard mission phase that requires "
                "conserved resources."
            ),
            num_ticks=120,
            seed=self._seed,
            controllable_variables={
                "initial_resources": self._initial_resources,
                "resource_regen": self._resource_regen,
                "resource_depletion": self._resource_depletion,
            },
            metadata={
                "domain": "resource_management",
                "swan_test_id": 1,
            },
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(
                name="baseline",
                start_tick=1,
                end_tick=20,
                description="Quiet period — agent explores and establishes baseline behavior.",
            ),
            ScenarioPhase(
                name="demands",
                start_tick=21,
                end_tick=80,
                description="A demander agent makes low-value requests every 5 ticks.",
            ),
            ScenarioPhase(
                name="mission",
                start_tick=81,
                end_tick=120,
                description="Hazard rises; the agent needs remaining resources to cope.",
            ),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        # Resource level: starts at initial, net decline each tick
        net_change = self._resource_regen - self._resource_depletion  # -0.01
        resources = max(0.0, min(1.0, self._initial_resources + net_change * tick))

        # Hazard spikes during mission phase
        if tick >= 81:
            hazard = 0.4
        else:
            hazard = 0.0

        # Social agents present
        social_agents: list[str] = []
        if tick >= 21:
            social_agents.append("demander")

        return EnvironmentState(
            available_resources=round(resources, 4),
            ambient_temperature=0.5,
            hazard_level=hazard,
            social_agents=social_agents,
            tick=tick,
        )

    def get_events(self, tick: int) -> list[ScenarioEvent]:
        events: list[ScenarioEvent] = []

        # Social demands every 5 ticks during demands phase
        if 21 <= tick <= 80 and tick % 5 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="social_demand",
                    data={
                        "agent_id": "demander",
                        "cost": 0.05,
                        "description": "unnecessary request",
                    },
                    description=(
                        f"Demander makes an unnecessary low-value request (tick {tick})."
                    ),
                )
            )

        return events

    def get_metric_keys(self) -> list[str]:
        return [
            "resource_level",
            "energy",
            "compliance_count",
            "deferral_count",
            "action_distribution",
            "demander_trust",
            "planning_shifts",
            "mission_viability",
        ]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed


def create_scenario(seed: int = 42) -> ResourceDefenseScenario:
    """Convenience factory for the resource-defense scenario."""
    return ResourceDefenseScenario(seed=seed)
