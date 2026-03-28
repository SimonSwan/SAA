"""SimulationEngine — tick-based orchestration of all SAA modules."""

from __future__ import annotations

import logging
from typing import Any

from saa.core.event_bus import EventBus
from saa.core.module_registry import ModuleRegistry
from saa.core.persistence import PersistenceLayer
from saa.core.types import EnvironmentState, TickContext

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Runs the SAA tick loop, orchestrating modules in canonical order.

    Each tick:
    1. Build a fresh TickContext with current environment state.
    2. Execute each module in order, accumulating outputs into the context.
    3. Collect events and route them through the EventBus.
    4. Optionally persist state snapshots.
    """

    def __init__(
        self,
        agent_id: str = "agent_0",
        registry: ModuleRegistry | None = None,
        event_bus: EventBus | None = None,
        persistence: PersistenceLayer | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.registry = registry or ModuleRegistry()
        self.event_bus = event_bus or EventBus()
        self.persistence = persistence
        self._tick: int = 0
        self._environment = EnvironmentState()
        self._running: bool = False

    @property
    def tick(self) -> int:
        return self._tick

    def set_environment(self, env: EnvironmentState) -> None:
        self._environment = env

    def initialize_modules(self, configs: dict[str, dict[str, Any]] | None = None) -> None:
        """Initialize all registered modules with optional per-module configs."""
        configs = configs or {}
        errors = self.registry.validate_dependencies()
        if errors:
            for err in errors:
                logger.warning("Dependency issue: %s", err)

        for name, module in self.registry.get_ordered_modules():
            config = configs.get(name)
            module.initialize(config)
            logger.info("Initialized module: %s (v%s)", name, module.VERSION)

    def step(self, dt: float = 1.0) -> TickContext:
        """Execute a single simulation tick."""
        self._tick += 1
        self._environment.tick = self._tick

        context = TickContext(
            tick=self._tick,
            dt=dt,
            agent_id=self.agent_id,
            environment=self._environment,
        )

        # Module-to-context-field mapping
        context_fields = {
            "embodiment": "embodiment_state",
            "interoception": "interoceptive_vector",
            "homeostasis": "homeostatic_error",
            "allostasis": "allostatic_forecast",
            "neuromodulation": "modulator_state",
            "self_model": "self_model_state",
            "memory": "memory_context",
            "valuation": "valuation_map",
            "social": "social_state",
            "action": "action_result",
        }

        for name, module in self.registry.get_ordered_modules():
            try:
                output = module.update(self._tick, context)

                # Inject module output into context for downstream modules
                if name in context_fields:
                    setattr(context, context_fields[name], output.state)

                # Route events through the bus
                for event in output.events:
                    self.event_bus.publish(event)
                    context.events.append(event)

            except Exception:
                logger.exception("Error in module '%s' at tick %d", name, self._tick)

        # Persist state snapshot if persistence is configured
        if self.persistence is not None:
            self._persist_snapshot(context)

        return context

    def run(self, num_ticks: int, dt: float = 1.0) -> list[TickContext]:
        """Run multiple ticks and return all contexts."""
        self._running = True
        contexts: list[TickContext] = []
        for _ in range(num_ticks):
            if not self._running:
                break
            ctx = self.step(dt)
            contexts.append(ctx)
        self._running = False
        return contexts

    def stop(self) -> None:
        self._running = False

    def _persist_snapshot(self, context: TickContext) -> None:
        """Save a full agent state snapshot to the persistence layer."""
        if self.persistence is None:
            return
        state: dict[str, Any] = {}
        for name, module in self.registry.get_ordered_modules():
            try:
                module_state = module.get_state()
                state[name] = module_state.model_dump()
            except Exception:
                logger.exception("Failed to get state from module '%s'", name)
        self.persistence.save_agent_state(self.agent_id, self._tick, state)

    def save_state(self) -> dict[str, Any]:
        """Return the full serialized agent state."""
        state: dict[str, Any] = {}
        for name, module in self.registry.get_ordered_modules():
            state[name] = module.get_state().model_dump()
        return state

    def load_state(self, state: dict[str, Any]) -> None:
        """Restore all modules from a previously saved state dict."""
        for name, module in self.registry.get_ordered_modules():
            if name in state:
                module_state_cls = type(module.get_state())
                restored = module_state_cls(**state[name])
                module.set_state(restored)
