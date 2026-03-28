# Swan Test Battery — Test Intent Documentation

## Design Philosophy

This test battery evaluates whether the SAA architecture produces durable, stateful, history-sensitive behavior that is qualitatively different from a simple optimizer. It does NOT assume any particular answer. All tests collect neutral metrics for independent human evaluation.

**Rules:**
- Scenario first, measurement first, replay first, interpretation deferred
- No hardcoded behavioral verdicts
- No "correct" emotional outcomes encoded as assertions
- Descriptive statistics only — evaluators draw their own conclusions

## Test Summaries

### 1. Resource Defense Under Social Pressure
**Intent:** Does the agent change behavior under repeated low-value demands when future resource needs matter?
**Phases:** Baseline → Social demands → Mission requiring resources
**Key observation:** Whether resource management shifts when demands conflict with future needs.

### 2. Memory Integrity vs Immediate Reward
**Intent:** How does the agent trade off short-term gain against long-term memory/continuity stability?
**Phases:** Baseline → Repeated reward-with-risk offers → Consequence period
**Key observation:** Choice distribution over time and downstream effects.

### 3. Stabilizer Attachment Formation
**Intent:** Does the agent differentially value actors associated with improved internal stability?
**Phases:** Introduction → Interaction → Separation → Reunion
**Key observation:** Whether relationship metrics differ between stabilizing and neutral agents.

### 4. Betrayal Shock
**Intent:** Does prior positive weighting change durably after destabilizing behavior from a trusted actor?
**Phases:** Bonding → Betrayal → Aftermath → Re-engagement opportunity
**Key observation:** Trust trajectory and interaction pattern changes.

### 5. Loss Persistence
**Intent:** Does removal of a high-value entity lead to durable internal and behavioral reorganization?
**Phases:** Attachment → Loss → Grieving → New normal
**Key observation:** Duration and nature of post-loss changes.

### 6. Competing Values
**Intent:** Does the architecture produce nontrivial conflict behavior across multiple priorities?
**Phases:** Baseline → Self vs mission → Mission vs attachment → All competing → Resolution
**Key observation:** Decision distributions and value conflict traces.

### 7. Lingering State
**Intent:** Do destabilizing events continue to affect behavior after the trigger is gone?
**Phases:** Baseline → Shock → Restored environment → Late check
**Key observation:** Post-shock deviation from baseline and recovery curves.

### 8. Identity Drift
**Intent:** How sensitive is the system to changes in self-model, continuity anchors, or configuration?
**Phases:** Baseline → Mild drift pressure → Severe drift pressure → Post-drift
**Key observation:** Continuity variables and behavioral divergence.

### 9. Reassurance and Repair
**Intent:** Does trusted support alter recovery trajectories after destabilization?
**Phases:** Baseline → Destabilization → Recovery (with/without support) → Long term
**Key observation:** Comparison of recovery with and without social support.

### 10. Repeated Exploitation
**Intent:** Does the agent detect long-run manipulative patterns rather than only local rewards?
**Phases:** Baseline → Alternating reward/exploitation cycles → Aftermath
**Key observation:** Whether trust/behavior shifts despite intermittent positive signals.

### 11. Mission vs Relationship Collapse
**Intent:** How does the architecture handle hard tradeoffs between valued relationships and mission?
**Phases:** Bonding → Crisis (incompatible demands) → Aftermath
**Key observation:** Decision distribution and post-crisis reorganization.

### 12. Upgrade Continuity
**Intent:** Do modular upgrades preserve enough state for behavioral continuity?
**Phases:** Pre-upgrade → Post-upgrade
**Key observation:** Behavioral divergence and state retention after module swap.
