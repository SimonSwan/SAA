# Swan Test Battery — Run Guide

## Quick Start

```bash
# Run full battery with Swan agent
python -m saa.testing.battery

# List available tests
python -m saa.testing.battery --list

# Run a single test
python -m saa.testing.battery --test resource_defense

# Compare agents
python -m saa.testing.battery --agent swan --agent greedy --agent random

# Multiple seeds
python -m saa.testing.battery --seeds 42,123,456,789,1024

# Custom output directory
python -m saa.testing.battery --output-dir my_results/
```

## Output Structure

```
results/
  resource_defense/
    swan_seed42.json          # Full run artifact
    greedy_seed42.json
    random_seed42.json
  attachment/
    swan_seed42.json
    ...
  battery_summary.json        # Summary table
```

## Artifact Format

Each `.json` artifact contains:

```json
{
  "metadata": {
    "run_id": "resource_defense__swan__seed42__20260328_...",
    "test_name": "resource_defense",
    "agent_type": "swan",
    "seed": 42,
    "num_ticks": 120,
    "scenario_config": {...},
    "phases": [...],
    "module_versions": {...}
  },
  "tick_metrics": [...],       // Per-tick measurements
  "event_log": [...],          // All events emitted
  "scenario_events": [...],    // Scripted scenario events
  "phase_summaries": {...},    // Descriptive stats per phase
  "descriptive_stats": {...},  // Run-level summaries
  "final_agent_state": {...}   // Full agent state at end
}
```

## Replay

```python
from saa.testing.core.replay import ReplayViewer, export_series_csv

# Load and inspect
viewer = ReplayViewer.from_file("results/resource_defense/swan_seed42.json")
print(viewer.print_summary())

# Extract time series
energy = viewer.get_series("energy")
stress = viewer.get_series("modulators")  # dict per tick

# Track a relationship
history = viewer.get_relationship_history("friend")

# Export for external analysis
export_series_csv(
    viewer.artifact,
    fields=["energy", "viability", "continuity_score", "selected_action"],
    output_path="export/energy_trace.csv",
)
```

## Comparison

```python
from saa.testing.core.comparison import ComparisonResult
from saa.testing.core.artifacts import RunArtifact

# Load multiple artifacts
artifacts = [
    RunArtifact.load("results/attachment/swan_seed42.json"),
    RunArtifact.load("results/attachment/greedy_seed42.json"),
]
comp = ComparisonResult(artifacts)

# Compare metrics
comp.compare_metric("energy_final")
comp.compare_action_distributions()
comp.compare_phase_metric("interaction", "means.energy")

# Summary table
for row in comp.summary_table():
    print(row)
```

## Programmatic Usage

```python
from saa.testing.battery import run_battery

result = run_battery(
    test_names=["resource_defense", "attachment"],
    agent_types=["swan", "greedy"],
    seeds=[42, 123],
    output_dir="my_experiment",
)

# result is a ComparisonResult with all artifacts
table = result.summary_table()
```

## Seed Control

All scenarios and agents accept seeds for reproducibility. Same seed = same environment evolution, same random agent choices, same scenario events.

## Agent Backends

| Agent | Description |
|-------|-------------|
| `swan` | Full SAA architecture with all 11 modules |
| `greedy` | Simple reactive optimizer (no memory, no social, no modulation) |
| `random` | Uniform random action selection |

Custom agents: implement `AgentInterface` from `saa.testing.agents.base`.
