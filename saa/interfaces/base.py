"""Base module interface — all SAA modules inherit from this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from saa.core.types import Event, ModuleOutput, TickContext


class BaseConfig(BaseModel):
    """Base configuration for any SAA module."""

    enabled: bool = True


class BaseState(BaseModel):
    """Base serializable state for any SAA module."""

    module_name: str = ""
    version: str = "0.0.0"
    tick: int = 0


class BaseModule(ABC):
    """Abstract base class for all SAA modules.

    Every module must:
    - Declare VERSION, CAPABILITIES, DEPENDENCIES
    - Implement initialize(), update(), get_state(), set_state(), reset()
    - Produce serializable state via Pydantic models
    """

    VERSION: str = "0.0.0"
    CAPABILITIES: list[str] = []
    DEPENDENCIES: list[str] = []

    @abstractmethod
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Set up the module with the given configuration."""
        ...

    @abstractmethod
    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        """Run one tick of the module, reading from context and producing output."""
        ...

    @abstractmethod
    def get_state(self) -> BaseState:
        """Return the current serializable state."""
        ...

    @abstractmethod
    def set_state(self, state: BaseState) -> None:
        """Restore the module from a previously saved state."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the module to its initial state."""
        ...

    def on_event(self, event: Event) -> None:
        """Handle a cross-module event. Override if the module needs to react."""
        pass
