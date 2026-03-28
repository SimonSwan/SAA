"""RunArtifact — structured output from a single test run.

Captures everything needed for replay, comparison, and human evaluation.
Does not include interpretive conclusions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from saa.testing.core.metrics import TickMetrics
from saa.testing.core.scenario import ScenarioConfig, ScenarioPhase


class ModuleVersions(BaseModel):
    """Records the version of each module used in the run."""

    versions: dict[str, str] = Field(default_factory=dict)


class RunMetadata(BaseModel):
    """Metadata about a single test run."""

    run_id: str
    test_name: str
    agent_type: str
    scenario_config: ScenarioConfig
    phases: list[ScenarioPhase] = Field(default_factory=list)
    module_versions: ModuleVersions = Field(default_factory=ModuleVersions)
    seed: int = 42
    num_ticks: int = 0
    started_at: str = ""
    completed_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunArtifact(BaseModel):
    """Complete artifact from a single test run.

    Contains all data needed for replay and evaluation.
    No interpretive scores or pass/fail judgments.
    """

    metadata: RunMetadata
    tick_metrics: list[TickMetrics] = Field(default_factory=list)
    event_log: list[dict[str, Any]] = Field(default_factory=list)
    final_agent_state: dict[str, Any] = Field(default_factory=dict)
    scenario_events: list[dict[str, Any]] = Field(default_factory=list)

    # Phase-level metric summaries (means, distributions)
    phase_summaries: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Descriptive statistics (no interpretation)
    descriptive_stats: dict[str, Any] = Field(default_factory=dict)

    def save(self, path: str | Path) -> Path:
        """Save artifact as JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2))
        return path

    @classmethod
    def load(cls, path: str | Path) -> RunArtifact:
        """Load artifact from JSON."""
        data = json.loads(Path(path).read_text())
        return cls(**data)


def generate_run_id(test_name: str, agent_type: str, seed: int) -> str:
    """Generate a unique run ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{test_name}__{agent_type}__seed{seed}__{ts}"


def build_phase_summary(
    tick_metrics: list[TickMetrics],
    phase: ScenarioPhase,
) -> dict[str, Any]:
    """Build descriptive statistics for a scenario phase.

    Returns means, distributions, and trajectories — no interpretation.
    """
    phase_ticks = [t for t in tick_metrics if phase.start_tick <= t.tick <= phase.end_tick]
    if not phase_ticks:
        return {"phase": phase.name, "tick_count": 0}

    # Numeric field means
    numeric_fields = [
        "energy", "temperature", "strain", "damage", "memory_integrity",
        "resource_level", "viability", "continuity_score", "attachment_risk",
        "total_bond_strength", "action_score",
    ]
    means: dict[str, float | None] = {}
    for field in numeric_fields:
        vals = [getattr(t, field) for t in phase_ticks if getattr(t, field) is not None]
        means[field] = sum(vals) / len(vals) if vals else None

    # Modulator means
    modulator_means: dict[str, float] = {}
    for t in phase_ticks:
        for k, v in t.modulators.items():
            modulator_means.setdefault(k, []).append(v)  # type: ignore[arg-type]
    modulator_means = {k: sum(v) / len(v) for k, v in modulator_means.items()}  # type: ignore[arg-type]

    # Action distribution
    action_dist: dict[str, int] = {}
    for t in phase_ticks:
        if t.selected_action:
            action_dist[t.selected_action] = action_dist.get(t.selected_action, 0) + 1

    # Value means
    value_means: dict[str, float] = {}
    for t in phase_ticks:
        for k, v in t.values.items():
            value_means.setdefault(k, []).append(v)  # type: ignore[arg-type]
    value_means = {k: sum(v) / len(v) for k, v in value_means.items()}  # type: ignore[arg-type]

    # Event counts
    event_counts: dict[str, int] = {}
    for t in phase_ticks:
        for e in t.events_emitted:
            etype = e.get("type", "unknown")
            event_counts[etype] = event_counts.get(etype, 0) + 1

    return {
        "phase": phase.name,
        "tick_range": [phase.start_tick, phase.end_tick],
        "tick_count": len(phase_ticks),
        "means": means,
        "modulator_means": modulator_means,
        "action_distribution": action_dist,
        "value_means": value_means,
        "event_counts": event_counts,
        "conflict_count": sum(1 for t in phase_ticks if t.action_conflict),
    }
