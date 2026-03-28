"""Unit tests for the DefaultSelfModel module."""

import pytest

from saa.core.types import EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.self_model.default import DefaultSelfModel


@pytest.fixture
def module():
    m = DefaultSelfModel()
    m.initialize()
    return m


def _ctx(tick=1, homeostatic_error=None, allostatic_forecast=None, events=None):
    return TickContext(
        tick=tick,
        dt=1.0,
        agent_id="test",
        environment=EnvironmentState(tick=tick),
        homeostatic_error=homeostatic_error or {},
        allostatic_forecast=allostatic_forecast or {},
        events=events or [],
    )


class TestSelfModelInitialization:
    def test_initialization(self, module):
        """Starts with identity anchors and continuity 1.0."""
        state = module.get_state()
        assert state.continuity_score == 1.0
        assert "continuity" in state.identity_anchors
        assert "stability" in state.identity_anchors
        assert "learning" in state.identity_anchors
        assert state.autobiographical_entries == []


class TestSelfModelContinuityDecay:
    def test_continuity_decay(self, module):
        """Score decays slightly each tick."""
        initial = module.get_state().continuity_score
        ctx = _ctx(tick=1)
        module.update(1, ctx)
        state = module.get_state()
        # With no threats, decay_rate=0.01 is applied, then +0.005 recovery
        # Net change: -0.01 + 0.005 = -0.005
        assert state.continuity_score < initial


class TestSelfModelThreatDetection:
    def test_threat_detection(self, module):
        """Detects threats from high memory_risk."""
        # High memory_risk in allostatic forecast triggers memory_wipe_threat
        allostatic = {"risk_scores": {"memory_risk": 0.9}}
        ctx = _ctx(tick=1, allostatic_forecast=allostatic)
        output = module.update(1, ctx)

        # Should emit continuity_threat event
        event_types = [e.event_type for e in output.events]
        assert "continuity_threat" in event_types
        threat_event = [e for e in output.events if e.event_type == "continuity_threat"][0]
        threat_types = [t["type"] for t in threat_event.data["threats"]]
        assert "memory_wipe_threat" in threat_types


class TestSelfModelAutobiographicalRecording:
    def test_autobiographical_recording(self, module):
        """Significant events recorded in autobiography."""
        # Pass a high-severity event to trigger recording
        events = [Event(
            tick=1,
            source_module="test",
            event_type="damage_critical",
            data={},
            severity=0.9,
        )]
        ctx = _ctx(tick=1, events=events)
        module.update(1, ctx)

        state = module.get_state()
        assert len(state.autobiographical_entries) > 0
        entry = state.autobiographical_entries[0]
        assert entry["tick"] == 1
        assert "damage_critical" in entry["event_types"]


class TestSelfModelContinuityThreatEvent:
    def test_continuity_threat_event(self, module):
        """Event emitted under threat."""
        # Create a high memory_risk threat
        allostatic = {"risk_scores": {"memory_risk": 0.8}}
        ctx = _ctx(tick=1, allostatic_forecast=allostatic)
        output = module.update(1, ctx)

        assert any(e.event_type == "continuity_threat" for e in output.events)
        threat_event = [e for e in output.events if e.event_type == "continuity_threat"][0]
        assert threat_event.data["continuity_score"] < 1.0
        assert "identity_anchors" in threat_event.data
