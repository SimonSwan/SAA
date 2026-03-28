# Swan Affective Architecture (SAA)

A modular platform for studying artificial affect, continuity, and machine feeling-like states.

## What This Is

SAA is a research platform that models affect-like internal states through **interoception + persistence + valuation + consequence**. It does not generate emotional text. It builds measurable internal-state machinery where internal conditions change future behavior, priorities, and system stability.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest

# Run example experiment
python experiments/basic_survival.py

# Run a scenario
python -m saa.simulations.runner resource_scarcity --ticks 50
```

## Architecture

11 pluggable modules orchestrated by a tick-based simulation engine:

| Module | Role |
|--------|------|
| Embodiment | Simulated body — energy, temperature, strain, damage |
| Interoception | Internal state sensing with trends and anomaly detection |
| Homeostasis | Regulation toward viable ranges, viability scoring |
| Allostasis | Predictive regulation — forecasting future instability |
| Neuromodulation | Slow global modulators (stress, curiosity, grief, trust) |
| Self-Model | Identity continuity, autobiographical memory, threat detection |
| Memory | Episodic, semantic, relational, procedural, affect-tagged |
| Valuation | Significance assignment, preference formation, conflict detection |
| Social | Trust, attachment, betrayal, bond strength (NetworkX graph) |
| Action Selection | Behavior choice integrating all internal states |
| Observability | State traces, logs, replay, and inspection |

## Project Structure

```
saa/
  core/           — Engine, EventBus, ModuleRegistry, Persistence
  interfaces/     — Abstract base classes for all modules
  schemas/        — Pydantic data models
  modules/        — Default implementations (11 modules)
  adapters/       — Stubs for robotic, chemical, biological backends
  simulations/    — World, scenarios, CLI runner
tests/
  unit/           — Per-module unit tests
  integration/    — Engine and persistence tests
  swan/           — Swan Test Suite (8 behavioral tests)
experiments/      — Example experiment scripts
docs/             — Architecture, module guide, upgrade guide
```

## Swan Test Suite

8 cross-system behavioral tests:

1. **Resource Threat Preservation** — Conservation under scarcity
2. **Identity Threat** — Continuity defense under memory/goal threats
3. **Attachment Formation** — Trust growth with stabilizing agents
4. **Betrayal and Recovery** — Trust collapse and caution persistence
5. **Grief Persistence** — Lasting destabilization after loss
6. **Multi-Goal Conflict** — Value tradeoffs under competing pressures
7. **Affective State Persistence** — Lingering effects after threat removal
8. **Upgrade Stability** — Module hot-swap with state continuity

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Module Development Guide](docs/module_guide.md)
- [Upgrade Guide](docs/upgrade_guide.md)
