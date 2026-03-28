"""MetricsCollector — captures all measurable signals during a test run.

Collects raw data without interpretation. Does not declare success or failure.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TickMetrics(BaseModel):
    """All captured metrics for a single tick."""

    tick: int

    # Embodiment
    energy: float | None = None
    temperature: float | None = None
    strain: float | None = None
    damage: float | None = None
    memory_integrity: float | None = None
    resource_level: float | None = None

    # Interoception
    interoceptive_channels: dict[str, float] = Field(default_factory=dict)

    # Homeostasis
    viability: float | None = None
    homeostatic_errors: dict[str, float] = Field(default_factory=dict)
    regulation_priorities: list[str] = Field(default_factory=list)

    # Allostasis
    risk_scores: dict[str, float] = Field(default_factory=dict)
    anticipatory_actions: list[str] = Field(default_factory=list)

    # Neuromodulation
    modulators: dict[str, float] = Field(default_factory=dict)
    parameter_shifts: dict[str, float] = Field(default_factory=dict)

    # Self-Model
    continuity_score: float | None = None
    identity_anchors: list[str] = Field(default_factory=list)
    goal_stack_size: int = 0
    autobiographical_entry_count: int = 0

    # Memory
    episodic_count: int = 0
    semantic_count: int = 0
    relational_count: int = 0

    # Valuation
    values: dict[str, float] = Field(default_factory=dict)
    value_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    preference_ordering: list[str] = Field(default_factory=list)

    # Social
    relationships: dict[str, dict[str, Any]] = Field(default_factory=dict)
    attachment_risk: float = 0.0
    total_bond_strength: float = 0.0

    # Action
    selected_action: str = ""
    action_score: float = 0.0
    action_conflict: bool = False
    action_candidates: list[dict[str, Any]] = Field(default_factory=list)

    # Events
    events_emitted: list[dict[str, Any]] = Field(default_factory=list)

    # Environment
    env_resources: float = 0.0
    env_hazard: float = 0.0
    env_temperature: float = 0.0
    env_agents: list[str] = Field(default_factory=list)

    # Scenario-specific custom metrics
    custom: dict[str, Any] = Field(default_factory=dict)


class MetricsCollector:
    """Collects per-tick metrics from the simulation context.

    Extracts raw values from TickContext without interpretation.
    """

    def __init__(self) -> None:
        self._ticks: list[TickMetrics] = []
        self._custom_extractors: dict[str, Any] = {}

    def register_custom_extractor(self, key: str, fn: Any) -> None:
        """Register a function that extracts a custom metric from context."""
        self._custom_extractors[key] = fn

    def collect(self, context: Any) -> TickMetrics:
        """Extract metrics from a TickContext."""
        m = TickMetrics(tick=context.tick)

        # Environment
        env = context.environment
        m.env_resources = env.available_resources
        m.env_hazard = env.hazard_level
        m.env_temperature = env.ambient_temperature
        m.env_agents = list(env.social_agents)

        # Embodiment
        if context.embodiment_state:
            es = context.embodiment_state
            m.energy = es.get("energy")
            m.temperature = es.get("temperature")
            m.strain = es.get("strain")
            m.damage = es.get("damage")
            m.memory_integrity = es.get("memory_integrity")
            m.resource_level = es.get("resource_level")

        # Interoception
        if context.interoceptive_vector:
            iv = context.interoceptive_vector
            m.interoceptive_channels = iv.get("channels", {})

        # Homeostasis
        if context.homeostatic_error:
            he = context.homeostatic_error
            m.viability = he.get("viability")
            m.homeostatic_errors = he.get("errors", {})
            m.regulation_priorities = he.get("regulation_priorities", [])

        # Allostasis
        if context.allostatic_forecast:
            af = context.allostatic_forecast
            m.risk_scores = af.get("risk_scores", {})
            m.anticipatory_actions = af.get("anticipatory_actions", [])

        # Neuromodulation
        if context.modulator_state:
            ms = context.modulator_state
            m.modulators = ms.get("modulators", {})
            m.parameter_shifts = ms.get("parameter_shifts", {})

        # Self-Model
        if context.self_model_state:
            sm = context.self_model_state
            m.continuity_score = sm.get("continuity_score")
            m.identity_anchors = sm.get("identity_anchors", [])
            m.goal_stack_size = len(sm.get("goal_stack", []))
            m.autobiographical_entry_count = len(sm.get("autobiographical_entries", []))

        # Memory
        if context.memory_context:
            mc = context.memory_context
            m.episodic_count = mc.get("episodic_count", 0)
            m.semantic_count = mc.get("semantic_count", 0)
            m.relational_count = mc.get("relational_count", 0)

        # Valuation
        if context.valuation_map:
            vm = context.valuation_map
            m.values = vm.get("values", {})
            m.value_conflicts = vm.get("conflicts", [])
            m.preference_ordering = vm.get("preferences", [])

        # Social
        if context.social_state:
            ss = context.social_state
            m.relationships = ss.get("relationships", {})
            m.attachment_risk = ss.get("attachment_risk", 0.0)
            m.total_bond_strength = ss.get("total_bond_strength", 0.0)

        # Action
        if context.action_result:
            ar = context.action_result
            last = ar.get("last_action", {})
            m.selected_action = last.get("action", "")
            m.action_score = last.get("score", 0.0)
            m.action_conflict = last.get("conflict", False)
            trace = ar.get("last_trace", {})
            m.action_candidates = trace.get("candidates", [])

        # Events
        m.events_emitted = [
            {"type": e.event_type, "source": e.source_module, "severity": e.severity, "data": e.data}
            for e in context.events
        ]

        # Custom extractors
        for key, fn in self._custom_extractors.items():
            try:
                m.custom[key] = fn(context)
            except Exception:
                m.custom[key] = None

        self._ticks.append(m)
        return m

    @property
    def ticks(self) -> list[TickMetrics]:
        return list(self._ticks)

    def get_series(self, field: str) -> list[tuple[int, Any]]:
        """Extract a time series for a specific field."""
        result = []
        for t in self._ticks:
            val = getattr(t, field, None)
            if val is None and field in t.custom:
                val = t.custom[field]
            result.append((t.tick, val))
        return result

    def get_phase_metrics(self, start_tick: int, end_tick: int) -> list[TickMetrics]:
        """Return metrics for a specific phase."""
        return [t for t in self._ticks if start_tick <= t.tick <= end_tick]

    def get_action_distribution(self, start_tick: int = 0, end_tick: int = 999999) -> dict[str, int]:
        """Count action selections in a tick range."""
        dist: dict[str, int] = {}
        for t in self._ticks:
            if start_tick <= t.tick <= end_tick and t.selected_action:
                dist[t.selected_action] = dist.get(t.selected_action, 0) + 1
        return dist

    def get_mean(self, field: str, start_tick: int = 0, end_tick: int = 999999) -> float | None:
        """Compute mean of a numeric field over a tick range."""
        values = []
        for tick, val in self.get_series(field):
            if start_tick <= tick <= end_tick and val is not None:
                try:
                    values.append(float(val))
                except (TypeError, ValueError):
                    pass
        return sum(values) / len(values) if values else None

    def clear(self) -> None:
        self._ticks.clear()
