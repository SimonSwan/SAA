"""Swan agent adapter — wraps the full SAA engine as an AgentInterface."""

from __future__ import annotations

from typing import Any

from saa.core.engine import SimulationEngine
from saa.core.event_bus import EventBus
from saa.core.module_registry import ModuleRegistry
from saa.core.persistence import PersistenceLayer
from saa.core.types import EnvironmentState, Event, TickContext
from saa.testing.agents.base import AgentInterface


class SwanAgent(AgentInterface):
    """Wraps the full SAA architecture as a testable agent."""

    def __init__(self) -> None:
        self._engine: SimulationEngine | None = None
        self._event_bus: EventBus | None = None
        self._registry: ModuleRegistry | None = None
        self._pending_events: list[dict[str, Any]] = []

    def initialize(self, config: dict[str, Any] | None = None) -> None:
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

        self._event_bus = EventBus()
        self._registry = ModuleRegistry()
        persistence = PersistenceLayer(":memory:")
        persistence.connect()

        self._registry.register("embodiment", SimulatedEmbodiment())
        self._registry.register("interoception", DefaultInteroception())
        self._registry.register("homeostasis", DefaultHomeostasis())
        self._registry.register("allostasis", DefaultAllostasis())
        self._registry.register("self_model", DefaultSelfModel())
        self._registry.register("memory", SQLiteMemorySystem())
        self._registry.register("valuation", DefaultValuation())
        self._registry.register("neuromodulation", DefaultNeuromodulation())
        self._registry.register("social", DefaultSocial())
        self._registry.register("action", DefaultActionSelection())
        self._registry.register("observability", DefaultObservability())

        self._engine = SimulationEngine(
            agent_id="swan_agent",
            registry=self._registry,
            event_bus=self._event_bus,
            persistence=persistence,
        )

        module_configs = (config or {}).get("module_configs", {})
        self._engine.initialize_modules(module_configs)

    def step(self, environment: EnvironmentState) -> TickContext:
        assert self._engine is not None
        self._engine.set_environment(environment)

        # Inject pending events into the event bus before the tick
        for evt in self._pending_events:
            event = Event(
                tick=self._engine.tick + 1,
                source_module="scenario",
                event_type=evt["event_type"],
                data=evt.get("data", {}),
                severity=evt.get("severity", 0.5),
            )
            self._event_bus.publish(event)  # type: ignore[union-attr]
        self._pending_events.clear()

        return self._engine.step()

    def get_state(self) -> dict[str, Any]:
        assert self._engine is not None
        return self._engine.save_state()

    def set_state(self, state: dict[str, Any]) -> None:
        assert self._engine is not None
        self._engine.load_state(state)

    def get_module_versions(self) -> dict[str, str]:
        if self._registry is None:
            return {}
        versions = {}
        for name, module in self._registry.get_ordered_modules():
            versions[name] = module.VERSION
        return versions

    def inject_event(self, event_type: str, data: dict[str, Any]) -> None:
        self._pending_events.append({"event_type": event_type, "data": data})

    def reset(self) -> None:
        self.initialize()

    @property
    def agent_type(self) -> str:
        return "swan"
