"""Replay — load and inspect saved run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from saa.testing.core.artifacts import RunArtifact
from saa.testing.core.metrics import TickMetrics


class ReplayViewer:
    """Load and inspect a saved run artifact."""

    def __init__(self, artifact: RunArtifact) -> None:
        self.artifact = artifact

    @classmethod
    def from_file(cls, path: str | Path) -> ReplayViewer:
        return cls(RunArtifact.load(path))

    @property
    def metadata(self):
        return self.artifact.metadata

    @property
    def ticks(self) -> list[TickMetrics]:
        return self.artifact.tick_metrics

    def get_tick(self, tick: int) -> TickMetrics | None:
        for t in self.ticks:
            if t.tick == tick:
                return t
        return None

    def get_series(self, field: str) -> list[tuple[int, Any]]:
        """Extract a time series for any field."""
        result = []
        for t in self.ticks:
            val = getattr(t, field, None)
            if val is None and field in t.custom:
                val = t.custom[field]
            result.append((t.tick, val))
        return result

    def get_relationship_history(self, agent_id: str) -> list[tuple[int, dict]]:
        """Track a specific relationship over time."""
        history = []
        for t in self.ticks:
            rel = t.relationships.get(agent_id)
            if rel is not None:
                history.append((t.tick, dict(rel)))
        return history

    def get_events_of_type(self, event_type: str) -> list[dict]:
        """Filter events by type across all ticks."""
        events = []
        for entry in self.artifact.event_log:
            if entry.get("type") == event_type:
                events.append(entry)
        return events

    def get_scenario_events(self) -> list[dict]:
        return self.artifact.scenario_events

    def get_phase_data(self, phase_name: str) -> dict[str, Any]:
        return self.artifact.phase_summaries.get(phase_name, {})

    def print_summary(self) -> str:
        """Return a human-readable summary of the run."""
        m = self.metadata
        s = self.artifact.descriptive_stats
        lines = [
            f"=== Run: {m.run_id} ===",
            f"Test: {m.test_name}",
            f"Agent: {m.agent_type}",
            f"Seed: {m.seed}",
            f"Ticks: {m.num_ticks}",
            f"Phases: {', '.join(p.name for p in m.phases)}",
            "",
            "--- Descriptive Stats ---",
        ]
        for k, v in sorted(s.items()):
            if isinstance(v, float):
                lines.append(f"  {k}: {v:.4f}")
            else:
                lines.append(f"  {k}: {v}")

        lines.append("")
        lines.append("--- Phase Summaries ---")
        for phase_name, data in self.artifact.phase_summaries.items():
            lines.append(f"  [{phase_name}] ticks: {data.get('tick_count', 0)}")
            means = data.get("means", {})
            for mk, mv in means.items():
                if mv is not None:
                    lines.append(f"    {mk}: {mv:.4f}")
            ad = data.get("action_distribution", {})
            if ad:
                lines.append(f"    actions: {ad}")

        return "\n".join(lines)


def export_series_csv(
    artifact: RunArtifact,
    fields: list[str],
    output_path: str | Path,
) -> None:
    """Export selected time series as CSV for external analysis."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    header = ["tick"] + fields
    rows = []
    for t in artifact.tick_metrics:
        row = [str(t.tick)]
        for f in fields:
            val = getattr(t, f, None)
            if val is None and f in t.custom:
                val = t.custom[f]
            row.append(str(val) if val is not None else "")
        rows.append(",".join(row))

    content = ",".join(header) + "\n" + "\n".join(rows) + "\n"
    path.write_text(content)
