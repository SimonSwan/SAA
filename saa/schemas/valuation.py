"""Schemas for the Valuation subsystem.

Valuation assigns subjective worth to states, actions, and outcomes,
and detects conflicts between competing values.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ValuationMap(BaseModel):
    """Maps value dimensions to their current weight / importance."""

    values: dict[str, float] = Field(
        default_factory=dict,
        description="Map of value name -> current weight (unbounded, but typically 0-1).",
    )
    tick: int = Field(default=0, ge=0, description="Tick of this valuation snapshot.")
    context: str = Field(default="", description="Situational context that shaped these weights.")


class PreferenceSet(BaseModel):
    """An ordered set of preferences derived from the valuation map."""

    preferences: list[str] = Field(
        default_factory=list,
        description="Value names in descending order of preference.",
    )
    source_tick: int = Field(default=0, ge=0, description="Tick when these preferences were computed.")
    stability: float = Field(default=1.0, ge=0.0, le=1.0, description="How stable/consistent these preferences have been recently.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context about preference derivation.")


class ValueConflict(BaseModel):
    """A detected conflict between two or more competing values."""

    competing_values: list[str] = Field(
        default_factory=list,
        description="Names of the values in conflict.",
    )
    resolution_difficulty: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How hard the conflict is to resolve (0=trivial, 1=intractable).",
    )
    context: str = Field(default="", description="Situation that surfaced the conflict.")
    tick: int = Field(default=0, ge=0, description="Tick when the conflict was detected.")
    proposed_resolution: str = Field(default="", description="Suggested resolution strategy, if any.")
    affected_actions: list[str] = Field(default_factory=list, description="Action types blocked or complicated by this conflict.")


class ValuationConfig(BaseModel):
    """Configuration for the Valuation module."""

    default_values: dict[str, float] = Field(
        default_factory=lambda: {
            "self_preservation": 0.8,
            "curiosity": 0.5,
            "social_bonding": 0.5,
            "honesty": 0.7,
            "helpfulness": 0.7,
        },
        description="Initial value weights.",
    )
    conflict_detection_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum weight-difference ratio that counts as a conflict.",
    )
    preference_update_interval: int = Field(default=10, ge=1, description="Ticks between preference recalculations.")
    enable_value_drift: bool = Field(default=True, description="Whether values can shift over time based on experience.")
    drift_rate: float = Field(default=0.01, ge=0.0, le=1.0, description="Maximum per-tick change to any value weight.")
