"""Unit tests for the DefaultObservability module."""

import pytest

from saa.core.types import EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.observability.default import DefaultObservability


@pytest.fixture
def module():
    m = DefaultObservability()
    m.initialize()
    return m


def _ctx(tick=1, embodiment_state=None, modulator_state=None, action_result=None):
    return TickContext(
        tick=tick,
        dt=1.0,
        agent_id="test",
        environment=EnvironmentState(tick=tick),
        embodiment_state=embodiment_state,
        modulator_state=modulator_state,
        action_result=action_result,
    )


class TestObservabilityInitialization:
    def test_initialization(self, module):
        """Empty snapshots."""
        state = module.get_state()
        assert state.snapshot_count == 0
        assert state.current_snapshot == {}
        assert module._snapshots == []


class TestObservabilitySnapshotRecording:
    def test_snapshot_recording(self, module):
        """Snapshots recorded each tick."""
        emb = {"energy": 0.8, "damage": 0.1}
        ctx = _ctx(tick=1, embodiment_state=emb)
        module.update(1, ctx)

        assert len(module._snapshots) == 1
        state = module.get_state()
        assert state.snapshot_count == 1
        assert state.current_snapshot["_obs_tick"] == 1
        assert state.current_snapshot["embodiment_state"] == emb


class TestObservabilityTraceRetrieval:
    def test_trace_retrieval(self, module):
        """Can query state traces."""
        for t in range(1, 6):
            emb = {"energy": 1.0 - t * 0.1, "damage": t * 0.05}
            ctx = _ctx(tick=t, embodiment_state=emb)
            module.update(t, ctx)

        # Query ticks 2-4
        trace = module.get_trace(2, 4)
        assert len(trace) == 3
        trace_ticks = [s["_obs_tick"] for s in trace]
        assert trace_ticks == [2, 3, 4]


class TestObservabilityModuleTrace:
    def test_module_trace(self, module):
        """Can query specific module traces."""
        for t in range(1, 6):
            emb = {"energy": 1.0 - t * 0.1, "damage": t * 0.05}
            mod = {"stress_load": t * 0.1}
            ctx = _ctx(tick=t, embodiment_state=emb, modulator_state=mod)
            module.update(t, ctx)

        # Query embodiment state traces
        emb_trace = module.get_module_trace("embodiment", 1, 5)
        assert len(emb_trace) == 5
        # Each entry should have an energy field and _tick
        for entry in emb_trace:
            assert "_tick" in entry
            assert "energy" in entry

        # Query modulator state traces
        mod_trace = module.get_module_trace("modulator", 2, 4)
        assert len(mod_trace) == 3
        for entry in mod_trace:
            assert "stress_load" in entry
