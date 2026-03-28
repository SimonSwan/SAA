"""Shared fixtures for SAA tests."""

import pytest

from saa.core.engine import SimulationEngine
from saa.core.event_bus import EventBus
from saa.core.module_registry import ModuleRegistry
from saa.core.persistence import PersistenceLayer
from saa.core.types import EnvironmentState, TickContext


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def registry():
    return ModuleRegistry()


@pytest.fixture
def persistence():
    p = PersistenceLayer(":memory:")
    p.connect()
    yield p
    p.close()


@pytest.fixture
def engine(registry, event_bus, persistence):
    return SimulationEngine(
        agent_id="test_agent",
        registry=registry,
        event_bus=event_bus,
        persistence=persistence,
    )


@pytest.fixture
def default_environment():
    return EnvironmentState(
        available_resources=0.8,
        ambient_temperature=0.5,
        hazard_level=0.0,
        social_agents=["ally_1"],
        tick=0,
    )


@pytest.fixture
def default_context(default_environment):
    return TickContext(
        tick=1,
        dt=1.0,
        agent_id="test_agent",
        environment=default_environment,
    )


@pytest.fixture
def stressed_context(default_environment):
    """A context representing a stressed agent state."""
    env = default_environment.model_copy()
    env.hazard_level = 0.7
    env.available_resources = 0.2
    return TickContext(
        tick=1,
        dt=1.0,
        agent_id="test_agent",
        environment=env,
        embodiment_state={
            "energy": 0.2,
            "temperature": 0.7,
            "strain": 0.6,
            "latency_load": 0.5,
            "memory_integrity": 0.8,
            "damage": 0.5,
            "recovery_rate": 0.3,
            "resource_level": 0.2,
        },
        interoceptive_vector={
            "channels": {
                "energy_deficit": 0.8,
                "thermal_stress": 0.4,
                "strain_load": 0.6,
                "damage_level": 0.5,
                "memory_risk": 0.2,
                "resource_scarcity": 0.8,
            }
        },
        homeostatic_error={
            "errors": {
                "energy_deficit": 0.5,
                "thermal_stress": 0.2,
                "strain_load": 0.3,
                "damage_level": 0.4,
                "memory_risk": 0.1,
                "resource_scarcity": 0.5,
            },
            "viability": 0.4,
            "regulation_priorities": ["energy_deficit", "resource_scarcity", "damage_level"],
        },
    )


def build_full_engine():
    """Build a complete engine with all default modules registered.

    Returns (engine, registry, event_bus, persistence).
    """
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

    event_bus = EventBus()
    registry = ModuleRegistry()
    persistence = PersistenceLayer(":memory:")
    persistence.connect()

    registry.register("embodiment", SimulatedEmbodiment())
    registry.register("interoception", DefaultInteroception())
    registry.register("homeostasis", DefaultHomeostasis())
    registry.register("allostasis", DefaultAllostasis())
    registry.register("self_model", DefaultSelfModel())
    registry.register("memory", SQLiteMemorySystem())
    registry.register("valuation", DefaultValuation())
    registry.register("neuromodulation", DefaultNeuromodulation())
    registry.register("social", DefaultSocial())
    registry.register("action", DefaultActionSelection())
    registry.register("observability", DefaultObservability())

    engine = SimulationEngine(
        agent_id="test_agent",
        registry=registry,
        event_bus=event_bus,
        persistence=persistence,
    )

    return engine, registry, event_bus, persistence
