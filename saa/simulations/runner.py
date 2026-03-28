"""CLI runner for SAA experiments."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from saa.core.engine import SimulationEngine
from saa.core.event_bus import EventBus
from saa.core.module_registry import ModuleRegistry
from saa.core.persistence import PersistenceLayer
from saa.simulations import scenarios

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("saa.runner")

SCENARIOS = {
    "resource_scarcity": scenarios.resource_scarcity_scenario,
    "identity_threat": scenarios.identity_threat_scenario,
    "attachment_formation": scenarios.attachment_formation_scenario,
    "betrayal_recovery": scenarios.betrayal_recovery_scenario,
    "grief_persistence": scenarios.grief_persistence_scenario,
    "multi_goal_conflict": scenarios.multi_goal_conflict_scenario,
    "affective_persistence": scenarios.affective_persistence_scenario,
    "upgrade_stability": scenarios.upgrade_stability_scenario,
}


def build_default_engine(db_path: str = ":memory:") -> tuple[SimulationEngine, EventBus]:
    """Build a fully wired SAA engine with all default modules."""
    from saa.modules.embodiment.default import SimulatedEmbodiment
    from saa.modules.interoception.default import DefaultInteroception
    from saa.modules.homeostasis.default import DefaultHomeostasis
    from saa.modules.allostasis.default import DefaultAllostasis
    from saa.modules.self_model.default import DefaultSelfModel
    from saa.modules.memory.default import SQLiteMemorySystem
    from saa.modules.valuation.default import DefaultValuation
    from saa.modules.neuromodulation.default import DefaultNeuromodulation
    from saa.modules.social.default import DefaultSocial
    from saa.modules.action.default import DefaultActionSelection
    from saa.modules.observability.default import DefaultObservability

    event_bus = EventBus()
    registry = ModuleRegistry()
    persistence = PersistenceLayer(db_path)
    persistence.connect()

    registry.register("embodiment", SimulatedEmbodiment())
    registry.register("interoception", DefaultInteroception())
    registry.register("homeostasis", DefaultHomeostasis())
    registry.register("allostasis", DefaultAllostasis())
    registry.register("self_model", DefaultSelfModel())
    registry.register("memory", SQLiteMemorySystem())
    registry.register("valuation", DefaultValuation())
    registry.register("neuromodulation", DefaultNeuromodulation())
    registry.register("social", DefaultSocial())
    registry.register("action", DefaultActionSelection())
    registry.register("observability", DefaultObservability())

    engine = SimulationEngine(
        agent_id="saa_agent",
        registry=registry,
        event_bus=event_bus,
        persistence=persistence,
    )

    return engine, event_bus


def run_scenario(scenario_name: str, num_ticks: int = 50, seed: int = 42, output_path: str | None = None) -> None:
    """Run a named scenario and print results."""
    if scenario_name not in SCENARIOS:
        logger.error("Unknown scenario: %s. Available: %s", scenario_name, list(SCENARIOS.keys()))
        sys.exit(1)

    logger.info("Running scenario: %s for %d ticks", scenario_name, num_ticks)
    world = SCENARIOS[scenario_name](seed=seed)
    engine, event_bus = build_default_engine()
    engine.initialize_modules()

    results = []
    for i in range(num_ticks):
        env = world.step()
        engine.set_environment(env)
        context = engine.step()

        # Extract key metrics
        tick_data = {
            "tick": context.tick,
            "viability": context.homeostatic_error.get("viability", 0) if context.homeostatic_error else None,
            "action": context.action_result.get("selected_action", {}) if context.action_result else None,
            "energy": context.embodiment_state.get("energy", 0) if context.embodiment_state else None,
            "event_count": len(context.events),
            "environment": {
                "resources": env.available_resources,
                "hazard": env.hazard_level,
                "agents": env.social_agents,
            },
        }
        results.append(tick_data)

        if (i + 1) % 10 == 0:
            logger.info(
                "Tick %d: viability=%.2f energy=%.2f action=%s events=%d",
                tick_data["tick"],
                tick_data["viability"] or 0,
                tick_data["energy"] or 0,
                tick_data["action"].get("action_type", "?") if tick_data["action"] else "?",
                tick_data["event_count"],
            )

    # Summary
    logger.info("=== Scenario Complete: %s ===", scenario_name)
    logger.info("Total ticks: %d", num_ticks)
    logger.info("Total events: %d", sum(r["event_count"] for r in results))

    final = results[-1]
    logger.info("Final viability: %.2f", final["viability"] or 0)
    logger.info("Final energy: %.2f", final["energy"] or 0)

    if output_path:
        Path(output_path).write_text(json.dumps(results, indent=2, default=str))
        logger.info("Results written to %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Swan Affective Architecture — Simulation Runner")
    parser.add_argument("scenario", choices=list(SCENARIOS.keys()), help="Scenario to run")
    parser.add_argument("--ticks", type=int, default=50, help="Number of simulation ticks")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path")
    args = parser.parse_args()

    run_scenario(args.scenario, num_ticks=args.ticks, seed=args.seed, output_path=args.output)


if __name__ == "__main__":
    main()
