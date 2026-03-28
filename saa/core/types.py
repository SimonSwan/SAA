"""Shared base types used across the SAA system."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Event(BaseModel):
    """A cross-module event published on the EventBus."""

    tick: int
    source_module: str
    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    severity: float = 0.5  # 0.0 = informational, 1.0 = critical


class ModuleOutput(BaseModel):
    """Standard wrapper for the output of a module's update() call."""

    module_name: str
    tick: int
    state: dict[str, Any] = Field(default_factory=dict)
    events: list[Event] = Field(default_factory=list)


class ActionType(str, Enum):
    """Built-in action types for the agent."""

    REST = "rest"
    CONSUME = "consume"
    EXPLORE = "explore"
    WITHDRAW = "withdraw"
    APPROACH = "approach"
    COMMUNICATE = "communicate"
    PROTECT = "protect"
    REPAIR = "repair"
    CONSERVE = "conserve"
    CUSTOM = "custom"


class EnvironmentState(BaseModel):
    """External environment conditions."""

    available_resources: float = 1.0
    ambient_temperature: float = 0.5
    hazard_level: float = 0.0
    social_agents: list[str] = Field(default_factory=list)
    tick: int = 0


class TickContext(BaseModel):
    """Accumulated context passed to each module during a tick.

    Built incrementally as each module runs within a single tick.
    Earlier modules populate fields that later modules can read.
    """

    tick: int = 0
    dt: float = 1.0
    agent_id: str = "agent_0"
    environment: EnvironmentState = Field(default_factory=EnvironmentState)
    events: list[Event] = Field(default_factory=list)

    # Populated by modules in execution order — Optional until the
    # responsible module has run for this tick.
    embodiment_state: Optional[dict[str, Any]] = None
    interoceptive_vector: Optional[dict[str, Any]] = None
    homeostatic_error: Optional[dict[str, Any]] = None
    allostatic_forecast: Optional[dict[str, Any]] = None
    modulator_state: Optional[dict[str, Any]] = None
    self_model_state: Optional[dict[str, Any]] = None
    memory_context: Optional[dict[str, Any]] = None
    valuation_map: Optional[dict[str, Any]] = None
    social_state: Optional[dict[str, Any]] = None
    action_result: Optional[dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
