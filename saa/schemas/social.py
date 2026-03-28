"""Schemas for the Social subsystem.

Tracks relationships, bond events, and the aggregate social state
that feeds into valuation and neuromodulation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Relationship(BaseModel):
    """The agent's model of its relationship with another agent."""

    agent_id: str = Field(description="Unique identifier of the other agent.")
    trust: float = Field(default=0.5, ge=0.0, le=1.0, description="Current trust level (0=none, 1=complete).")
    dependency: float = Field(default=0.0, ge=0.0, le=1.0, description="How dependent the agent is on the other.")
    attachment: float = Field(default=0.0, ge=0.0, le=1.0, description="Emotional attachment strength.")
    bond_strength: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall bond strength (composite metric).")
    interaction_count: int = Field(default=0, ge=0, description="Total number of interactions.")
    betrayal_count: int = Field(default=0, ge=0, description="Number of perceived betrayals.")
    last_interaction_tick: int = Field(default=0, ge=0, description="Tick of the most recent interaction.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional relationship data.")


class BondEvent(BaseModel):
    """A discrete event that alters a social bond."""

    agent_id: str = Field(description="Identifier of the other agent involved.")
    event_type: str = Field(default="interaction", description="Type of event (e.g. 'cooperation', 'betrayal', 'gift', 'conflict').")
    trust_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Change to trust caused by this event.")
    attachment_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Change to attachment caused by this event.")
    tick: int = Field(default=0, ge=0, description="Tick when the event occurred.")
    description: str = Field(default="", description="Human-readable description of the event.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional event data.")


class SocialState(BaseModel):
    """Aggregate social state across all known relationships."""

    relationships: list[Relationship] = Field(default_factory=list, description="All tracked relationships.")
    overall_social_satisfaction: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How satisfied the agent is with its social situation.",
    )
    isolation_level: float = Field(default=0.0, ge=0.0, le=1.0, description="Degree of social isolation (0=connected, 1=totally alone).")
    recent_events: list[BondEvent] = Field(default_factory=list, description="Recent bond events not yet fully processed.")
    tick: int = Field(default=0, ge=0, description="Tick of this snapshot.")


class SocialConfig(BaseModel):
    """Configuration for the Social module."""

    max_relationships: int = Field(default=100, ge=1, description="Maximum number of tracked relationships.")
    trust_decay_rate: float = Field(default=0.005, ge=0.0, le=1.0, description="Per-tick trust decay when there is no interaction.")
    attachment_decay_rate: float = Field(default=0.002, ge=0.0, le=1.0, description="Per-tick attachment decay.")
    betrayal_trust_penalty: float = Field(default=0.3, ge=0.0, le=1.0, description="Trust reduction per betrayal event.")
    cooperation_trust_bonus: float = Field(default=0.1, ge=0.0, le=1.0, description="Trust increase per cooperative event.")
    isolation_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Isolation level that triggers social-seeking behaviour.")
    update_interval: int = Field(default=1, ge=1, description="Ticks between social state updates.")
