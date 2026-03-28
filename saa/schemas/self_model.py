"""Schemas for the Self-Model subsystem.

The self-model maintains the agent's sense of identity, continuity over
time, and autobiographical narrative.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IdentityAnchor(BaseModel):
    """A core belief or value that anchors the agent's identity."""

    label: str = Field(description="Short name for this anchor (e.g. 'helpfulness', 'honesty').")
    description: str = Field(default="", description="Longer explanation of what this anchor means to the agent.")
    strength: float = Field(default=1.0, ge=0.0, le=1.0, description="How deeply rooted this anchor is (0=tenuous, 1=foundational).")
    formed_at_tick: int = Field(default=0, ge=0, description="Tick when this anchor was first established.")


class ContinuityThreat(BaseModel):
    """An event or condition that threatens the agent's sense of self-continuity."""

    threat_type: str = Field(description="Category of threat (e.g. 'memory_loss', 'goal_conflict', 'identity_drift').")
    severity: float = Field(default=0.5, ge=0.0, le=1.0, description="How severe the threat is to continuity.")
    affected_anchors: list[str] = Field(default_factory=list, description="Identity-anchor labels affected by this threat.")
    tick: int = Field(default=0, ge=0, description="Tick when the threat was detected.")
    description: str = Field(default="", description="Human-readable description of the threat.")
    resolved: bool = Field(default=False, description="Whether the threat has been addressed.")


class AutobiographicalEntry(BaseModel):
    """A significant event recorded in the agent's life narrative."""

    tick: int = Field(default=0, ge=0, description="Tick when the event occurred.")
    summary: str = Field(default="", description="Brief description of the event.")
    emotional_valence: float = Field(default=0.0, ge=-1.0, le=1.0, description="Emotional tone (-1=very negative, +1=very positive).")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Significance of this event to the agent's narrative.")
    related_anchors: list[str] = Field(default_factory=list, description="Identity anchors this event relates to.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional structured data about the event.")


class SelfModelState(BaseModel):
    """Current state of the agent's self-model."""

    identity_anchors: list[str] = Field(
        default_factory=list,
        description="Labels of the active identity anchors.",
    )
    continuity_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Overall sense of self-continuity (0=fragmented, 1=fully coherent).",
    )
    goal_stack: list[str] = Field(
        default_factory=list,
        description="Ordered list of active goals, highest priority first.",
    )
    autobiographical_entries: list[AutobiographicalEntry] = Field(
        default_factory=list,
        description="Chronological record of significant life events.",
    )
    active_threats: list[ContinuityThreat] = Field(
        default_factory=list,
        description="Unresolved threats to self-continuity.",
    )
    tick: int = Field(default=0, ge=0, description="Tick of this state snapshot.")


class SelfModelConfig(BaseModel):
    """Configuration for the Self-Model module."""

    max_autobiographical_entries: int = Field(default=1000, ge=1, description="Maximum entries kept in the autobiographical log.")
    continuity_decay_rate: float = Field(default=0.01, ge=0.0, le=1.0, description="Per-tick passive decay of continuity score when threats are present.")
    identity_anchor_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum strength for an anchor to remain active.")
    update_interval: int = Field(default=1, ge=1, description="Ticks between self-model updates.")
    max_goal_stack_depth: int = Field(default=20, ge=1, description="Maximum number of simultaneous goals tracked.")
