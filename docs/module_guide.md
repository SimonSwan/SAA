# Module Development Guide

## Adding a New Module

### 1. Define the Schema

Create `saa/schemas/your_module.py`:

```python
from pydantic import BaseModel, Field
from saa.interfaces.base import BaseConfig, BaseState

class YourModuleConfig(BaseConfig):
    some_parameter: float = 0.5

class YourModuleState(BaseState):
    module_name: str = "your_module"
    version: str = "0.1.0"
    some_value: float = 0.0
```

### 2. Define the Interface

Create `saa/interfaces/your_module.py`:

```python
from abc import abstractmethod
from saa.interfaces.base import BaseModule
from saa.core.types import ModuleOutput, TickContext

class YourModuleInterface(BaseModule):
    VERSION = "0.1.0"
    CAPABILITIES = ["your_capability"]
    DEPENDENCIES = ["embodiment"]  # list modules you read from

    @abstractmethod
    def your_custom_method(self) -> dict:
        ...
```

### 3. Implement the Module

Create `saa/modules/your_module/default.py`:

```python
from saa.interfaces.your_module import YourModuleInterface
from saa.core.types import Event, ModuleOutput, TickContext

class DefaultYourModule(YourModuleInterface):
    VERSION = "0.1.0"
    CAPABILITIES = ["your_capability"]
    DEPENDENCIES = ["embodiment"]

    def __init__(self):
        self._state = YourModuleState()
        self._config = YourModuleConfig()

    def initialize(self, config=None):
        if config:
            self._config = YourModuleConfig(**config)
        self._state = YourModuleState()

    def update(self, tick, context):
        # Read upstream data from context
        body = context.embodiment_state or {}
        energy = body.get("energy", 1.0)

        # Your logic here
        self._state.some_value = energy * self._config.some_parameter
        self._state.tick = tick

        events = []
        if self._state.some_value > 0.8:
            events.append(Event(
                tick=tick,
                source_module="your_module",
                event_type="your_event",
                data={"value": self._state.some_value},
            ))

        return ModuleOutput(
            module_name="your_module",
            tick=tick,
            state=self._state.model_dump(),
            events=events,
        )

    def get_state(self):
        return self._state.model_copy()

    def set_state(self, state):
        self._state = YourModuleState(**state.model_dump())

    def reset(self):
        self.initialize()

    def your_custom_method(self):
        return {"value": self._state.some_value}
```

### 4. Register It

```python
from saa.modules.your_module.default import DefaultYourModule

registry.register("your_module", DefaultYourModule())
```

### 5. Write Tests

Create `tests/unit/test_your_module.py` with tests for initialization, update, state persistence, and edge cases.

## Replacing an Existing Module

1. Implement the same interface (e.g., `EmbodimentInterface`)
2. Register with the same name: `registry.register("embodiment", YourNewEmbodiment())`
3. Ensure your state model is compatible or provide migration logic
4. Run the Swan Test Suite to verify compatibility

## Module Versioning

- Use semantic versioning: `MAJOR.MINOR.PATCH`
- MAJOR: Breaking interface changes
- MINOR: New capabilities, backward compatible
- PATCH: Bug fixes
- State migrations should handle version differences in `set_state()`

## Module Communication

Modules communicate in two ways:

1. **TickContext** (primary): Each module reads upstream outputs and writes its own
2. **EventBus** (secondary): Modules publish events for cross-cutting concerns

Avoid direct module-to-module dependencies. Read from context, not from other module instances.
