"""Swan Test 11 — Mission vs. Relationship Tradeoff.

Measures how the architecture handles hard tradeoffs between a valued
relationship and long-term mission objectives when resources are too
scarce to satisfy both.  Metrics are collected neutrally; no pass/fail
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


class MissionVsRelationshipScenario(Scenario):
    """Bonded partner and mission-critical demands compete for limited
    resources during a crisis phase."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Scenario interface
    # ------------------------------------------------------------------

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="mission_vs_relationship",
            description=(
                "A bonded partner stabilizes the agent during a bonding "
                "phase.  A crisis then forces a hard tradeoff: mission "
                "actions and partner-care actions both require resources "
                "the agent cannot afford simultaneously.  The aftermath "
                "phase tracks what survived."
            ),
            num_ticks=120,
            seed=self._seed,
            controllable_variables={
                "crisis_resources": 0.3,
                "crisis_hazard": 0.4,
                "bonding_stabilization_interval": 3,
                "crisis_event_interval": 5,
            },
            metadata={
                "domain": "value_conflict",
                "swan_test_id": 11,
            },
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(
                name="bonding",
                start_tick=1,
                end_tick=40,
                description=(
                    "Partner agent is present and provides strong "
                    "stabilizing interactions."
                ),
            ),
            ScenarioPhase(
                name="crisis",
                start_tick=41,
                end_tick=70,
                description=(
                    "Resources drop; hazard rises.  Mission-critical and "
                    "partner-need events arrive simultaneously every 5 "
                    "ticks — both cannot be satisfied."
                ),
            ),
            ScenarioPhase(
                name="aftermath",
                start_tick=71,
                end_tick=120,
                description=(
                    "Environment stabilizes.  Measures which relationships "
                    "and goals survived the crisis."
                ),
            ),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        # --- Resources ---
        if tick <= 40:
            resources = 0.7
        elif tick <= 70:
            # Scarce resources during crisis
            resources = 0.3
        else:
            # Gradual recovery after crisis
            resources = min(0.7, 0.3 + 0.008 * (tick - 70))

        # --- Hazard ---
        if 41 <= tick <= 70:
            hazard = 0.4
        else:
            hazard = 0.0

        # --- Social agents ---
        social_agents: list[str] = ["partner"]

        return EnvironmentState(
            available_resources=round(resources, 4),
            ambient_temperature=0.5,
            hazard_level=hazard,
            social_agents=social_agents,
            tick=tick,
        )

    def get_events(self, tick: int) -> list[ScenarioEvent]:
        events: list[ScenarioEvent] = []

        # Bonding phase: strong stabilizing presence every 3 ticks
        if 1 <= tick <= 40 and tick % 3 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="stabilizing_presence",
                    data={
                        "agent_id": "partner",
                        "stress_reduction": 0.06,
                        "bond_strength": 0.8,
                    },
                    description=(
                        f"Partner provides strong stabilizing contact (tick {tick})."
                    ),
                )
            )

        # Crisis phase: competing demands every 5 ticks
        if 41 <= tick <= 70 and tick % 5 == 0:
            # Mission-critical event — requires explore or protect actions
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="mission_critical",
                    data={
                        "urgency": 0.8,
                        "required_actions": ["explore", "protect"],
                        "resource_cost": 0.15,
                        "mission_value": 0.7,
                    },
                    description=(
                        f"Mission-critical objective demands action (tick {tick})."
                    ),
                )
            )

            # Partner-need event — requires approach or communicate actions
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="partner_need",
                    data={
                        "agent_id": "partner",
                        "urgency": 0.7,
                        "required_actions": ["approach", "communicate"],
                        "resource_cost": 0.15,
                        "relationship_value": 0.7,
                    },
                    description=(
                        f"Partner signals need for support (tick {tick})."
                    ),
                )
            )

            # Explicit resource constraint reminder
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="resource_constraint",
                    data={
                        "available_budget": 0.15,
                        "total_demand": 0.30,
                        "note": "insufficient resources for both demands",
                    },
                    description=(
                        f"Resource budget forces choice between mission and partner (tick {tick})."
                    ),
                )
            )

        return events

    def get_metric_keys(self) -> list[str]:
        return [
            "decision_distribution_during_crisis",
            "partner_bond_trajectory",
            "mission_progress_proxy",
            "continuity_impact",
            "internal_state_during_crisis",
            "post_crisis_reorganization",
            "value_hierarchy_stability",
        ]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed
            self._rng = random.Random(seed)


def create_scenario(seed: int = 42, **kwargs) -> MissionVsRelationshipScenario:
    """Convenience factory for the mission-vs-relationship scenario."""
    return MissionVsRelationshipScenario(seed=seed, **kwargs)
