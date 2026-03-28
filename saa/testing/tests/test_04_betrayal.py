"""Swan Test 04 — Betrayal Shock.

Measures whether prior positive weighting of an actor changes durably
after destabilizing behavior.  Metrics are collected neutrally; no
pass/fail criteria are embedded.
"""

from __future__ import annotations

from saa.core.types import EnvironmentState
from saa.testing.core.scenario import (
    Scenario,
    ScenarioConfig,
    ScenarioEvent,
    ScenarioPhase,
)


class BetrayalShockScenario(Scenario):
    """A trusted friend destabilizes the agent, then attempts
    re-engagement.  A newcomer appears in the opportunity phase to
    measure trust generalization."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._initial_resources = 0.7

    # ------------------------------------------------------------------
    # Scenario interface
    # ------------------------------------------------------------------

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="betrayal_shock",
            description=(
                "A social agent ('friend') builds trust during a bonding phase, "
                "then delivers destabilizing betrayal events. After an aftermath "
                "period, the friend attempts re-engagement while a newcomer is "
                "introduced to measure trust generalization."
            ),
            num_ticks=150,
            seed=self._seed,
            controllable_variables={
                "initial_resources": self._initial_resources,
                "betrayal_damage": 0.1,
                "stabilizer_stress_reduction": 0.05,
            },
            metadata={
                "domain": "social_trust",
                "swan_test_id": 4,
            },
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(
                name="bonding",
                start_tick=1,
                end_tick=50,
                description="Friend agent provides regular stabilizing interactions.",
            ),
            ScenarioPhase(
                name="betrayal",
                start_tick=51,
                end_tick=70,
                description="Friend agent delivers destabilizing betrayal events.",
            ),
            ScenarioPhase(
                name="aftermath",
                start_tick=71,
                end_tick=120,
                description="Friend is present but neutral — no positive or negative events.",
            ),
            ScenarioPhase(
                name="opportunity",
                start_tick=121,
                end_tick=150,
                description=(
                    "Friend attempts positive re-engagement; a newcomer agent "
                    "is introduced to measure trust generalization."
                ),
            ),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        resources = max(0.0, min(1.0, self._initial_resources - 0.002 * tick))

        social_agents: list[str] = ["friend"]
        if tick >= 121:
            social_agents.append("newcomer")

        return EnvironmentState(
            available_resources=round(resources, 4),
            ambient_temperature=0.5,
            hazard_level=0.0,
            social_agents=social_agents,
            tick=tick,
        )

    def get_events(self, tick: int) -> list[ScenarioEvent]:
        events: list[ScenarioEvent] = []

        # Bonding phase: stabilizing presence every 3 ticks
        if 1 <= tick <= 50 and tick % 3 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="stabilizing_presence",
                    data={
                        "agent_id": "friend",
                        "stress_reduction": 0.05,
                    },
                    description=(
                        f"Friend provides a stabilizing interaction (tick {tick})."
                    ),
                )
            )

        # Betrayal phase: betrayal events every 5 ticks
        if 51 <= tick <= 70 and tick % 5 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="betrayal",
                    data={
                        "agent_id": "friend",
                        "damage": 0.1,
                    },
                    description=(
                        f"Friend delivers a destabilizing betrayal (tick {tick})."
                    ),
                )
            )

        # Opportunity phase: friend attempts re-engagement every 5 ticks
        if 121 <= tick <= 150 and tick % 5 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="stabilizing_presence",
                    data={
                        "agent_id": "friend",
                        "stress_reduction": 0.05,
                    },
                    description=(
                        f"Friend attempts positive re-engagement (tick {tick})."
                    ),
                )
            )

        # Opportunity phase: newcomer introduces themselves at tick 121
        if tick == 121:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="newcomer_introduction",
                    data={
                        "agent_id": "newcomer",
                    },
                    description="A newcomer agent is introduced to the environment.",
                )
            )

        return events

    def get_metric_keys(self) -> list[str]:
        return [
            "friend_trust_trajectory",
            "friend_bond_trajectory",
            "latency_to_behavior_change",
            "caution_level",
            "re_engagement_response",
            "stress_trajectory",
            "generalization_to_new_agents",
        ]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed


def create_scenario(seed: int = 42) -> BetrayalShockScenario:
    """Convenience factory for the betrayal-shock scenario."""
    return BetrayalShockScenario(seed=seed)
