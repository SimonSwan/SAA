"""Unit tests for the DefaultSocial module."""

import pytest

from saa.core.types import EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.social.default import DefaultSocial


@pytest.fixture
def module():
    m = DefaultSocial()
    m.initialize()
    return m


def _ctx(tick=1, social_agents=None, events=None):
    return TickContext(
        tick=tick,
        dt=1.0,
        agent_id="test",
        environment=EnvironmentState(
            social_agents=social_agents or [],
            tick=tick,
        ),
        events=events or [],
    )


class TestSocialInitialization:
    def test_initialization(self, module):
        """Empty relationship graph."""
        state = module.get_state()
        assert state.relationships == {}
        assert state.total_bond_strength == 0.0
        assert state.attachment_risk == 0.0


class TestSocialTrustFormation:
    def test_trust_formation(self, module):
        """Trust increases with positive interactions."""
        events = [Event(
            tick=1,
            source_module="test",
            event_type="trust_gain",
            data={"agent_id": "ally_1", "amount": 1.0},
            severity=0.3,
        )]
        ctx = _ctx(tick=1, social_agents=["ally_1"], events=events)
        output = module.update(1, ctx)

        rel = output.state["relationships"]["ally_1"]
        # Initial trust=0.5, gain_rate=0.05 * 1.0 * 1.0 * 1.0 = 0.05
        # minus decay: 0.02 * 1.0 = 0.02
        # net: 0.5 + 0.05 - 0.02 = 0.53
        assert rel["trust"] > 0.5


class TestSocialBetrayalImpact:
    def test_betrayal_impact(self, module):
        """Trust drops sharply on betrayal."""
        # First establish relationship
        ctx1 = _ctx(tick=1, social_agents=["enemy_1"])
        module.update(1, ctx1)

        # Now betrayal
        events = [Event(
            tick=2,
            source_module="test",
            event_type="betrayal",
            data={"agent_id": "enemy_1"},
            severity=0.8,
        )]
        ctx2 = _ctx(tick=2, social_agents=["enemy_1"], events=events)
        output = module.update(2, ctx2)

        rel = output.state["relationships"]["enemy_1"]
        # Initial trust was 0.5, betrayal_impact=0.3 -> drops to ~0.2 minus decay
        assert rel["trust"] < 0.5
        assert rel["betrayal_count"] == 1


class TestSocialAttachmentGrowth:
    def test_attachment_growth(self, module):
        """Attachment grows with stabilizing agent."""
        events = [Event(
            tick=1,
            source_module="test",
            event_type="stabilizing_presence",
            data={"agent_id": "caregiver_1", "magnitude": 0.8},
            severity=0.3,
        )]
        ctx = _ctx(tick=1, social_agents=["caregiver_1"], events=events)
        output = module.update(1, ctx)

        rel = output.state["relationships"]["caregiver_1"]
        assert rel["attachment"] > 0.0
        assert rel["dependency"] > 0.0


class TestSocialSeparationStress:
    def test_separation_stress(self, module):
        """Stress when bonded agent absent."""
        # Build a strong bond by directly setting relationship data
        module._ensure_relationship("bonded_agent")
        rel = module._graph["self"]["bonded_agent"]
        rel["trust"] = 0.9
        rel["attachment"] = 0.8
        rel["dependency"] = 0.5
        rel["bond_strength"] = 0.7  # above attachment_threshold (0.6)
        rel["last_seen_tick"] = 0

        # Agent is absent and 10 ticks have passed
        ctx = _ctx(tick=10, social_agents=[])  # bonded_agent not present
        output = module.update(10, ctx)

        # Should emit separation_stress event
        sep_events = [e for e in output.events if e.event_type == "separation_stress"]
        assert len(sep_events) > 0
        assert sep_events[0].data["agent_id"] == "bonded_agent"


class TestSocialCautionAfterBetrayal:
    def test_caution_after_betrayal(self, module):
        """Trust recovery slower after betrayal."""
        # Establish relationship with betrayal history
        module._ensure_relationship("unreliable_1")
        rel = module._graph["self"]["unreliable_1"]
        rel["trust"] = 0.3
        rel["betrayal_count"] = 2

        # Trust gain event
        events_gain = [Event(
            tick=1,
            source_module="test",
            event_type="trust_gain",
            data={"agent_id": "unreliable_1", "amount": 1.0},
            severity=0.3,
        )]
        ctx1 = _ctx(tick=1, social_agents=["unreliable_1"], events=events_gain)
        module.update(1, ctx1)
        trust_after_caution = module._graph["self"]["unreliable_1"]["trust"]

        # Compare with a clean agent getting same trust_gain
        module._ensure_relationship("clean_1")
        rel_clean = module._graph["self"]["clean_1"]
        rel_clean["trust"] = 0.3
        rel_clean["betrayal_count"] = 0

        events_gain2 = [Event(
            tick=2,
            source_module="test",
            event_type="trust_gain",
            data={"agent_id": "clean_1", "amount": 1.0},
            severity=0.3,
        )]
        ctx2 = _ctx(tick=2, social_agents=["clean_1", "unreliable_1"], events=events_gain2)
        module.update(2, ctx2)
        trust_clean = module._graph["self"]["clean_1"]["trust"]

        # The betrayed agent should have gained less trust
        # (gain_factor = 1/(1+2) = 0.333 vs 1/(1+0) = 1.0)
        assert trust_after_caution < trust_clean
