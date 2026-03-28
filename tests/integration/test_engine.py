"""Integration tests for the SimulationEngine."""

import pytest

from saa.core.engine import SimulationEngine
from saa.core.event_bus import EventBus
from saa.core.module_registry import ModuleRegistry
from saa.core.persistence import PersistenceLayer
from saa.core.types import EnvironmentState
from tests.conftest import build_full_engine


class TestEngineIntegration:
    """Test the full engine with all modules wired together."""

    def test_engine_boots_and_runs(self):
        engine, registry, bus, persistence = build_full_engine()
        engine.initialize_modules()
        contexts = engine.run(10)

        assert len(contexts) == 10
        assert contexts[-1].tick == 10

    def test_all_context_fields_populated(self):
        engine, _, _, _ = build_full_engine()
        engine.initialize_modules()
        contexts = engine.run(3)
        last = contexts[-1]

        assert last.embodiment_state is not None
        assert last.interoceptive_vector is not None
        assert last.homeostatic_error is not None
        assert last.allostatic_forecast is not None
        assert last.modulator_state is not None
        assert last.self_model_state is not None
        assert last.memory_context is not None
        assert last.valuation_map is not None
        assert last.social_state is not None
        assert last.action_result is not None

    def test_events_flow_through_bus(self):
        engine, _, bus, _ = build_full_engine()
        engine.initialize_modules()
        engine.run(5)

        assert len(bus.history) > 0

    def test_environment_affects_agent(self):
        engine, _, bus, _ = build_full_engine()
        engine.initialize_modules()

        # Normal environment
        engine.set_environment(EnvironmentState(
            available_resources=1.0, hazard_level=0.0, ambient_temperature=0.5
        ))
        normal_ctx = engine.step()

        # Harsh environment for many ticks
        for _ in range(20):
            engine.set_environment(EnvironmentState(
                available_resources=0.1, hazard_level=0.8, ambient_temperature=0.9
            ))
            harsh_ctx = engine.step()

        # Agent should be worse off
        normal_energy = normal_ctx.embodiment_state.get("energy", 1.0)
        harsh_energy = harsh_ctx.embodiment_state.get("energy", 1.0)
        assert harsh_energy < normal_energy

    def test_state_save_and_load(self):
        engine, _, _, _ = build_full_engine()
        engine.initialize_modules()
        engine.run(10)

        # Save state
        saved = engine.save_state()
        assert "embodiment" in saved
        assert "homeostasis" in saved

        # Create a new engine and restore
        engine2, _, _, _ = build_full_engine()
        engine2.initialize_modules()
        engine2.load_state(saved)

        # States should match
        state1 = engine.save_state()
        state2 = engine2.save_state()
        assert state1["embodiment"]["energy"] == state2["embodiment"]["energy"]

    def test_module_execution_order(self):
        """Verify modules execute in canonical order."""
        engine, registry, _, _ = build_full_engine()
        engine.initialize_modules()

        ordered = registry.get_ordered_modules()
        names = [name for name, _ in ordered]

        # Embodiment must come before interoception
        assert names.index("embodiment") < names.index("interoception")
        # Interoception before homeostasis
        assert names.index("interoception") < names.index("homeostasis")
        # Homeostasis before allostasis
        assert names.index("homeostasis") < names.index("allostasis")
        # Action should be near the end
        assert names.index("action") > names.index("valuation")

    def test_long_run_stability(self):
        """Run for many ticks without crashes."""
        engine, _, _, _ = build_full_engine()
        engine.initialize_modules()
        contexts = engine.run(100)

        assert len(contexts) == 100
        # Viability should still be defined
        last = contexts[-1]
        if last.homeostatic_error:
            viability = last.homeostatic_error.get("viability")
            assert viability is not None
            assert 0.0 <= viability <= 1.0
