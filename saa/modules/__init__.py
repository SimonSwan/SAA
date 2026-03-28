"""SAA modules — the functional building blocks of the Self-Aware Agent architecture.

Each sub-package implements one layer of the SAA processing pipeline.
Modules are executed in a fixed order each tick, progressively enriching
the shared TickContext so that downstream modules can build on upstream
outputs.

Execution order (foundation modules):
    1. embodiment   — simulated body state
    2. interoception — internal-signal aggregation
    3. homeostasis   — setpoint regulation and viability
"""
