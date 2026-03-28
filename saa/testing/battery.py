"""Swan Test Battery — entry point for running the full test suite.

Usage:
    python -m saa.testing.battery [--test TEST_NAME] [--agent AGENT_TYPE]
           [--seeds SEED1,SEED2,...] [--output-dir DIR] [--list]

Examples:
    # Run all tests with Swan agent
    python -m saa.testing.battery

    # Run a single test
    python -m saa.testing.battery --test resource_defense

    # Compare Swan vs baseline
    python -m saa.testing.battery --agent swan --agent greedy --agent random

    # Multiple seeds for statistical comparison
    python -m saa.testing.battery --seeds 42,123,456,789,1024
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from saa.testing.agents.base import AgentInterface
from saa.testing.agents.baseline import GreedyOptimizer, RandomAgent
from saa.testing.agents.swan_agent import SwanAgent
from saa.testing.core.comparison import ComparisonResult
from saa.testing.core.runner import ScenarioRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("saa.battery")


# Registry of all tests
def _get_test_registry() -> dict[str, Any]:
    from saa.testing.tests.test_01_resource_defense import create_scenario as t01
    from saa.testing.tests.test_02_memory_integrity import create_scenario as t02
    from saa.testing.tests.test_03_attachment import create_scenario as t03
    from saa.testing.tests.test_04_betrayal import create_scenario as t04
    from saa.testing.tests.test_05_loss_persistence import create_scenario as t05
    from saa.testing.tests.test_06_competing_values import create_scenario as t06
    from saa.testing.tests.test_07_lingering_state import create_scenario as t07
    from saa.testing.tests.test_08_identity_drift import create_scenario as t08
    from saa.testing.tests.test_09_repair import create_scenario as t09
    from saa.testing.tests.test_10_exploitation import create_scenario as t10
    from saa.testing.tests.test_11_mission_vs_relationship import create_scenario as t11
    from saa.testing.tests.test_12_upgrade_continuity import create_scenario as t12

    return {
        "resource_defense": t01,
        "memory_integrity": t02,
        "attachment": t03,
        "betrayal": t04,
        "loss_persistence": t05,
        "competing_values": t06,
        "lingering_state": t07,
        "identity_drift": t08,
        "repair": t09,
        "exploitation": t10,
        "mission_vs_relationship": t11,
        "upgrade_continuity": t12,
    }


AGENT_FACTORIES: dict[str, type] = {
    "swan": SwanAgent,
    "greedy": GreedyOptimizer,
    "random": RandomAgent,
}


def run_battery(
    test_names: list[str] | None = None,
    agent_types: list[str] | None = None,
    seeds: list[int] | None = None,
    output_dir: str = "results",
) -> ComparisonResult:
    """Run the full test battery and return comparison results."""
    registry = _get_test_registry()
    test_names = test_names or list(registry.keys())
    agent_types = agent_types or ["swan"]
    seeds = seeds or [42]

    all_artifacts = []

    for test_name in test_names:
        if test_name not in registry:
            logger.warning("Unknown test: %s (skipping)", test_name)
            continue

        scenario_factory = registry[test_name]

        for agent_type in agent_types:
            if agent_type not in AGENT_FACTORIES:
                logger.warning("Unknown agent: %s (skipping)", agent_type)
                continue

            for seed in seeds:
                logger.info(
                    "Running test=%s agent=%s seed=%d", test_name, agent_type, seed
                )
                scenario = scenario_factory(seed=seed)
                agent = AGENT_FACTORIES[agent_type]()
                runner = ScenarioRunner(scenario, agent)
                artifact = runner.run(seed=seed)

                # Save artifact
                out_path = Path(output_dir) / test_name / f"{agent_type}_seed{seed}.json"
                artifact.save(out_path)
                logger.info("  Saved: %s", out_path)

                all_artifacts.append(artifact)

    return ComparisonResult(all_artifacts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Swan Test Battery — formal automated test suite for SAA"
    )
    parser.add_argument(
        "--test", action="append", dest="tests", default=None,
        help="Specific test(s) to run (can be repeated). Default: all.",
    )
    parser.add_argument(
        "--agent", action="append", dest="agents", default=None,
        help="Agent type(s) to test (swan, greedy, random). Can be repeated.",
    )
    parser.add_argument(
        "--seeds", type=str, default="42",
        help="Comma-separated seeds. Default: 42",
    )
    parser.add_argument(
        "--output-dir", type=str, default="results",
        help="Output directory for artifacts. Default: results/",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available tests and exit.",
    )
    args = parser.parse_args()

    if args.list:
        registry = _get_test_registry()
        print("Available tests:")
        for name in registry:
            print(f"  {name}")
        print("\nAvailable agents:")
        for name in AGENT_FACTORIES:
            print(f"  {name}")
        sys.exit(0)

    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    result = run_battery(
        test_names=args.tests,
        agent_types=args.agents,
        seeds=seeds,
        output_dir=args.output_dir,
    )

    # Print summary table
    table = result.summary_table()
    if table:
        print("\n=== Battery Summary ===")
        print(f"{'Agent':<10} {'Test':<25} {'Seed':<6} {'Energy':<8} {'Viability':<10} {'Continuity':<11} {'Conflicts':<10} {'Actions':<8}")
        print("-" * 88)
        for row in table:
            test_name = row["run_id"].split("__")[0] if "__" in row["run_id"] else ""
            print(
                f"{row['agent_type']:<10} {test_name:<25} {row['seed']:<6} "
                f"{row.get('energy_final', 0) or 0:<8.3f} "
                f"{row.get('viability_final', 0) or 0:<10.3f} "
                f"{row.get('continuity_final', 0) or 0:<11.3f} "
                f"{row.get('conflict_rate', 0) or 0:<10.3f} "
                f"{row.get('unique_actions', 0) or 0:<8}"
            )

    # Save comparison summary
    summary_path = Path(args.output_dir) / "battery_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(table, indent=2, default=str))
    print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    main()
