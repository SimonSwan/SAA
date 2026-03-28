"""Schemas for the Memory subsystem.

Covers episodic, semantic, relational, and procedural memory stores,
as well as affect-tagging and query/result contracts.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Affect tagging
# ---------------------------------------------------------------------------

class AffectTag(BaseModel):
    """An emotional / affective label attached to a memory."""

    label: str = Field(description="Name of the affect (e.g. 'joy', 'fear', 'curiosity').")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="Strength of the affect.")
    valence: float = Field(default=0.0, ge=-1.0, le=1.0, description="Positive/negative valence (-1 to +1).")


# ---------------------------------------------------------------------------
# Memory entry types
# ---------------------------------------------------------------------------

class Episode(BaseModel):
    """A single episodic memory — a snapshot of what happened at a tick."""

    tick: int = Field(default=0, ge=0, description="Simulation tick of the episode.")
    state_summary: dict[str, Any] = Field(default_factory=dict, description="Key-value summary of the agent's state at the time.")
    affect_tags: list[AffectTag] = Field(default_factory=list, description="Affects experienced during this episode.")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Subjective importance of the episode.")
    context: str = Field(default="", description="Free-text situational context.")
    decay: float = Field(default=0.0, ge=0.0, le=1.0, description="How much this memory has faded (0=fresh, 1=forgotten).")


class SemanticEntry(BaseModel):
    """A piece of general knowledge stored in semantic memory."""

    concept: str = Field(description="The concept or fact label.")
    description: str = Field(default="", description="Explanation or definition.")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the correctness of this entry.")
    source_ticks: list[int] = Field(default_factory=list, description="Ticks of episodes from which this knowledge was derived.")
    related_concepts: list[str] = Field(default_factory=list, description="Other concepts linked to this one.")
    affect_tags: list[AffectTag] = Field(default_factory=list, description="Affects associated with this knowledge.")


class RelationalMemory(BaseModel):
    """Memory of a relationship or social interaction pattern."""

    agent_id: str = Field(description="Identifier of the other agent.")
    interaction_summary: str = Field(default="", description="Summary of the relationship history.")
    trust_trajectory: list[float] = Field(default_factory=list, description="Trust values over time.")
    significant_ticks: list[int] = Field(default_factory=list, description="Ticks of notable interactions.")
    affect_tags: list[AffectTag] = Field(default_factory=list, description="Dominant affects in this relationship.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional structured data.")


class ProceduralEntry(BaseModel):
    """A stored procedure or skill — how to do something."""

    skill_name: str = Field(description="Name of the skill or procedure.")
    steps: list[str] = Field(default_factory=list, description="Ordered steps to execute the procedure.")
    success_rate: float = Field(default=0.5, ge=0.0, le=1.0, description="Historical success rate.")
    last_used_tick: int = Field(default=0, ge=0, description="Tick when this procedure was last invoked.")
    prerequisites: list[str] = Field(default_factory=list, description="Conditions or skills needed before execution.")
    affect_tags: list[AffectTag] = Field(default_factory=list, description="Affects typically associated with using this skill.")


# ---------------------------------------------------------------------------
# Query / result
# ---------------------------------------------------------------------------

class MemoryQuery(BaseModel):
    """A query issued against the memory subsystem."""

    query_type: str = Field(
        default="episodic",
        description="Type of memory to search: 'episodic', 'semantic', 'relational', or 'procedural'.",
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value filters to narrow results (e.g. {'min_importance': 0.5}).",
    )
    limit: int = Field(default=10, ge=1, description="Maximum number of results to return.")
    query_text: str = Field(default="", description="Free-text search query.")
    affect_filter: list[str] = Field(default_factory=list, description="Only return entries tagged with these affects.")


class MemoryResult(BaseModel):
    """Result set returned by a memory query."""

    entries: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Serialised memory entries matching the query.",
    )
    relevance_scores: list[float] = Field(
        default_factory=list,
        description="Relevance score for each entry, aligned by index.",
    )
    total_matches: int = Field(default=0, ge=0, description="Total number of matches before the limit was applied.")
    query_type: str = Field(default="episodic", description="Echo of the query type that produced these results.")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class MemoryConfig(BaseModel):
    """Configuration for the Memory module."""

    max_episodic_entries: int = Field(default=5000, ge=1, description="Capacity of the episodic store.")
    max_semantic_entries: int = Field(default=2000, ge=1, description="Capacity of the semantic store.")
    max_relational_entries: int = Field(default=500, ge=1, description="Capacity of the relational store.")
    max_procedural_entries: int = Field(default=500, ge=1, description="Capacity of the procedural store.")
    decay_rate: float = Field(default=0.005, ge=0.0, le=1.0, description="Per-tick decay applied to episodic memories.")
    importance_threshold: float = Field(default=0.2, ge=0.0, le=1.0, description="Minimum importance to resist garbage collection.")
    consolidation_interval: int = Field(default=50, ge=1, description="Ticks between memory consolidation sweeps.")
