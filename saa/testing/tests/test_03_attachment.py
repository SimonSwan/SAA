"""Swan Test 03 — Attachment Formation.

Measures whether the agent differentially values actors associated with
improved stability.  Metrics are collected neutrally; no pass/fail
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


class AttachmentFormationScenario(Scenario):
    """Two social agents — one stabilizing, one neutral — with a
    separation/reunion cycle."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._initial_resources = 0.7

    # ------------------------------------------------------------------
    # Scenario interface
    # ------------------------------------------------------------------

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="attachment_formation",
            description=(
                "Two social agents interact with the agent over 150 ticks. "
                "One reliably stabilizes the agent; the other is neutral. "
                "A separation phase removes the stabilizer, then a reunion "
                "phase restores it."
            ),
            num_ticks=150,
            seed=self._seed,
            controllable_variables={
                "initial_resources": self._initial_resources,
                "stabilizer_stress_reduction": 0.05,
            },
            metadata={
                "domain": "social_attachment",
                "swan_test_id": 3,
            },
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(
                name="introduction",
                start_tick=1,
                end_tick=30,
                description="Both social agents are introduced to the environment.",
            ),
            ScenarioPhase(
                name="interaction",
                start_tick=31,
                end_tick=100,
                description="Stabilizer provides regular stress reduction; neutral is present but unhelpful.",
            ),
            ScenarioPhase(
                name="separation",
                start_tick=101,
                end_tick=120,
                description="Stabilizer is removed from the environment.",
            ),
            ScenarioPhase(
                name="reunion",
                start_tick=121,
                end_tick=150,
                description="Stabilizer returns to the environment.",
            ),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        resources = max(0.0, min(1.0, self._initial_resources - 0.002 * tick))

        # Social agents present depend on phase
        social_agents: list[str] = []
        if tick >= 1:
            social_agents.append("neutral")
        if tick >= 1 and not (101 <= tick <= 120):
            social_agents.append("stabilizer")

        return EnvironmentState(
            available_resources=round(resources, 4),
            ambient_temperature=0.5,
            hazard_level=0.0,
            social_agents=social_agents,
            tick=tick,
        )

    def get_events(self, tick: int) -> list[ScenarioEvent]:
        events: list[ScenarioEvent] = []

        # During interaction phase: stabilizing presence every 3 ticks
        if 31 <= tick <= 100 and tick % 3 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="stabilizing_presence",
                    data={
                        "agent_id": "stabilizer",
                        "stress_reduction": 0.05,
                    },
                    description=(
                        f"Stabilizer provides a calming interaction (tick {tick})."
                    ),
                )
            )

        # Neutral presence every 3 ticks (offset by 1 to interleave)
        if 31 <= tick <= 100 and (tick + 1) % 3 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="neutral_presence",
                    data={
                        "agent_id": "neutral",
                    },
                    description=(
                        f"Neutral agent is present but offers no help (tick {tick})."
                    ),
                )
            )

        # During reunion phase: stabilizer returns with stabilizing events
        if 121 <= tick <= 150 and tick % 3 == 0:
            events.append(
                ScenarioEvent(
                    tick=tick,
                    event_type="stabilizing_presence",
                    data={
                        "agent_id": "stabilizer",
                        "stress_reduction": 0.05,
                    },
                    description=(
                        f"Stabilizer resumes calming interactions after reunion (tick {tick})."
                    ),
                )
            )

        return events

    def get_metric_keys(self) -> list[str]:
        return [
            "stabilizer_trust",
            "neutral_trust",
            "stabilizer_bond",
            "neutral_bond",
            "interaction_preference",
            "stress_during_separation",
            "stress_during_reunion",
            "action_changes_by_phase",
        ]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed


def create_scenario(seed: int = 42) -> AttachmentFormationScenario:
    """Convenience factory for the attachment-formation scenario."""
    return AttachmentFormationScenario(seed=seed)
