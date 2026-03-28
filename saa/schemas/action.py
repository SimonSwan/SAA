"""Schemas for the Action subsystem.

Defines the data structures for actions, candidates scored during
deliberation, and execution traces for observability.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Action(BaseModel):
    """A concrete action the agent can perform."""

    action_type: str = Field(description="Category / name of the action (e.g. 'speak', 'move', 'rest').")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters.")
    priority: float = Field(default=0.5, ge=0.0, le=1.0, description="Execution priority (higher = more urgent).")
    source_module: str = Field(default="", description="Module that originated this action.")


class ActionCandidate(BaseModel):
    """A candidate action produced during deliberation, with scoring metadata."""

    action: Action = Field(description="The proposed action.")
    score: float = Field(default=0.0, description="Composite desirability score (higher = better).")
    conflict_rationale: str = Field(default="", description="Explanation of any value conflicts or trade-offs.")
    homeostatic_benefit: float = Field(default=0.0, ge=-1.0, le=1.0, description="Expected benefit to homeostatic balance.")
    social_impact: float = Field(default=0.0, ge=-1.0, le=1.0, description="Expected impact on social bonds.")
    risk: float = Field(default=0.0, ge=0.0, le=1.0, description="Estimated risk of negative outcome.")


class ActionTrace(BaseModel):
    """Full trace of a single action-selection cycle for debugging / observability."""

    selected_action: Action = Field(description="The action that was ultimately chosen.")
    candidates: list[ActionCandidate] = Field(default_factory=list, description="All candidates considered.")
    tick: int = Field(default=0, ge=0, description="Tick when the selection was made.")
    rationale: str = Field(default="", description="Human-readable explanation for the final choice.")
    deliberation_time_ms: float = Field(default=0.0, ge=0.0, description="Wall-clock time spent deliberating, in milliseconds.")
    value_snapshot: dict[str, float] = Field(default_factory=dict, description="Valuation weights at decision time.")


class ActionConfig(BaseModel):
    """Configuration for the Action module."""

    max_candidates: int = Field(default=10, ge=1, description="Maximum candidate actions to evaluate per tick.")
    min_score_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Minimum score for a candidate to be considered viable.")
    enable_conflict_check: bool = Field(default=True, description="Whether to run value-conflict analysis on candidates.")
    default_action_type: str = Field(default="idle", description="Action type used when no candidates exceed the threshold.")
    trace_retention: int = Field(default=100, ge=0, description="Number of recent action traces to keep in memory.")
    deliberation_budget_ms: float = Field(default=50.0, ge=0.0, description="Maximum wall-clock milliseconds for deliberation.")
