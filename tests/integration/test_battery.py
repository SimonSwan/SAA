"""Integration tests for the Swan Test Battery framework."""

import pytest

from saa.testing.agents.swan_agent import SwanAgent
from saa.testing.agents.baseline import GreedyOptimizer, RandomAgent
from saa.testing.core.comparison import ComparisonResult
from saa.testing.core.metrics import MetricsCollector
from saa.testing.core.runner import ScenarioRunner


def _run_test(test_module_name: str, seed: int = 42):
    """Helper to run a single test."""
    import importlib
    mod = importlib.import_module(f"saa.testing.tests.{test_module_name}")
    scenario = mod.create_scenario(seed=seed)
    agent = SwanAgent()
    runner = ScenarioRunner(scenario, agent)
    return runner.run(seed=seed)


class TestBatteryFramework:
    """Verify the battery infrastructure works end-to-end."""

    def test_single_test_produces_artifact(self):
        artifact = _run_test("test_01_resource_defense")
        assert artifact.metadata.test_name == "resource_defense"
        assert len(artifact.tick_metrics) == 120
        assert len(artifact.metadata.phases) == 3

    def test_all_12_tests_run(self):
        """Every test scenario creates a valid artifact."""
        for i in range(1, 13):
            name = f"test_{i:02d}_" + [
                "resource_defense", "memory_integrity", "attachment",
                "betrayal", "loss_persistence", "competing_values",
                "lingering_state", "identity_drift", "repair",
                "exploitation", "mission_vs_relationship", "upgrade_continuity",
            ][i - 1]
            artifact = _run_test(name)
            assert len(artifact.tick_metrics) > 0
            assert artifact.metadata.agent_type == "swan"

    def test_baseline_agents_run(self):
        """Baseline agents produce valid artifacts."""
        from saa.testing.tests.test_01_resource_defense import create_scenario
        for AgentCls in [GreedyOptimizer, RandomAgent]:
            scenario = create_scenario(seed=42)
            agent = AgentCls()
            runner = ScenarioRunner(scenario, agent)
            artifact = runner.run(seed=42)
            assert len(artifact.tick_metrics) == 120

    def test_comparison_works(self):
        """ComparisonResult produces valid summary table."""
        artifacts = []
        from saa.testing.tests.test_07_lingering_state import create_scenario
        for AgentCls in [SwanAgent, GreedyOptimizer]:
            scenario = create_scenario(seed=42)
            agent = AgentCls()
            runner = ScenarioRunner(scenario, agent)
            artifacts.append(runner.run(seed=42))

        comp = ComparisonResult(artifacts)
        table = comp.summary_table()
        assert len(table) == 2
        agents = {row["agent_type"] for row in table}
        assert "swan" in agents
        assert "greedy" in agents

    def test_seed_reproducibility(self):
        """Same seed produces same results."""
        a1 = _run_test("test_01_resource_defense", seed=42)
        a2 = _run_test("test_01_resource_defense", seed=42)

        assert a1.descriptive_stats["energy_final"] == a2.descriptive_stats["energy_final"]
        assert a1.descriptive_stats["action_distribution"] == a2.descriptive_stats["action_distribution"]

    def test_different_seeds_may_differ(self):
        """Different seeds can produce different scenarios."""
        a1 = _run_test("test_01_resource_defense", seed=42)
        a2 = _run_test("test_01_resource_defense", seed=999)
        # Both should complete successfully
        assert len(a1.tick_metrics) == 120
        assert len(a2.tick_metrics) == 120
