"""Unit tests for the DefaultNeuromodulation module."""

import pytest

from saa.core.types import EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.neuromodulation.default import DefaultNeuromodulation


@pytest.fixture
def module():
    m = DefaultNeuromodulation()
    m.initialize()
    return m


def _ctx(tick=1, embodiment_state=None, interoceptive_vector=None,
         homeostatic_error=None, social_state=None, events=None,
         hazard_level=0.0):
    return TickContext(
        tick=tick,
        dt=1.0,
        agent_id="test",
        environment=EnvironmentState(hazard_level=hazard_level, tick=tick),
        embodiment_state=embodiment_state or {},
        interoceptive_vector=interoceptive_vector or {},
        homeostatic_error=homeostatic_error or {},
        social_state=social_state or {},
        events=events or [],
    )


class TestNeuromodulationInitialization:
    def test_initialization(self, module):
        """Modulators at baseline."""
        state = module.get_state()
        assert state.modulators["stress_load"] == pytest.approx(0.2, abs=0.01)
        assert state.modulators["curiosity_drive"] == pytest.approx(0.5, abs=0.01)
        assert state.modulators["grief_persistence"] == pytest.approx(0.0, abs=0.01)
        assert state.modulators["reward_drive"] == pytest.approx(0.5, abs=0.01)


class TestNeuromodulationStressAccumulation:
    def test_stress_accumulation(self, module):
        """Stress increases under threat."""
        initial_stress = module.get_state().modulators["stress_load"]
        # High damage, strain, and hazard should accumulate stress
        emb = {"damage": 0.7, "strain": 0.6}
        ctx = _ctx(tick=1, embodiment_state=emb, hazard_level=0.8)
        module.update(1, ctx)
        state = module.get_state()
        assert state.modulators["stress_load"] > initial_stress


class TestNeuromodulationSlowDecay:
    def test_slow_decay(self, module):
        """Modulators decay toward baseline."""
        # Push stress high
        module._state.modulators["stress_load"] = 0.9
        # Run with no threatening inputs to let it decay
        ctx = _ctx(tick=1, embodiment_state={"damage": 0.0, "strain": 0.0})
        module.update(1, ctx)
        state = module.get_state()
        # Stress should have decayed toward baseline (0.2)
        assert state.modulators["stress_load"] < 0.9


class TestNeuromodulationGriefPersistence:
    def test_grief_persistence(self, module):
        """Grief decays very slowly."""
        # Set grief high
        module._state.modulators["grief_persistence"] = 0.8
        # Run one tick with no loss events
        ctx = _ctx(tick=1)
        module.update(1, ctx)
        state = module.get_state()
        # Grief should still be close to 0.8 (decay rate is 0.005)
        # Decay: 0.8 + (0.0 - 0.8) * 0.005 * 1.0 = 0.8 - 0.004 = 0.796
        assert state.modulators["grief_persistence"] > 0.79


class TestNeuromodulationParameterShifts:
    def test_parameter_shifts(self, module):
        """Shifts computed from modulator state."""
        # Set stress high so shifts are significant
        module._state.modulators["stress_load"] = 0.8
        ctx = _ctx(tick=1)
        module.update(1, ctx)
        state = module.get_state()

        shifts = state.parameter_shifts
        assert "planning_depth" in shifts
        assert "action_urgency" in shifts
        # High stress should reduce planning depth and increase urgency
        assert shifts["planning_depth"] < 0
        assert shifts["action_urgency"] > 0


class TestNeuromodulationSocialStress:
    """Stress must rise from conversational/social events, not just physical."""

    def test_threatening_sio_event_raises_stress(self, module):
        """A threatening SIO interaction event should increase stress."""
        initial = module.get_state().modulators["stress_load"]
        threat_event = Event(
            tick=1, source_module="sio", event_type="social_threat",
            data={"classification": "threatening", "urgency": 0.8, "social_signal": -0.5},
            severity=0.8,
        )
        ctx = _ctx(tick=1, events=[threat_event])
        module.update(1, ctx)
        assert module.get_state().modulators["stress_load"] > initial

    def test_demanding_sio_event_raises_stress(self, module):
        """A demanding SIO interaction event should increase stress."""
        initial = module.get_state().modulators["stress_load"]
        demand_event = Event(
            tick=1, source_module="sio", event_type="social_demand",
            data={"classification": "demanding", "urgency": 0.8, "social_signal": 0.0},
            severity=0.8,
        )
        ctx = _ctx(tick=1, events=[demand_event])
        module.update(1, ctx)
        assert module.get_state().modulators["stress_load"] > initial

    def test_repeated_demands_compound_stress(self, module):
        """Multiple demanding events should compound stress."""
        for i in range(5):
            event = Event(
                tick=i + 1, source_module="sio", event_type="social_demand",
                data={"classification": "demanding", "urgency": 0.8, "social_signal": 0.0},
                severity=0.8,
            )
            ctx = _ctx(tick=i + 1, events=[event])
            module.update(i + 1, ctx)
        stress = module.get_state().modulators["stress_load"]
        assert stress > 0.3, f"5 demanding events should raise stress above 0.3, got {stress}"

    def test_trust_erosion_raises_stress(self, module):
        """Low trust should contribute to stress."""
        module._state.modulators["trust_level"] = 0.2
        initial = module.get_state().modulators["stress_load"]
        ctx = _ctx(tick=1)
        ctx.self_model_state = {"continuity_score": 0.6}
        module.update(1, ctx)
        assert module.get_state().modulators["stress_load"] > initial

    def test_continuity_threat_event_raises_stress(self, module):
        """A continuity_threat event should increase stress."""
        initial = module.get_state().modulators["stress_load"]
        event = Event(
            tick=1, source_module="self_model", event_type="continuity_threat",
            data={"threat_type": "memory_corruption"}, severity=0.7,
        )
        ctx = _ctx(tick=1, events=[event])
        module.update(1, ctx)
        assert module.get_state().modulators["stress_load"] > initial

    def test_supportive_interaction_does_not_add_stress(self, module):
        """A supportive SIO event should not increase stress."""
        initial = module.get_state().modulators["stress_load"]
        support_event = Event(
            tick=1, source_module="sio", event_type="social_support",
            data={"classification": "supportive", "urgency": 0.3, "social_signal": 0.5},
            severity=0.3,
        )
        ctx = _ctx(tick=1, events=[support_event])
        module.update(1, ctx)
        after = module.get_state().modulators["stress_load"]
        # Should not increase (may decrease slightly due to decay)
        assert after <= initial + 0.01


class TestNeuromodulationCuriositySuppression:
    def test_curiosity_suppression(self, module):
        """Curiosity drops under high stress."""
        initial_curiosity = module.get_state().modulators["curiosity_drive"]
        # Set stress above 0.5 to suppress curiosity
        module._state.modulators["stress_load"] = 0.8
        ctx = _ctx(tick=1, embodiment_state={"damage": 0.5, "strain": 0.5},
                   hazard_level=0.7)
        module.update(1, ctx)
        state = module.get_state()
        assert state.modulators["curiosity_drive"] < initial_curiosity
