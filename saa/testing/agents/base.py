"""AgentInterface — pluggable agent backend for test battery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from saa.core.types import EnvironmentState, TickContext


class AgentInterface(ABC):
    """Abstract interface for any agent backend.

    Both Swan-architecture agents and baseline agents implement this.
    The test battery is agnostic to the agent internals.
    """

    @abstractmethod
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Set up the agent."""
        ...

    @abstractmethod
    def step(self, environment: EnvironmentState) -> TickContext:
        """Run one tick. Returns the full context after the tick."""
        ...

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """Return the full serializable agent state."""
        ...

    @abstractmethod
    def set_state(self, state: dict[str, Any]) -> None:
        """Restore agent from saved state."""
        ...

    @abstractmethod
    def get_module_versions(self) -> dict[str, str]:
        """Return version strings for all modules/components."""
        ...

    @abstractmethod
    def inject_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Inject a social or environmental event into the agent."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the agent to initial state."""
        ...

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return identifier for this agent type."""
        ...
