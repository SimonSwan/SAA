# Swan Affective Architecture — System Architecture

## Overview

SAA is a modular research platform for studying artificial affect, continuity, and machine feeling-like states. It models affect as **interoception + persistence + valuation + consequence** — not as emotional text labels.

The system is built around a tick-based simulation engine that orchestrates 11 pluggable modules. Each tick, the engine executes modules in a fixed order, building up a shared context that downstream modules can read.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SimulationEngine (tick loop)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─��──────────┐  │
│  │Embodiment│→ │Intero-   │→ │Homeo-    │→ │Allostasis  │  │
��  │  Layer   │  │ception   │  │stasis    │  │(Predictive)│  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│       ↓              ↓             ↓              ↓         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Memory  │← │Self-Model│← │Valuation │← │Neuro-      │  │
│  │  System  │  │Continuity│  │  Layer   │  │modulation  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│       ↓              ↓             ↓              ↓         │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────────┐ │
│  │  Social  │→ │  Action  │→ │  Observability & Logging  │ │
│  │Attachment│  │Selection │  │                           │ │
│  └──────────┘  └──────────┘  └───────────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  EventBus  |  ModuleRegistry  |  Persistence (SQLite)  ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Tick Execution Order

1. **Embodiment** — Updates body state (energy, temperature, strain, damage) based on environment and prior actions
2. **Interoception** — Senses internal state, produces normalized interoceptive vector with trend analysis
3. **Homeostasis** — Computes regulation error against setpoints, generates viability score
4. **Allostasis** — Forecasts future instability using trend extrapolation
5. **Neuromodulation** — Updates slow global modulators (stress, curiosity, grief, etc.)
6. **Self-Model** — Updates identity representation, continuity score, and autobiographical memory
7. **Memory** — Encodes current episode, retrieves relevant memories, applies decay
8. **Valuation** — Assigns significance to states/entities/goals, detects value conflicts
9. **Social** — Updates relationship graph, trust, attachment, bond strengths
10. **Action Selection** — Integrates all inputs to choose behavior
11. **Observability** — Logs full state snapshot for inspection and replay

## Core Infrastructure

### EventBus
Pub/sub system for cross-module communication. Modules publish events (e.g., "critical_energy_low", "trust_broken") and subscribe to event types. All events are logged for replay.

### ModuleRegistry
Plugin management system. Modules register by name and declare VERSION, CAPABILITIES, and DEPENDENCIES. The registry validates dependencies and provides ordered iteration.

### PersistenceLayer
SQLite-backed storage for agent state snapshots, episodic memory, and key-value configuration. Supports save/load/resume across sessions.

### TickContext
The shared context object built incrementally during each tick. Earlier modules populate fields that later modules read. All fields are optional dictionaries until the responsible module runs.

## Module Pattern

Every module follows the same pattern:

| Layer | Location | Purpose |
|-------|----------|---------|
| Schema | `saa/schemas/<module>.py` | Pydantic models for config, state, I/O |
| Interface | `saa/interfaces/<module>.py` | ABC defining the contract |
| Implementation | `saa/modules/<module>/default.py` | Default implementation |

Each module declares:
- `VERSION` — semantic version string
- `CAPABILITIES` — list of capability flags
- `DEPENDENCIES` — list of required module names

## Data Flow

Data flows through the TickContext, which is built incrementally:

```
Environment → Embodiment.update() → context.embodiment_state
                                         ↓
              Interoception.update() → context.interoceptive_vector
                                         ↓
              Homeostasis.update() → context.homeostatic_error
                                         ↓
              ... each module reads upstream, writes its output ...
                                         ↓
              ActionSelection.update() → context.action_result
                                         ↓
              Observability.update() → [logged snapshot]
```

## Key Design Principles

1. **Affect emerges from regulation** — not from labels or sentiment
2. **Internal state has consequences** — states change future behavior, not just text
3. **Strict separation** — sensing, regulation, valuation, continuity, and behavior are distinct
4. **Everything is inspectable** — full state traces, event logs, replayable experiments
5. **Pluggable architecture** — any module can be replaced without rewriting the system
6. **Future-proof** — abstraction layers for robotic, chemical, and biological backends
