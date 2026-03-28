"""ComparisonRunner — batch comparison across agents, seeds, and versions.

Produces descriptive comparison tables without interpretive judgments.
"""

from __future__ import annotations

from typing import Any

from saa.testing.core.artifacts import RunArtifact


class ComparisonResult(object):
    """Holds comparison data across multiple runs.

    All comparisons are descriptive. No pass/fail determination.
    """

    def __init__(self, artifacts: list[RunArtifact]) -> None:
        self.artifacts = artifacts

    def by_agent_type(self) -> dict[str, list[RunArtifact]]:
        """Group artifacts by agent type."""
        groups: dict[str, list[RunArtifact]] = {}
        for a in self.artifacts:
            groups.setdefault(a.metadata.agent_type, []).append(a)
        return groups

    def by_seed(self) -> dict[int, list[RunArtifact]]:
        """Group artifacts by seed."""
        groups: dict[int, list[RunArtifact]] = {}
        for a in self.artifacts:
            groups.setdefault(a.metadata.seed, []).append(a)
        return groups

    def compare_metric(self, metric: str) -> dict[str, dict[str, float | None]]:
        """Compare a descriptive stat across agent types.

        Returns {agent_type: {seed_N: value, ...}}.
        """
        result: dict[str, dict[str, float | None]] = {}
        for a in self.artifacts:
            agent = a.metadata.agent_type
            seed_key = f"seed_{a.metadata.seed}"
            result.setdefault(agent, {})[seed_key] = a.descriptive_stats.get(metric)
        return result

    def compare_action_distributions(self) -> dict[str, dict[str, int]]:
        """Aggregate action distributions by agent type."""
        result: dict[str, dict[str, int]] = {}
        for a in self.artifacts:
            agent = a.metadata.agent_type
            dist = a.descriptive_stats.get("action_distribution", {})
            if agent not in result:
                result[agent] = {}
            for action, count in dist.items():
                result[agent][action] = result[agent].get(action, 0) + count
        return result

    def compare_phase_metric(
        self, phase_name: str, metric_path: str
    ) -> dict[str, list[Any]]:
        """Compare a metric within a specific phase across agents.

        metric_path is a dot-separated path like "means.energy" or "action_distribution".
        Returns {agent_type: [value_per_run, ...]}.
        """
        result: dict[str, list[Any]] = {}
        for a in self.artifacts:
            agent = a.metadata.agent_type
            phase_data = a.phase_summaries.get(phase_name, {})
            # Navigate the path
            val: Any = phase_data
            for key in metric_path.split("."):
                if isinstance(val, dict):
                    val = val.get(key)
                else:
                    val = None
                    break
            result.setdefault(agent, []).append(val)
        return result

    def summary_table(self) -> list[dict[str, Any]]:
        """Generate a summary table with one row per run.

        Columns: run_id, agent_type, seed, energy_final, viability_final,
        continuity_final, conflict_rate, unique_actions, total_events.
        """
        rows = []
        for a in self.artifacts:
            s = a.descriptive_stats
            rows.append({
                "run_id": a.metadata.run_id,
                "agent_type": a.metadata.agent_type,
                "seed": a.metadata.seed,
                "energy_final": s.get("energy_final"),
                "viability_final": s.get("viability_final"),
                "continuity_final": s.get("continuity_final"),
                "conflict_rate": s.get("conflict_rate"),
                "unique_actions": s.get("unique_actions"),
                "total_events": s.get("total_events"),
            })
        return rows
