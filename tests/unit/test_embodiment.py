"""Unit tests for the SimulatedEmbodiment module."""

import pytest

from saa.core.types import EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.embodiment.default import SimulatedEmbodiment


@pytest.fixture
def module():
    m = SimulatedEmbodiment()
    m.initialize()
    return m


def _ctx(tick=1, dt=1.0, hazard=0.0, ambient_temp=0.5, resources=0.8):
    return TickContext(
        tick=tick,
        dt=dt,
        agent_id="test",
        environment=EnvironmentState(
            hazard_level=hazard,
            ambient_temperature=ambient_temp,
            available_resources=resources,
            tick=tick,
        ),
    )


class TestEmbodimentInitialization:
    def test_initialization(self, module):
        state = module.get_state()
        assert state.energy == 1.0
        assert state.temperature == 0.5
        assert state.strain == 0.0
        assert state.damage == 0.0
        assert state.memory_integrity == 1.0
        assert state.resource_level == 1.0
        assert state.recovery_rate == 0.5


class TestEmbodimentEnergyDepletion:
    def test_energy_depletion(self, module):
        """Energy decreases over ticks due to base depletion."""
        initial_energy = module.get_state().energy
        ctx = _ctx(tick=1)
        module.update(1, ctx)
        state = module.get_state()
        # Energy should decrease (base depletion minus resource replenishment)
        # base_depletion=0.02, resource_consumption=0.01, actual_consumed replenishes 0.5*consumed
        # Net: energy -= 0.02, then += min(0.01, 0.8) * 0.5 = 0.005 => net -0.015
        assert state.energy < initial_energy


class TestEmbodimentRecovery:
    def test_recovery(self, module):
        """Damage recovers slowly over time via recovery_rate."""
        # Inject some damage
        module._state.damage = 0.5
        ctx = _ctx(tick=1, hazard=0.0)
        module.update(1, ctx)
        state = module.get_state()
        # damage_recovery_factor=0.03, recovery_rate=0.5 => recovery = 0.015 per tick
        assert state.damage < 0.5


class TestEmbodimentEnvironmentEffects:
    def test_environment_effects(self, module):
        """Hazard level increases damage."""
        ctx = _ctx(tick=1, hazard=0.8)
        module.update(1, ctx)
        state = module.get_state()
        # hazard_damage_rate=0.05 * 0.8 = 0.04 damage added
        # minus recovery: 0.03 * 0.5 = 0.015
        # net damage > 0
        assert state.damage > 0.0
        # Strain should also increase from hazard
        assert state.strain > 0.0


class TestEmbodimentCriticalEnergyEvent:
    def test_critical_energy_event(self, module):
        """Event emitted when energy < 0.2."""
        module._state.energy = 0.1
        ctx = _ctx(tick=1)
        output = module.update(1, ctx)
        event_types = [e.event_type for e in output.events]
        assert "critical_energy_low" in event_types


class TestEmbodimentOverheatingEvent:
    def test_overheating_event(self, module):
        """Event emitted when temperature > 0.8."""
        # Set high ambient temperature to push body temp up
        module._state.temperature = 0.85
        ctx = _ctx(tick=1, ambient_temp=0.95)
        output = module.update(1, ctx)
        # Temperature should remain above 0.8 since it started at 0.85 and
        # moves toward 0.95
        event_types = [e.event_type for e in output.events]
        assert "overheating" in event_types
