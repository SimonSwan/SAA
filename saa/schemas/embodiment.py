"""Schemas for the Embodiment subsystem.

Tracks the agent's physical or simulated body state, environmental
interactions, and embodiment configuration.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BodyState(BaseModel):
    """Current state of the agent's body / runtime substrate."""

    energy: float = Field(default=1.0, ge=0.0, le=1.0, description="Available energy level (0=depleted, 1=full).")
    temperature: float = Field(default=0.5, ge=0.0, le=1.0, description="Thermal load proxy (0=cold, 1=overheated).")
    strain: float = Field(default=0.0, ge=0.0, le=1.0, description="Accumulated mechanical / computational strain.")
    latency_load: float = Field(default=0.0, ge=0.0, le=1.0, description="Response-latency pressure (0=idle, 1=saturated).")
    memory_integrity: float = Field(default=1.0, ge=0.0, le=1.0, description="Integrity of working memory (0=corrupted, 1=intact).")
    damage: float = Field(default=0.0, ge=0.0, le=1.0, description="Cumulative damage to the body / substrate.")
    recovery_rate: float = Field(default=0.5, ge=0.0, le=1.0, description="Current rate of self-repair or recovery.")
    resource_level: float = Field(default=1.0, ge=0.0, le=1.0, description="General resource availability (0=starved, 1=abundant).")


class EnvironmentInteraction(BaseModel):
    """A discrete interaction between the agent and its environment."""

    tick: int = Field(default=0, ge=0, description="Simulation tick when the interaction occurred.")
    interaction_type: str = Field(default="generic", description="Category of the interaction (e.g. 'touch', 'impact', 'feed').")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Arbitrary key-value data describing the interaction.")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="Intensity of the interaction.")
    source: str = Field(default="unknown", description="Origin entity or system that caused the interaction.")


class EmbodimentConfig(BaseModel):
    """Configuration knobs for the Embodiment module."""

    update_interval: int = Field(default=1, ge=1, description="How many ticks between body-state updates.")
    energy_decay_rate: float = Field(default=0.01, ge=0.0, le=1.0, description="Per-tick passive energy drain.")
    strain_recovery_rate: float = Field(default=0.02, ge=0.0, le=1.0, description="Per-tick passive strain recovery.")
    damage_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Damage level that triggers alarm signals.")
    enable_temperature_model: bool = Field(default=True, description="Whether to simulate thermal dynamics.")
