"""Unit tests for the DefaultAllostasis module."""

import pytest

from saa.core.types import EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.allostasis.default import DefaultAllostasis


@pytest.fixture
def module():
    m = DefaultAllostasis()
    m.initialize()
    return m


def _ctx(tick=1, interoceptive_vector=None, homeostatic_error=None):
    return TickContext(
        tick=tick,
        dt=1.0,
        agent_id="test",
        environment=EnvironmentState(tick=tick),
        interoceptive_vector=interoceptive_vector,
        homeostatic_error=homeostatic_error,
    )


class TestAllostasisInitialization:
    def test_initialization(self, module):
        """Starts with empty forecasts."""
        state = module.get_state()
        assert state.forecasts == {}
        assert state.risk_scores == {}
        assert state.anticipatory_actions == []


class TestAllostasisTrendDetection:
    def test_trend_detection(self, module):
        """Detects upward trend in a channel."""
        # Feed increasing energy_deficit over several ticks
        for i in range(10):
            value = 0.1 + i * 0.08  # 0.1, 0.18, 0.26, ... 0.82
            intero = {"energy_deficit": value}
            ctx = _ctx(tick=i + 1, interoceptive_vector=intero)
            module.update(i + 1, ctx)

        state = module.get_state()
        # Forecast should extrapolate above current value (upward trend)
        assert state.forecasts["energy_deficit"] > 0.82


class TestAllostasisRiskScoring:
    def test_risk_scoring(self, module):
        """Risk score computed for trending channels."""
        # Feed steadily increasing values
        for i in range(10):
            value = 0.2 + i * 0.06
            intero = {"energy_deficit": value}
            ctx = _ctx(tick=i + 1, interoceptive_vector=intero)
            module.update(i + 1, ctx)

        state = module.get_state()
        # Risk score should be > 0 for an upward-trending channel
        assert state.risk_scores["energy_deficit"] > 0.0


class TestAllostasisAnticipatoryAction:
    def test_anticipatory_action(self, module):
        """Suggests conserve when energy trending down (deficit trending up)."""
        # Feed rapidly increasing energy_deficit to push risk above threshold
        for i in range(15):
            value = 0.3 + i * 0.05  # reaches 1.0 at i=14
            value = min(1.0, value)
            intero = {"energy_deficit": value}
            ctx = _ctx(tick=i + 1, interoceptive_vector=intero)
            module.update(i + 1, ctx)

        state = module.get_state()
        # Risk for energy_deficit should exceed threshold (0.6)
        assert state.risk_scores["energy_deficit"] > 0.6
        assert "conserve" in state.anticipatory_actions


class TestAllostasisPredictedCrisisEvent:
    def test_predicted_crisis_event(self, module):
        """Event when risk exceeds threshold."""
        # Feed rapidly increasing values to trigger crisis
        for i in range(15):
            value = min(1.0, 0.3 + i * 0.05)
            intero = {"energy_deficit": value}
            ctx = _ctx(tick=i + 1, interoceptive_vector=intero)
            output = module.update(i + 1, ctx)

        # The last output should have a predicted_crisis event
        crisis_events = [e for e in output.events if e.event_type == "predicted_crisis"]
        assert len(crisis_events) > 0
        assert "risk_scores" in crisis_events[0].data
