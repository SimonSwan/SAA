"""Unit tests for the DefaultInteroception module."""

import pytest

from saa.core.types import EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.interoception.default import DefaultInteroception


@pytest.fixture
def module():
    m = DefaultInteroception()
    m.initialize()
    return m


def _ctx(tick=1, embodiment_state=None):
    return TickContext(
        tick=tick,
        dt=1.0,
        agent_id="test",
        environment=EnvironmentState(tick=tick),
        embodiment_state=embodiment_state,
    )


class TestInteroceptionInitialization:
    def test_initialization(self, module):
        """Starts with empty channels."""
        state = module.get_state()
        assert state.channels == {}
        assert state.history == []
        assert state.alerts == []


class TestInteroceptionChannelComputation:
    def test_channel_computation(self, module):
        """Channels computed correctly from body state."""
        body = {
            "energy": 0.3,
            "temperature": 0.8,
            "strain": 0.6,
            "damage": 0.4,
            "memory_integrity": 0.7,
            "resource_level": 0.5,
        }
        ctx = _ctx(tick=1, embodiment_state=body)
        output = module.update(1, ctx)

        channels = output.state["channels"]
        # energy_deficit = 1.0 - 0.3 = 0.7
        assert abs(channels["energy_deficit"] - 0.7) < 0.01
        # thermal_stress = min(1.0, abs(0.8 - 0.5) * 2.0) = 0.6
        assert abs(channels["thermal_stress"] - 0.6) < 0.01
        # strain_load = 0.6
        assert abs(channels["strain_load"] - 0.6) < 0.01
        # damage_level = 0.4
        assert abs(channels["damage_level"] - 0.4) < 0.01
        # memory_risk = 1.0 - 0.7 = 0.3
        assert abs(channels["memory_risk"] - 0.3) < 0.01
        # resource_scarcity = 1.0 - 0.5 = 0.5
        assert abs(channels["resource_scarcity"] - 0.5) < 0.01


class TestInteroceptionTemporalSmoothing:
    def test_temporal_smoothing(self, module):
        """Values smoothed over window using EMA."""
        # First tick establishes raw values
        body1 = {"energy": 1.0, "temperature": 0.5, "strain": 0.0,
                 "damage": 0.0, "memory_integrity": 1.0, "resource_level": 1.0}
        module.update(1, _ctx(tick=1, embodiment_state=body1))

        # Second tick with very different values - smoothing should dampen
        body2 = {"energy": 0.0, "temperature": 0.5, "strain": 1.0,
                 "damage": 1.0, "memory_integrity": 0.0, "resource_level": 0.0}
        output = module.update(2, _ctx(tick=2, embodiment_state=body2))

        channels = output.state["channels"]
        # With alpha=0.3, energy_deficit should be 0.3*1.0 + 0.7*0.0 = 0.3
        # (raw was 0.0 first tick -> energy_deficit=0; raw is 1.0 second tick)
        assert abs(channels["energy_deficit"] - 0.3) < 0.01
        # strain_load: 0.3*1.0 + 0.7*0.0 = 0.3
        assert abs(channels["strain_load"] - 0.3) < 0.01


class TestInteroceptionThresholdAlert:
    def test_threshold_alert(self, module):
        """Alerts emitted on threshold crossing."""
        body = {"energy": 0.1, "temperature": 0.5, "strain": 0.0,
                "damage": 0.0, "memory_integrity": 1.0, "resource_level": 1.0}
        ctx = _ctx(tick=1, embodiment_state=body)
        output = module.update(1, ctx)

        # energy_deficit = 0.9, threshold = 0.6 -> should trigger alert
        assert any(e.event_type == "threshold_crossed" for e in output.events)
        threshold_events = [e for e in output.events if e.event_type == "threshold_crossed"]
        energy_alert = [e for e in threshold_events if e.data["channel"] == "energy_deficit"]
        assert len(energy_alert) > 0


class TestInteroceptionAnomalyDetection:
    def test_anomaly_detection(self, module):
        """Sudden jumps detected as anomalies."""
        # First tick - normal state
        body1 = {"energy": 1.0, "temperature": 0.5, "strain": 0.0,
                 "damage": 0.0, "memory_integrity": 1.0, "resource_level": 1.0}
        module.update(1, _ctx(tick=1, embodiment_state=body1))

        # Second tick - huge jump in damage (0.0 -> 1.0)
        # After smoothing: damage_level = 0.3*1.0 + 0.7*0.0 = 0.3
        # Delta = |0.3 - 0.0| = 0.3, threshold = 0.3 -> needs > 0.3
        # Use a config with lower threshold to guarantee detection
        module._config.anomaly_jump_threshold = 0.2
        body2 = {"energy": 1.0, "temperature": 0.5, "strain": 0.0,
                 "damage": 1.0, "memory_integrity": 1.0, "resource_level": 1.0}
        output = module.update(2, _ctx(tick=2, embodiment_state=body2))

        anomaly_events = [e for e in output.events if e.event_type == "anomaly_detected"]
        assert len(anomaly_events) > 0
        assert any(e.data["channel"] == "damage_level" for e in anomaly_events)
