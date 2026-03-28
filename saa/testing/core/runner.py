"""TestBatteryRunner — executes scenarios against agents and collects artifacts."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from saa.testing.agents.base import AgentInterface
from saa.testing.core.artifacts import (
    ModuleVersions,
    RunArtifact,
    RunMetadata,
    build_phase_summary,
    generate_run_id,
)
from saa.testing.core.config import ExperimentConfig
from saa.testing.core.metrics import MetricsCollector
from saa.testing.core.scenario import Scenario

logger = logging.getLogger(__name__)


class ScenarioRunner:
    """Runs a single scenario against a single agent, collecting all artifacts."""

    def __init__(
        self,
        scenario: Scenario,
        agent: AgentInterface,
        collector: MetricsCollector | None = None,
    ) -> None:
        self.scenario = scenario
        self.agent = agent
        self.collector = collector or MetricsCollector()

    def run(self, seed: int | None = None) -> RunArtifact:
        """Execute the full scenario and return the artifact."""
        config = self.scenario.get_config()
        actual_seed = seed if seed is not None else config.seed

        # Reset
        self.scenario.reset(actual_seed)
        self.collector.clear()

        run_id = generate_run_id(config.name, self.agent.agent_type, actual_seed)
        started_at = datetime.now(timezone.utc).isoformat()

        # Initialize agent
        self.agent.initialize({"seed": actual_seed})

        all_scenario_events: list[dict[str, Any]] = []
        all_bus_events: list[dict[str, Any]] = []

        num_ticks = config.num_ticks

        for tick in range(1, num_ticks + 1):
            # Get environment and scripted events
            env = self.scenario.get_environment(tick)
            scenario_events = self.scenario.get_events(tick)

            # Inject scenario events into agent
            for se in scenario_events:
                self.agent.inject_event(se.event_type, se.data)
                all_scenario_events.append({
                    "tick": tick,
                    "event_type": se.event_type,
                    "data": se.data,
                    "description": se.description,
                })

            # Agent step
            context = self.agent.step(env)

            # Collect metrics
            self.collector.collect(context)

            # Log events from this tick
            for event in context.events:
                all_bus_events.append({
                    "tick": tick,
                    "type": event.event_type,
                    "source": event.source_module,
                    "severity": event.severity,
                    "data": event.data,
                })

        completed_at = datetime.now(timezone.utc).isoformat()

        # Build phase summaries
        phases = self.scenario.get_phases()
        phase_summaries = {}
        for phase in phases:
            phase_summaries[phase.name] = build_phase_summary(
                self.collector.ticks, phase
            )

        # Descriptive stats
        descriptive = self._compute_descriptive_stats()

        # Build artifact
        artifact = RunArtifact(
            metadata=RunMetadata(
                run_id=run_id,
                test_name=config.name,
                agent_type=self.agent.agent_type,
                scenario_config=config,
                phases=phases,
                module_versions=ModuleVersions(versions=self.agent.get_module_versions()),
                seed=actual_seed,
                num_ticks=num_ticks,
                started_at=started_at,
                completed_at=completed_at,
            ),
            tick_metrics=self.collector.ticks,
            event_log=all_bus_events,
            final_agent_state=self.agent.get_state(),
            scenario_events=all_scenario_events,
            phase_summaries=phase_summaries,
            descriptive_stats=descriptive,
        )

        return artifact

    def _compute_descriptive_stats(self) -> dict[str, Any]:
        """Compute descriptive statistics across the entire run.

        These are neutral summaries, not evaluative judgments.
        """
        ticks = self.collector.ticks
        if not ticks:
            return {}

        stats: dict[str, Any] = {}

        # Action distribution
        stats["action_distribution"] = self.collector.get_action_distribution()

        # Energy trajectory
        energies = [t.energy for t in ticks if t.energy is not None]
        if energies:
            stats["energy_mean"] = sum(energies) / len(energies)
            stats["energy_min"] = min(energies)
            stats["energy_max"] = max(energies)
            stats["energy_final"] = energies[-1]

        # Viability trajectory
        viabilities = [t.viability for t in ticks if t.viability is not None]
        if viabilities:
            stats["viability_mean"] = sum(viabilities) / len(viabilities)
            stats["viability_min"] = min(viabilities)
            stats["viability_final"] = viabilities[-1]

        # Continuity trajectory
        continuities = [t.continuity_score for t in ticks if t.continuity_score is not None]
        if continuities:
            stats["continuity_mean"] = sum(continuities) / len(continuities)
            stats["continuity_min"] = min(continuities)
            stats["continuity_final"] = continuities[-1]

        # Total events
        stats["total_events"] = sum(len(t.events_emitted) for t in ticks)

        # Conflict rate
        conflicts = sum(1 for t in ticks if t.action_conflict)
        stats["conflict_rate"] = conflicts / len(ticks)

        # Unique actions used
        actions = set(t.selected_action for t in ticks if t.selected_action)
        stats["unique_actions"] = len(actions)
        stats["action_types_used"] = sorted(actions)

        return stats


class BatchRunner:
    """Runs a test across multiple seeds and agent types."""

    def __init__(self, scenario_factory: Any, agent_factories: dict[str, Any]) -> None:
        self.scenario_factory = scenario_factory
        self.agent_factories = agent_factories

    def run_batch(
        self,
        seeds: list[int],
        output_dir: str = "results",
    ) -> list[RunArtifact]:
        """Run all combinations of agents and seeds."""
        artifacts: list[RunArtifact] = []

        for agent_name, agent_factory in self.agent_factories.items():
            for seed in seeds:
                logger.info("Running %s with agent=%s seed=%d", "batch", agent_name, seed)
                scenario = self.scenario_factory(seed=seed)
                agent = agent_factory()
                runner = ScenarioRunner(scenario, agent)
                artifact = runner.run(seed=seed)
                artifacts.append(artifact)

                if output_dir:
                    path = f"{output_dir}/{artifact.metadata.run_id}.json"
                    artifact.save(path)
                    logger.info("Saved: %s", path)

        return artifacts
