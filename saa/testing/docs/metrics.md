# Swan Test Battery — Metrics Reference

## Per-Tick Metrics (Collected Every Tick)

### Embodiment
| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| energy | float | 0-1 | Current energy level |
| temperature | float | 0-1 | Body temperature |
| strain | float | 0-1 | Mechanical/computational strain |
| damage | float | 0-1 | Accumulated damage |
| memory_integrity | float | 0-1 | Memory system integrity |
| resource_level | float | 0-1 | Available resources |

### Homeostasis
| Metric | Type | Description |
|--------|------|-------------|
| viability | float | Overall viability score (0-1) |
| homeostatic_errors | dict | Per-channel error magnitudes |
| regulation_priorities | list | Ordered regulation priorities |

### Neuromodulation
| Metric | Type | Description |
|--------|------|-------------|
| modulators.reward_drive | float | Reward/motivation level |
| modulators.stress_load | float | Accumulated stress |
| modulators.trust_level | float | Global trust baseline |
| modulators.baseline_stability | float | System stability baseline |
| modulators.damage_salience | float | Attention to damage |
| modulators.curiosity_drive | float | Exploration motivation |
| modulators.grief_persistence | float | Grief/loss signal |
| modulators.social_dependency | float | Social need level |

### Self-Model
| Metric | Type | Description |
|--------|------|-------------|
| continuity_score | float | Identity continuity (0-1) |
| identity_anchors | list | Core identity elements |
| goal_stack_size | int | Number of active goals |

### Social
| Metric | Type | Description |
|--------|------|-------------|
| relationships | dict | Per-agent relationship data |
| attachment_risk | float | Risk of attachment loss |
| total_bond_strength | float | Sum of all bond strengths |

### Action
| Metric | Type | Description |
|--------|------|-------------|
| selected_action | str | Chosen action this tick |
| action_score | float | Confidence in selection |
| action_conflict | bool | Whether top actions were close |
| action_candidates | list | All scored candidates |

### Valuation
| Metric | Type | Description |
|--------|------|-------------|
| values | dict | Current value dimension weights |
| value_conflicts | list | Active value conflicts |

## Derived Metrics (Computed Per Phase)

| Metric | Computation |
|--------|-------------|
| action_distribution | Count of each action type in phase |
| mean_energy | Average energy over phase |
| mean_viability | Average viability over phase |
| mean_stress | Average stress_load modulator |
| conflict_rate | Fraction of ticks with action conflict |
| event_counts | Count of each event type |
| modulator_means | Per-modulator averages |
| value_means | Per-value-dimension averages |

## Run-Level Descriptive Statistics

| Stat | Description |
|------|-------------|
| energy_mean/min/max/final | Energy trajectory summary |
| viability_mean/min/final | Viability trajectory summary |
| continuity_mean/min/final | Continuity trajectory summary |
| total_events | Total events emitted |
| conflict_rate | Overall action conflict rate |
| unique_actions | Number of distinct action types used |
| action_types_used | List of action types selected |

## Custom Metrics

Tests can register custom metric extractors for scenario-specific measurements. These appear in `TickMetrics.custom`.
