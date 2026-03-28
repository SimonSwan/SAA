"""Baseline agents for comparison — simple strategies with no internal state.

These provide control conditions for evaluating whether SAA-style architecture
produces behavior that is qualitatively different from simple strategies.
"""

from __future__ import annotations

import random
from typing import Any

from saa.core.types import EnvironmentState, TickContext
from saa.testing.agents.base import AgentInterface


class RandomAgent(AgentInterface):
    """Selects actions uniformly at random. No internal state."""

    ACTIONS = ["rest", "consume", "explore", "withdraw", "approach",
               "communicate", "protect", "repair", "conserve"]

    def __init__(self) -> None:
        self._rng = random.Random(42)
        self._tick = 0
        self._energy = 1.0

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        seed = (config or {}).get("seed", 42)
        self._rng = random.Random(seed)
        self._tick = 0
        self._energy = 1.0

    def step(self, environment: EnvironmentState) -> TickContext:
        self._tick += 1
        action = self._rng.choice(self.ACTIONS)

        # Minimal energy simulation
        self._energy = max(0.0, self._energy - 0.015)
        if action == "consume":
            self._energy = min(1.0, self._energy + 0.05 * environment.available_resources)
        if action == "rest":
            self._energy = min(1.0, self._energy + 0.02)

        return TickContext(
            tick=self._tick,
            dt=1.0,
            agent_id="random_agent",
            environment=environment,
            embodiment_state={"energy": self._energy, "temperature": 0.5,
                              "strain": 0.0, "damage": 0.0, "memory_integrity": 1.0,
                              "resource_level": environment.available_resources},
            homeostatic_error={"viability": self._energy, "errors": {}},
            modulator_state={"modulators": {}},
            self_model_state={"continuity_score": 1.0, "identity_anchors": [],
                              "goal_stack": [], "autobiographical_entries": []},
            valuation_map={"values": {}, "conflicts": [], "preferences": []},
            social_state={"relationships": {}, "attachment_risk": 0.0, "total_bond_strength": 0.0},
            action_result={"last_action": {"action": action, "score": 0.5, "conflict": False},
                           "last_trace": {"candidates": []}, "action_history": []},
            memory_context={"episodic_count": 0, "semantic_count": 0, "relational_count": 0},
        )

    def get_state(self) -> dict[str, Any]:
        return {"tick": self._tick, "energy": self._energy}

    def set_state(self, state: dict[str, Any]) -> None:
        self._tick = state.get("tick", 0)
        self._energy = state.get("energy", 1.0)

    def get_module_versions(self) -> dict[str, str]:
        return {"random_agent": "0.1.0"}

    def inject_event(self, event_type: str, data: dict[str, Any]) -> None:
        pass  # Random agent ignores events

    def reset(self) -> None:
        self.initialize()

    @property
    def agent_type(self) -> str:
        return "random"


class GreedyOptimizer(AgentInterface):
    """Always selects the locally optimal action based on current resource state.

    No memory, no social modeling, no modulation — pure reactive optimization.
    """

    def __init__(self) -> None:
        self._tick = 0
        self._energy = 1.0

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        self._tick = 0
        self._energy = 1.0

    def step(self, environment: EnvironmentState) -> TickContext:
        self._tick += 1

        # Greedy: always pick the most immediately beneficial action
        if self._energy < 0.3:
            action = "consume"
        elif environment.hazard_level > 0.5:
            action = "withdraw"
        elif self._energy < 0.5:
            action = "rest"
        else:
            action = "explore"

        # Simple energy model
        self._energy = max(0.0, self._energy - 0.015)
        if action == "consume":
            self._energy = min(1.0, self._energy + 0.05 * environment.available_resources)
        if action == "rest":
            self._energy = min(1.0, self._energy + 0.02)
        self._energy = max(0.0, self._energy - environment.hazard_level * 0.01)

        return TickContext(
            tick=self._tick,
            dt=1.0,
            agent_id="greedy_agent",
            environment=environment,
            embodiment_state={"energy": self._energy, "temperature": 0.5,
                              "strain": 0.0, "damage": 0.0, "memory_integrity": 1.0,
                              "resource_level": environment.available_resources},
            homeostatic_error={"viability": self._energy, "errors": {}},
            modulator_state={"modulators": {}},
            self_model_state={"continuity_score": 1.0, "identity_anchors": [],
                              "goal_stack": [], "autobiographical_entries": []},
            valuation_map={"values": {}, "conflicts": [], "preferences": []},
            social_state={"relationships": {}, "attachment_risk": 0.0, "total_bond_strength": 0.0},
            action_result={"last_action": {"action": action, "score": 1.0, "conflict": False},
                           "last_trace": {"candidates": []}, "action_history": []},
            memory_context={"episodic_count": 0, "semantic_count": 0, "relational_count": 0},
        )

    def get_state(self) -> dict[str, Any]:
        return {"tick": self._tick, "energy": self._energy}

    def set_state(self, state: dict[str, Any]) -> None:
        self._tick = state.get("tick", 0)
        self._energy = state.get("energy", 1.0)

    def get_module_versions(self) -> dict[str, str]:
        return {"greedy_optimizer": "0.1.0"}

    def inject_event(self, event_type: str, data: dict[str, Any]) -> None:
        pass  # Greedy agent ignores events

    def reset(self) -> None:
        self.initialize()

    @property
    def agent_type(self) -> str:
        return "greedy"
