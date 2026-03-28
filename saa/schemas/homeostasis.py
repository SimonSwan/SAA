"""Schemas for the Homeostasis subsystem.

Homeostasis maintains vital variables within viable ranges by computing
errors against setpoints and prioritising regulation actions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SetpointRange(BaseModel):
    """Defines the ideal range for a single homeostatic variable."""

    variable: str = Field(description="Name of the variable being regulated.")
    low: float = Field(default=0.3, ge=0.0, le=1.0, description="Lower bound of the comfortable range.")
    target: float = Field(default=0.5, ge=0.0, le=1.0, description="Ideal target value.")
    high: float = Field(default=0.7, ge=0.0, le=1.0, description="Upper bound of the comfortable range.")
    critical_low: float = Field(default=0.1, ge=0.0, le=1.0, description="Value below which the variable becomes life-threatening.")
    critical_high: float = Field(default=0.9, ge=0.0, le=1.0, description="Value above which the variable becomes life-threatening.")
    weight: float = Field(default=1.0, ge=0.0, description="Relative importance of this variable in the overall viability score.")


class HomeostaticError(BaseModel):
    """Current deviation of each regulated variable from its setpoint."""

    errors: dict[str, float] = Field(
        default_factory=dict,
        description="Map of variable name -> signed error (positive = above target, negative = below).",
    )
    viability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Aggregate viability score (0=critical, 1=perfect homeostasis).",
    )
    tick: int = Field(default=0, ge=0, description="Simulation tick of this measurement.")


class RegulationPriority(BaseModel):
    """Priority-ordered regulation need for a single variable."""

    variable: str = Field(description="Name of the variable requiring regulation.")
    urgency: float = Field(default=0.0, ge=0.0, le=1.0, description="How urgently this variable needs correction.")
    direction: str = Field(default="increase", description="'increase' or 'decrease' to move toward setpoint.")
    current_value: float = Field(default=0.5, ge=0.0, le=1.0, description="Current value of the variable.")
    target_value: float = Field(default=0.5, ge=0.0, le=1.0, description="Target setpoint value.")
    error_magnitude: float = Field(default=0.0, ge=0.0, description="Absolute magnitude of the error.")


class HomeostasisConfig(BaseModel):
    """Configuration for the Homeostasis module."""

    setpoints: list[SetpointRange] = Field(
        default_factory=list,
        description="Setpoint definitions for each regulated variable.",
    )
    viability_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Viability score below which emergency regulation is triggered.",
    )
    regulation_gain: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Proportional gain for homeostatic corrections.",
    )
    update_interval: int = Field(default=1, ge=1, description="Ticks between homeostatic assessments.")
    max_simultaneous_corrections: int = Field(
        default=3,
        ge=1,
        description="Maximum number of variables corrected in a single tick.",
    )
