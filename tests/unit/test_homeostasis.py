"""Unit tests for the DefaultHomeostasis module."""

import pytest

from saa.core.types import EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.homeostasis.default import DefaultHomeostasis


@pytest.fixture
def module():
    m = DefaultHomeostasis()
    m.initialize()
    return m


def _ctx(tick=1, interoceptive_vector=None):
    return TickContext(
        tick=tick,
        dt=1.0,
        agent_id="test",
        environment=EnvironmentState(tick=tick),
        interoceptive_vector=interoceptive_vector,
    )


class TestHomeostasisInitialization:
    def test_initialization(self, module):
        """Starts with viability 1.0."""
        state = module.get_state()
        assert state.viability == 1.0
        assert state.errors == {}
        assert state.regulation_priorities == []


class TestHomeostasisErrorComputation:
    def test_error_computation(self, module):
        """Errors computed from interoceptive vector."""
        intero = {
            "energy_deficit": 0.5,    # setpoint high=0.3, so error=0.2
            "thermal_stress": 0.1,    # within [0.0, 0.2], error=0
            "strain_load": 0.0,       # within range, error=0
            "damage_level": 0.0,      # within range, error=0
            "memory_risk": 0.0,       # within range, error=0
            "resource_scarcity": 0.0, # within range, error=0
        }
        ctx = _ctx(tick=1, interoceptive_vector=intero)
        output = module.update(1, ctx)

        errors = output.state["errors"]
        assert errors["energy_deficit"] > 0  # 0.5 - 0.3 = 0.2
        assert errors["thermal_stress"] == 0.0
        assert errors["strain_load"] == 0.0


class TestHomeostasisViabilityScoring:
    def test_viability_scoring(self, module):
        """Viability decreases with errors."""
        # All channels at high values -> many errors
        intero = {
            "energy_deficit": 0.8,
            "thermal_stress": 0.7,
            "strain_load": 0.8,
            "damage_level": 0.6,
            "memory_risk": 0.5,
            "resource_scarcity": 0.8,
        }
        ctx = _ctx(tick=1, interoceptive_vector=intero)
        output = module.update(1, ctx)

        assert output.state["viability"] < 1.0
        # With these high values, viability should be quite low
        assert output.state["viability"] < 0.5


class TestHomeostasisRegulationPriorities:
    def test_regulation_priorities(self, module):
        """Priorities ordered by error magnitude."""
        intero = {
            "energy_deficit": 0.9,      # highest error
            "thermal_stress": 0.1,      # no error (within range)
            "strain_load": 0.5,         # moderate error
            "damage_level": 0.7,        # high error
            "memory_risk": 0.0,         # no error
            "resource_scarcity": 0.4,   # small error
        }
        ctx = _ctx(tick=1, interoceptive_vector=intero)
        output = module.update(1, ctx)

        priorities = output.state["regulation_priorities"]
        # Should be ordered by descending error
        assert len(priorities) > 0
        errors_in_order = [p["error"] for p in priorities]
        assert errors_in_order == sorted(errors_in_order, reverse=True)
        # energy_deficit should be first (highest error)
        assert priorities[0]["channel"] == "energy_deficit"


class TestHomeostasisCriticalViabilityEvent:
    def test_critical_viability_event(self, module):
        """Event when viability < 0.3."""
        # Push all channels to critical levels
        intero = {
            "energy_deficit": 0.9,
            "thermal_stress": 0.8,
            "strain_load": 0.9,
            "damage_level": 0.8,
            "memory_risk": 0.7,
            "resource_scarcity": 0.9,
        }
        ctx = _ctx(tick=1, interoceptive_vector=intero)
        output = module.update(1, ctx)

        assert output.state["viability"] < 0.3
        event_types = [e.event_type for e in output.events]
        assert "viability_critical" in event_types


class TestHomeostasisCascadingFailure:
    def test_cascading_failure(self, module):
        """Multiple variables going critical."""
        intero = {
            "energy_deficit": 1.0,
            "thermal_stress": 1.0,
            "strain_load": 1.0,
            "damage_level": 1.0,
            "memory_risk": 1.0,
            "resource_scarcity": 1.0,
        }
        ctx = _ctx(tick=1, interoceptive_vector=intero)
        output = module.update(1, ctx)

        # All channels should have errors
        errors = output.state["errors"]
        assert all(v > 0 for v in errors.values())
        # Viability should be near zero
        assert output.state["viability"] < 0.1
        # All channels should appear in priorities
        priority_channels = [p["channel"] for p in output.state["regulation_priorities"]]
        assert len(priority_channels) == 6
