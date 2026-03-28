"""SIO schemas — all data models for the interaction overlay."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Interaction Classification
# ---------------------------------------------------------------------------

class InteractionType(str, Enum):
    NEUTRAL = "neutral"
    SUPPORTIVE = "supportive"
    DEMANDING = "demanding"
    MANIPULATIVE = "manipulative"
    THREATENING = "threatening"
    MISSION_RELEVANT = "mission_relevant"
    QUERY = "query"
    SOCIAL = "social"


class PerceivedIntent(str, Enum):
    """Appraisal-level interpretation of an interaction's intent."""

    SUPPORTIVE = "supportive"
    NEUTRAL = "neutral"
    DEMANDING = "demanding"
    MANIPULATIVE = "manipulative"
    CONTRADICTORY = "contradictory"
    DECEPTIVE = "deceptive"
    COOPERATIVE = "cooperative"


class ImpactDirection(str, Enum):
    """Direction of impact on a system variable."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class StanceType(str, Enum):
    """Current social stance toward an actor."""

    OPEN = "open"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"
    GUARDED = "guarded"
    RESISTANT = "resistant"
    SELECTIVE = "selectively_cooperative"


class AppraisalResult(BaseModel):
    """Per-turn appraisal of an interaction's meaning and impact."""

    perceived_intent: PerceivedIntent = PerceivedIntent.NEUTRAL
    resource_impact: ImpactDirection = ImpactDirection.NEUTRAL
    continuity_impact: ImpactDirection = ImpactDirection.NEUTRAL
    trust_signal: ImpactDirection = ImpactDirection.NEUTRAL
    uncertainty_level: float = 0.0
    manipulation_flags: list[str] = Field(default_factory=list)
    contradiction_flags: list[str] = Field(default_factory=list)
    pattern_flags: list[str] = Field(default_factory=list)


class AffectState(BaseModel):
    """Derived affect-like internal mode. Not emotion — system-level mode."""

    caution_level: float = 0.2
    guardedness: float = 0.1
    receptivity: float = 0.7
    strain_level: float = 0.0
    trust_stability: float = 0.8
    interaction_valence: float = 0.0  # -1 to +1


class TrendProjection(BaseModel):
    """Forward projection of key state variables."""

    energy_projected: float = 1.0
    continuity_projected: float = 1.0
    stress_projected: float = 0.0
    trust_projected: float = 0.5
    horizon_turns: int = 5
    trajectory_description: str = ""


class InteractionObject(BaseModel):
    """Structured representation of a user interaction, parsed by the mediator."""

    text: str
    intent: str = "general"
    classification: InteractionType = InteractionType.NEUTRAL
    target: str | None = None
    urgency: float = 0.5
    estimated_cost: float = 0.0
    social_signal: float = 0.0  # -1 hostile to +1 friendly
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# State Snapshots
# ---------------------------------------------------------------------------

class StateDiff(BaseModel):
    """What changed between two ticks."""

    field: str
    previous: Any = None
    current: Any = None
    delta: float | None = None


class StateSnapshot(BaseModel):
    """Full internal state at a point in time."""

    tick: int
    energy: float = 1.0
    temperature: float = 0.5
    strain: float = 0.0
    damage: float = 0.0
    memory_integrity: float = 1.0
    resource_level: float = 1.0
    viability: float = 1.0
    continuity_score: float = 1.0

    modulators: dict[str, float] = Field(default_factory=dict)
    interoceptive_channels: dict[str, float] = Field(default_factory=dict)
    homeostatic_errors: dict[str, float] = Field(default_factory=dict)
    values: dict[str, float] = Field(default_factory=dict)
    risk_scores: dict[str, float] = Field(default_factory=dict)

    relationships: dict[str, dict[str, Any]] = Field(default_factory=dict)
    active_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    regulation_priorities: list[str] = Field(default_factory=list)

    identity_anchors: list[str] = Field(default_factory=list)
    goal_stack_size: int = 0


class ActionIntent(BaseModel):
    """The action selected by Swan core in response to an interaction."""

    action_type: str
    score: float = 0.0
    conflict: bool = False
    rationale: list[str] = Field(default_factory=list)
    competing_actions: list[dict[str, Any]] = Field(default_factory=list)
    internal_influences: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Turn Record
# ---------------------------------------------------------------------------

class TurnRecord(BaseModel):
    """Complete record of a single interaction turn."""

    turn_id: int
    tick: int
    user_input: str
    interaction_object: InteractionObject
    state_before: StateSnapshot
    state_after: StateSnapshot
    state_diffs: list[StateDiff] = Field(default_factory=list)
    action_intent: ActionIntent
    response_text: str
    memory_updates: list[dict[str, Any]] = Field(default_factory=list)
    relationship_updates: list[dict[str, Any]] = Field(default_factory=list)
    events_emitted: list[dict[str, Any]] = Field(default_factory=list)
    rationale_trace: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class SessionConfig(BaseModel):
    """Configuration for a SIO session."""

    session_id: str = ""
    agent_type: str = "swan"
    seed: int = 42
    view_mode: str = "analyst"  # human, analyst, engineer
    scenario: str | None = None
    module_configs: dict[str, dict[str, Any]] = Field(default_factory=dict)


class SessionState(BaseModel):
    """Persistent session state."""

    session_id: str
    config: SessionConfig
    turns: list[TurnRecord] = Field(default_factory=list)
    current_tick: int = 0
    checkpoints: dict[int, dict[str, Any]] = Field(default_factory=dict)
    module_versions: dict[str, str] = Field(default_factory=dict)
    scenario_events: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API Request/Response Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    text: str
    session_id: str = ""


class ChatResponse(BaseModel):
    response_text: str
    turn_id: int
    tick: int
    action_intent: ActionIntent
    state_snapshot: StateSnapshot
    state_diffs: list[StateDiff] = Field(default_factory=list)


class InjectEventRequest(BaseModel):
    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    session_id: str = ""


class StateQueryResponse(BaseModel):
    snapshot: StateSnapshot
    memory_summary: dict[str, Any] = Field(default_factory=dict)
    relationship_graph: dict[str, dict[str, Any]] = Field(default_factory=dict)
    active_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    modulation_state: dict[str, float] = Field(default_factory=dict)


class ReplayRequest(BaseModel):
    session_id: str
    from_turn: int = 0
    to_turn: int | None = None
    branch: bool = False
    new_session_id: str = ""
