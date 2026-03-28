"""Unit tests for the SQLiteMemorySystem module."""

import pytest

from saa.core.types import EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.memory.default import SQLiteMemorySystem


@pytest.fixture
def module():
    m = SQLiteMemorySystem()
    m.initialize()
    return m


def _ctx(tick=1, homeostatic_error=None, events=None, social_state=None,
         interoceptive_vector=None):
    return TickContext(
        tick=tick,
        dt=1.0,
        agent_id="test",
        environment=EnvironmentState(tick=tick),
        homeostatic_error=homeostatic_error or {},
        events=events or [],
        social_state=social_state,
        interoceptive_vector=interoceptive_vector,
    )


class TestMemoryInitialization:
    def test_initialization(self, module):
        """Memory system initializes."""
        state = module.get_state()
        assert state.episodic_count == 0
        assert state.semantic_count == 0
        assert state.relational_count == 0
        assert state.last_encoded_tick == 0


class TestMemoryEpisodeEncoding:
    def test_episode_encoding(self, module):
        """Episodes stored and retrievable."""
        # High-severity event triggers importance above threshold
        events = [Event(
            tick=1,
            source_module="test",
            event_type="damage_critical",
            data={},
            severity=0.9,
        )]
        ctx = _ctx(tick=1, events=events)
        output = module.update(1, ctx)

        state = module.get_state()
        assert state.episodic_count >= 1
        assert state.last_encoded_tick == 1
        # Memory context should indicate encoding happened
        assert output.state["memory_context"]["encoded_this_tick"] is True


class TestMemoryImportanceWeighting:
    def test_importance_weighting(self, module):
        """High-importance episodes retained, low-importance ones skipped."""
        # Low importance: no events, no errors -> importance below threshold
        ctx_low = _ctx(tick=1)
        output_low = module.update(1, ctx_low)
        assert output_low.state["memory_context"]["encoded_this_tick"] is False

        # High importance: severe event
        events = [Event(
            tick=2,
            source_module="test",
            event_type="crisis",
            data={},
            severity=0.95,
        )]
        ctx_high = _ctx(tick=2, events=events)
        output_high = module.update(2, ctx_high)
        assert output_high.state["memory_context"]["encoded_this_tick"] is True


class TestMemoryDecay:
    def test_decay(self, module):
        """Importance decays over time for old episodes."""
        # Encode an episode at tick=1
        events = [Event(tick=1, source_module="test", event_type="crisis",
                        data={}, severity=0.9)]
        module.update(1, _ctx(tick=1, events=events))

        # Get initial importance
        rows = module._conn.execute(
            "SELECT importance FROM episodic_memory WHERE tick = 1"
        ).fetchall()
        initial_importance = rows[0]["importance"]

        # Run many ticks to trigger decay (decay applies to episodes older than 10 ticks)
        for t in range(2, 25):
            module.update(t, _ctx(tick=t))

        rows = module._conn.execute(
            "SELECT importance FROM episodic_memory WHERE tick = 1"
        ).fetchall()
        if rows:
            decayed_importance = rows[0]["importance"]
            assert decayed_importance < initial_importance


class TestMemoryRelationalMemory:
    def test_relational_memory(self, module):
        """Trust/betrayal stored per agent."""
        # Encode a positive interaction
        module.encode_relational("agent_a", trust_delta=0.2, interaction_type="cooperation")
        rel = module.get_relational("agent_a")
        assert rel["trust"] == pytest.approx(0.7, abs=0.01)
        assert rel["interaction_count"] == 1

        # Encode a betrayal
        module.encode_relational("agent_a", trust_delta=-0.3, interaction_type="betrayal")
        rel = module.get_relational("agent_a")
        assert rel["trust"] < 0.7
        assert rel["betrayal_count"] == 1
        assert rel["interaction_count"] == 2

        # Check unknown agent returns empty
        assert module.get_relational("unknown_agent") == {}
