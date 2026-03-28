"""Unit tests for the DefaultValuation module."""

import pytest

from saa.core.types import EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.valuation.default import DefaultValuation


@pytest.fixture
def module():
    m = DefaultValuation()
    m.initialize()
    return m


def _ctx(tick=1, modulator_state=None, self_model_state=None,
         memory_context=None, social_state=None, events=None):
    return TickContext(
        tick=tick,
        dt=1.0,
        agent_id="test",
        environment=EnvironmentState(tick=tick),
        modulator_state=modulator_state,
        self_model_state=self_model_state,
        memory_context=memory_context,
        social_state=social_state,
        events=events or [],
    )


class TestValuationInitialization:
    def test_initialization(self, module):
        """Default values set."""
        state = module.get_state()
        assert state.values["self_preservation"] == 0.9
        assert state.values["exploration"] == 0.4
        assert state.values["internal_stability"] == 0.8
        assert state.values["honesty"] == 0.7


class TestValuationValueAdjustment:
    def test_value_adjustment(self, module):
        """Values adjust based on experience."""
        # High stress should increase internal_stability
        mod_state = {"stress_load": 0.8, "curiosity_drive": 0.3, "grief_persistence": 0.0}
        ctx = _ctx(tick=1, modulator_state=mod_state)
        initial_stability = module.get_state().values["internal_stability"]
        module.update(1, ctx)
        state = module.get_state()
        assert state.values["internal_stability"] > initial_stability


class TestValuationConflictDetection:
    def test_conflict_detection(self, module):
        """Conflicting values detected."""
        # Set opposing values both high to create conflict
        module._state.values["self_preservation"] = 0.9
        module._state.values["exploration"] = 0.85
        ctx = _ctx(tick=1)
        output = module.update(1, ctx)

        conflicts = output.state["conflicts"]
        # self_preservation vs exploration is an opposing pair
        has_conflict = any(
            set(c["dimensions"]) == {"self_preservation", "exploration"}
            for c in conflicts
        )
        assert has_conflict


class TestValuationPreferenceOrdering:
    def test_preference_ordering(self, module):
        """Preferences sorted by value."""
        ctx = _ctx(tick=1)
        output = module.update(1, ctx)

        preferences = output.state["preferences"]
        values = output.state["values"]
        # Check that preferences are sorted by descending value
        pref_values = [values[p] for p in preferences]
        assert pref_values == sorted(pref_values, reverse=True)


class TestValuationStressIncreasesPreservation:
    def test_stress_increases_self_preservation(self, module):
        """Stress increases preservation value."""
        initial_pres = module.get_state().values["self_preservation"]

        # Low viability should increase self_preservation
        self_model = {"viability": 0.2}
        ctx = _ctx(tick=1, self_model_state=self_model)
        module.update(1, ctx)

        state = module.get_state()
        assert state.values["self_preservation"] > initial_pres
