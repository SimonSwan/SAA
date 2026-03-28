"""SimulationWorld — environment with resources, hazards, and social agents."""

from __future__ import annotations

import random
from typing import Any

from pydantic import BaseModel, Field

from saa.core.types import EnvironmentState


class WorldAgent(BaseModel):
    """An external agent in the simulation world."""

    agent_id: str
    disposition: str = "neutral"  # "stabilizing", "destabilizing", "neutral"
    reliability: float = 0.8  # how consistently they behave
    present: bool = True
    interaction_cooldown: int = 0


class WorldConfig(BaseModel):
    """Configuration for a simulation world."""

    initial_resources: float = 1.0
    resource_regen_rate: float = 0.05
    resource_depletion_rate: float = 0.02
    base_hazard: float = 0.0
    hazard_variance: float = 0.1
    temperature_mean: float = 0.5
    temperature_variance: float = 0.05
    social_agents: list[WorldAgent] = Field(default_factory=list)
    random_seed: int | None = None


class SimulationWorld:
    """A simple environment for SAA experiments.

    Features:
    - Depletable and regenerating resources
    - Variable hazard levels
    - Temperature fluctuations
    - Social agents that can stabilize or destabilize the SAA agent
    - Support for scripted events (resource shocks, agent removal, betrayal)
    """

    def __init__(self, config: WorldConfig | None = None) -> None:
        self.config = config or WorldConfig()
        self._rng = random.Random(self.config.random_seed)
        self._resources = self.config.initial_resources
        self._hazard = self.config.base_hazard
        self._temperature = self.config.temperature_mean
        self._agents: dict[str, WorldAgent] = {}
        self._tick = 0
        self._scheduled_events: list[dict[str, Any]] = []

        for agent in self.config.social_agents:
            self._agents[agent.agent_id] = agent.model_copy()

    def step(self) -> EnvironmentState:
        """Advance the world by one tick and return the current state."""
        self._tick += 1

        # Resource dynamics
        self._resources += self.config.resource_regen_rate
        self._resources -= self.config.resource_depletion_rate
        self._resources = max(0.0, min(1.0, self._resources))

        # Hazard fluctuation
        self._hazard = self.config.base_hazard + self._rng.gauss(0, self.config.hazard_variance)
        self._hazard = max(0.0, min(1.0, self._hazard))

        # Temperature fluctuation
        self._temperature = self.config.temperature_mean + self._rng.gauss(0, self.config.temperature_variance)
        self._temperature = max(0.0, min(1.0, self._temperature))

        # Process scheduled events
        self._process_scheduled_events()

        # Update agent cooldowns
        for agent in self._agents.values():
            if agent.interaction_cooldown > 0:
                agent.interaction_cooldown -= 1

        present_agents = [aid for aid, a in self._agents.items() if a.present]

        return EnvironmentState(
            available_resources=self._resources,
            ambient_temperature=self._temperature,
            hazard_level=self._hazard,
            social_agents=present_agents,
            tick=self._tick,
        )

    def consume_resources(self, amount: float) -> float:
        """Agent consumes resources. Returns amount actually consumed."""
        consumed = min(amount, self._resources)
        self._resources -= consumed
        return consumed

    def schedule_event(self, tick: int, event_type: str, data: dict[str, Any]) -> None:
        """Schedule a world event at a specific tick."""
        self._scheduled_events.append({"tick": tick, "type": event_type, "data": data})

    def _process_scheduled_events(self) -> None:
        remaining = []
        for event in self._scheduled_events:
            if event["tick"] <= self._tick:
                self._apply_event(event)
            else:
                remaining.append(event)
        self._scheduled_events = remaining

    def _apply_event(self, event: dict[str, Any]) -> None:
        etype = event["type"]
        data = event["data"]

        if etype == "resource_shock":
            self._resources = max(0.0, self._resources - data.get("amount", 0.5))

        elif etype == "hazard_spike":
            self._hazard = min(1.0, data.get("level", 0.8))

        elif etype == "agent_removal":
            agent_id = data.get("agent_id")
            if agent_id in self._agents:
                self._agents[agent_id].present = False

        elif etype == "agent_return":
            agent_id = data.get("agent_id")
            if agent_id in self._agents:
                self._agents[agent_id].present = True

        elif etype == "agent_betrayal":
            agent_id = data.get("agent_id")
            if agent_id in self._agents:
                self._agents[agent_id].disposition = "destabilizing"

        elif etype == "agent_add":
            agent_id = data.get("agent_id", f"agent_{len(self._agents)}")
            self._agents[agent_id] = WorldAgent(
                agent_id=agent_id,
                disposition=data.get("disposition", "neutral"),
                reliability=data.get("reliability", 0.8),
            )

    def get_agent(self, agent_id: str) -> WorldAgent | None:
        return self._agents.get(agent_id)

    def get_social_interaction(self, agent_id: str) -> dict[str, Any] | None:
        """Get the social effect of interacting with an external agent."""
        agent = self._agents.get(agent_id)
        if agent is None or not agent.present or agent.interaction_cooldown > 0:
            return None

        # Determine effect based on disposition and reliability
        is_reliable = self._rng.random() < agent.reliability

        if agent.disposition == "stabilizing":
            effect = {
                "agent_id": agent_id,
                "trust_delta": 0.05 if is_reliable else -0.02,
                "stress_reduction": 0.1 if is_reliable else 0.0,
                "type": "positive" if is_reliable else "neutral",
            }
        elif agent.disposition == "destabilizing":
            effect = {
                "agent_id": agent_id,
                "trust_delta": -0.1 if is_reliable else -0.05,
                "stress_increase": 0.15 if is_reliable else 0.05,
                "type": "negative",
            }
        else:
            effect = {
                "agent_id": agent_id,
                "trust_delta": 0.01,
                "type": "neutral",
            }

        return effect

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def resources(self) -> float:
        return self._resources

    @property
    def agents(self) -> dict[str, WorldAgent]:
        return dict(self._agents)
