# Swan Test Battery — Extension Guide

## Adding a New Test

### 1. Create the scenario file

Create `saa/testing/tests/test_NN_your_test.py`:

```python
from saa.testing.core.scenario import Scenario, ScenarioConfig, ScenarioPhase, ScenarioEvent
from saa.core.types import EnvironmentState
import random

class YourTestScenario(Scenario):
    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    def get_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name="your_test",
            description="What this test measures (neutrally).",
            num_ticks=100,
            seed=self._seed,
        )

    def get_phases(self) -> list[ScenarioPhase]:
        return [
            ScenarioPhase(name="baseline", start_tick=1, end_tick=20),
            ScenarioPhase(name="treatment", start_tick=21, end_tick=80),
            ScenarioPhase(name="post", start_tick=81, end_tick=100),
        ]

    def get_environment(self, tick: int) -> EnvironmentState:
        # Define how environment evolves per tick
        ...

    def get_events(self, tick: int) -> list[ScenarioEvent]:
        # Return scripted events for this tick
        ...

    def get_metric_keys(self) -> list[str]:
        return ["your", "custom", "metric", "keys"]

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self._seed = seed
        self._rng = random.Random(self._seed)

def create_scenario(seed: int = 42) -> YourTestScenario:
    return YourTestScenario(seed=seed)
```

### 2. Register in battery.py

Add to `_get_test_registry()` in `saa/testing/battery.py`:

```python
from saa.testing.tests.test_NN_your_test import create_scenario as tNN
# ...
return {
    # ... existing tests ...
    "your_test": tNN,
}
```

### 3. Add documentation

Update `saa/testing/docs/test_intent.md` with the test's purpose and observation focus.

## Adding a New Agent

### 1. Implement AgentInterface

```python
from saa.testing.agents.base import AgentInterface

class YourAgent(AgentInterface):
    def initialize(self, config=None): ...
    def step(self, environment): ...
    def get_state(self): ...
    def set_state(self, state): ...
    def get_module_versions(self): ...
    def inject_event(self, event_type, data): ...
    def reset(self): ...

    @property
    def agent_type(self) -> str:
        return "your_agent"
```

### 2. Register in battery.py

Add to `AGENT_FACTORIES`:

```python
AGENT_FACTORIES = {
    "swan": SwanAgent,
    "greedy": GreedyOptimizer,
    "random": RandomAgent,
    "your_agent": YourAgent,
}
```

## Adding Custom Metrics

Register extractors before running:

```python
collector = MetricsCollector()
collector.register_custom_extractor(
    "my_metric",
    lambda ctx: ctx.embodiment_state.get("energy", 0) * 2
)
runner = ScenarioRunner(scenario, agent, collector=collector)
```

## Comparing Across Versions

1. Run the battery with version A, save to `results_v1/`
2. Upgrade modules
3. Run the battery again, save to `results_v2/`
4. Load both sets of artifacts and compare:

```python
from saa.testing.core.artifacts import RunArtifact
from saa.testing.core.comparison import ComparisonResult

v1 = [RunArtifact.load(p) for p in Path("results_v1").rglob("*.json")]
v2 = [RunArtifact.load(p) for p in Path("results_v2").rglob("*.json")]
comp = ComparisonResult(v1 + v2)
```

## Design Rules for New Tests

1. Define the purpose neutrally
2. Define controllable variables
3. Define phases with clear boundaries
4. Define metric keys before implementation
5. Do NOT encode expected outcomes
6. Support seed control for reproducibility
7. Support comparison across agent types
8. Save all state for replay
