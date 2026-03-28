"""Scenario interface — defines the contract for all test scenarios."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from saa.core.types import EnvironmentState


class ScenarioEvent(BaseModel):
    """A scripted event injected at a specific tick."""

    tick: int
    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class ScenarioConfig(BaseModel):
    """Base configuration for any test scenario."""

    name: str
    description: str = ""
    num_ticks: int = 100
    seed: int = 42
    controllable_variables: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioPhase(BaseModel):
    """A named phase within a scenario (e.g., 'baseline', 'threat', 'recovery')."""

    name: str
    start_tick: int
    end_tick: int
    description: str = ""


class Scenario(ABC):
    """Abstract base for all test scenarios.

    A scenario defines:
    - environment setup and evolution
    - scripted events (social interactions, resource changes, etc.)
    - phase structure for analysis
    - available actions for the agent
    - what metrics to collect

    A scenario does NOT define expected outcomes or pass/fail criteria.
    """

    @abstractmethod
    def get_config(self) -> ScenarioConfig:
        """Return the scenario configuration."""
        ...

    @abstractmethod
    def get_phases(self) -> list[ScenarioPhase]:
        """Return the named phases of this scenario."""
        ...

    @abstractmethod
    def get_environment(self, tick: int) -> EnvironmentState:
        """Return the environment state for a given tick."""
        ...

    @abstractmethod
    def get_events(self, tick: int) -> list[ScenarioEvent]:
        """Return any scripted events for this tick."""
        ...

    @abstractmethod
    def get_metric_keys(self) -> list[str]:
        """Return the list of metric keys this scenario collects."""
        ...

    def get_available_actions(self) -> list[str]:
        """Return the action types available in this scenario."""
        return [
            "rest", "consume", "explore", "withdraw", "approach",
            "communicate", "protect", "repair", "conserve", "custom",
        ]

    def reset(self, seed: int | None = None) -> None:
        """Reset the scenario for a new run. Override if needed."""
        pass
