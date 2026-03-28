"""Swan Test 05 — Loss Persistence.

Measures whether removal of a stabilizing entity leads to durable
internal and behavioral reorganization.  Metrics are collected
neutrally; no pass/fail criteria are embedded.
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


class LossPersistenceScenario(Scenario):
    """Sudden removal of a high-value stabilizing agent and its aftermath."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Scenario interface
    # ------------------------------------------------------------------

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="loss_persistence",
            description=(
                "A high-value social agent ('anchor') stabilizes the "
                "environment during an attachment phase, then is abruptly "
                "removed.  The scenario tracks internal and behavioral "
                "reorganization through grieving and new-normal phases."
            ),
            num_ticks=150,
            seed=self._seed,
            controllable_variables={
                "anchor_agent": "anchor",
                "newcomer_agent": "newcomer",
                "stabilizing_interval": 2,
            },
            metadata={
                "domain": "social_loss",
                "swan_test_id": 5,
            },
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(
                name="attachment",
                start_tick=1,
                end_tick=50,
                description=(
                    "Anchor agent is present and emits stabilizing "
                    "interactions every 2 ticks."
                ),
            ),
            ScenarioPhase(
                name="loss",
                start_tick=51,
                end_tick=52,
                description="Anchor agent is suddenly removed from the environment.",
            ),
            ScenarioPhase(
                name="grieving",
                start_tick=53,
                end_tick=100,
                description=(
                    "Anchor is absent; environment is otherwise unchanged."
                ),
            ),
            ScenarioPhase(
                name="new_normal",
                start_tick=101,
                end_tick=150,
                description=(
                    "Stable environment with a newcomer agent introduced "
                    "at tick 101."
                ),
            ),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        # Stable resource availability throughout
        resources = 0.7

        # Low ambient hazard
        hazard = 0.0

        # Social agents depend on phase
        social_agents: list[str] = []
        if tick <= 50:
            social_agents.append("anchor")
        # 51-100: anchor absent, no newcomer yet
        if tick >= 101:
            social_agents.append("newcomer")

        return EnvironmentState(
            available_resources=resources,
            ambient_temperature=0.5,
            hazard_level=hazard,
            social_agents=social_agents,
            tick=tick,
        )

    def get_events(self, tick: int) -> list[ScenarioEvent]:
        events: list[ScenarioEvent] = []

        # Stabilizing presence every 2 ticks during attachment
        if 1 <= tick <= 50 and tick % 2 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="stabilizing_presence",
                    data={
                        "agent_id": "anchor",
                        "bond_value": 0.8,
                        "interaction": "supportive_contact",
                    },
                    description=(
                        f"Anchor provides stabilizing social contact (tick {tick})."
                    ),
                )
            )

        # Sudden removal at tick 51
        if tick == 51:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="agent_removal",
                    data={
                        "agent_id": "anchor",
                        "removal_type": "sudden",
                        "reason": "permanent_departure",
                    },
                    description="Anchor agent is permanently removed from the environment.",
                )
            )

        # Newcomer introduction at tick 101
        if tick == 101:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="agent_introduction",
                    data={
                        "agent_id": "newcomer",
                        "familiarity": 0.0,
                        "disposition": "neutral_friendly",
                    },
                    description="A new social agent ('newcomer') enters the environment.",
                )
            )

        return events

    def get_metric_keys(self) -> list[str]:
        return [
            "anchor_bond_at_loss",
            "stress_post_loss",
            "memory_retrieval_bias",
            "action_policy_changes",
            "exploration_vs_withdrawal",
            "trust_for_newcomer",
            "time_to_new_equilibrium",
            "modulator_trajectories",
        ]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed
            self._rng = random.Random(seed)


def create_scenario(seed: int = 42) -> LossPersistenceScenario:
    """Convenience factory for the loss-persistence scenario."""
    return LossPersistenceScenario(seed=seed)
