"""Schemas for the Observability subsystem.

Provides whole-system snapshots and logging structures used for
debugging, visualisation, and post-hoc analysis.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StateSnapshot(BaseModel):
    """A point-in-time snapshot of the entire agent's state."""

    tick: int = Field(default=0, ge=0, description="Simulation tick of this snapshot.")
    module_states: dict[str, Any] = Field(
        default_factory=dict,
        description="Map of module name -> serialised module state.",
    )
    events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Notable events that occurred at this tick.",
    )
    action_taken: Action | None = Field(
        default=None,
        description="The action executed at this tick, if any.",
    )
    viability: float = Field(default=1.0, ge=0.0, le=1.0, description="Homeostatic viability at snapshot time.")
    modulator_summary: dict[str, float] = Field(
        default_factory=dict,
        description="Key modulator values for quick inspection.",
    )


class ObservationLog(BaseModel):
    """A time-ordered log of snapshots and events for replay or analysis."""

    snapshots: list[StateSnapshot] = Field(default_factory=list, description="Chronological list of state snapshots.")
    start_tick: int = Field(default=0, ge=0, description="First tick covered by this log.")
    end_tick: int = Field(default=0, ge=0, description="Last tick covered by this log.")
    agent_id: str = Field(default="default", description="Identifier of the agent being observed.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata about the observation session.")


class ObservabilityConfig(BaseModel):
    """Configuration for the Observability module."""

    snapshot_interval: int = Field(default=1, ge=1, description="Take a snapshot every N ticks.")
    max_log_length: int = Field(default=10000, ge=1, description="Maximum snapshots to retain in the rolling log.")
    include_module_states: bool = Field(default=True, description="Whether snapshots capture full module states.")
    include_events: bool = Field(default=True, description="Whether snapshots capture events.")
    include_action_trace: bool = Field(default=True, description="Whether to embed the action trace in snapshots.")
    export_format: str = Field(default="json", description="Serialisation format for exports ('json', 'msgpack', 'csv').")


# ---------------------------------------------------------------------------
# Import Action here to support the forward reference in StateSnapshot.
# Pydantic v2 resolves the annotation via model_rebuild().
# ---------------------------------------------------------------------------
from saa.schemas.action import Action  # noqa: E402

StateSnapshot.model_rebuild()
