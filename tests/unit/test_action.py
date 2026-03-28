"""Unit tests for the DefaultActionSelection module."""

import pytest

from saa.core.types import ActionType, EnvironmentState, Event, ModuleOutput, TickContext
from saa.modules.action.default import DefaultActionSelection


@pytest.fixture
def module():
    m = DefaultActionSelection()
    m.initialize()
    return m


def _ctx(tick=1, embodiment_state=None, interoceptive_vector=None,
         homeostatic_error=None, allostatic_forecast=None,
         modulator_state=None, self_model_state=None,
         memory_context=None, valuation_map=None, social_state=None):
    return TickContext(
        tick=tick,
        dt=1.0,
        agent_id="test",
        environment=EnvironmentState(tick=tick),
        embodiment_state=embodiment_state,
        interoceptive_vector=interoceptive_vector,
        homeostatic_error=homeostatic_error,
        allostatic_forecast=allostatic_forecast,
        modulator_state=modulator_state,
        self_model_state=self_model_state,
        memory_context=memory_context,
        valuation_map=valuation_map,
        social_state=social_state,
    )


class TestActionInitialization:
    def test_initialization(self, module):
        """No action history."""
        state = module.get_state()
        assert state.action_history == []
        assert state.last_action == {}
        assert state.last_trace == {}


class TestActionSelection:
    def test_action_selection(self, module):
        """Selects highest-scored action."""
        # High energy deficit should favor REST and CONSUME
        emb = {"energy": 0.1, "strain": 0.8, "damage": 0.0, "resource_level": 0.5}
        intero = {"energy_deficit": 0.9, "resource_scarcity": 0.5, "curiosity_drive": 0.0,
                  "social_need": 0.0}
        ctx = _ctx(tick=1, embodiment_state=emb, interoceptive_vector=intero)
        output = module.update(1, ctx)

        trace = output.state["last_trace"]
        assert trace["selected"] in ["rest", "consume"]
        assert trace["selected_score"] > 0


class TestActionStressFavorsRest:
    def test_stress_favors_rest(self, module):
        """High stress increases rest score."""
        emb = {"energy": 0.3, "strain": 0.7, "damage": 0.1, "resource_level": 0.5}
        intero = {"energy_deficit": 0.7, "resource_scarcity": 0.0, "curiosity_drive": 0.1,
                  "social_need": 0.0}
        mod = {"stress_load": 0.9, "damage_salience": 0.1, "attachment": 0.0, "arousal": 0.5}
        ctx = _ctx(tick=1, embodiment_state=emb, interoceptive_vector=intero,
                   modulator_state=mod)
        output = module.update(1, ctx)

        # REST should score high because of energy_deficit and stress_load
        candidates = output.state["last_trace"]["candidates"]
        rest_entry = next(c for c in candidates if c["action"] == "rest")
        assert rest_entry["score"] > 0.5


class TestActionDamageFavorsWithdraw:
    def test_damage_favors_withdraw(self, module):
        """High damage increases withdrawal."""
        emb = {"energy": 0.8, "strain": 0.1, "damage": 0.8, "resource_level": 0.8}
        intero = {"energy_deficit": 0.2, "resource_scarcity": 0.2, "curiosity_drive": 0.0,
                  "social_need": 0.0}
        homeo = {"damage_error": 0.8}
        mod = {"stress_load": 0.3, "damage_salience": 0.9, "attachment": 0.0, "arousal": 0.5}
        ctx = _ctx(tick=1, embodiment_state=emb, interoceptive_vector=intero,
                   homeostatic_error=homeo, modulator_state=mod)
        output = module.update(1, ctx)

        candidates = output.state["last_trace"]["candidates"]
        withdraw_entry = next(c for c in candidates if c["action"] == "withdraw")
        # WITHDRAW should have a meaningful score
        assert withdraw_entry["score"] > 0.3


class TestActionConflictDetection:
    def test_conflict_detection(self, module):
        """Close scores flag as conflict."""
        # Set up a context where multiple actions score similarly
        emb = {"energy": 0.5, "strain": 0.3, "damage": 0.4, "resource_level": 0.5}
        intero = {"energy_deficit": 0.5, "resource_scarcity": 0.5, "curiosity_drive": 0.4,
                  "social_need": 0.3}
        homeo = {"damage_error": 0.4, "continuity_risk": 0.3}
        ctx = _ctx(tick=1, embodiment_state=emb, interoceptive_vector=intero,
                   homeostatic_error=homeo)
        output = module.update(1, ctx)

        trace = output.state["last_trace"]
        candidates = trace["candidates"]
        # Check if top two are within 0.1
        if len(candidates) >= 2:
            diff = candidates[0]["score"] - candidates[1]["score"]
            if diff < 0.1:
                assert trace["conflict"] is not None


class TestActionHistory:
    def test_action_history(self, module):
        """History maintained."""
        for t in range(1, 6):
            ctx = _ctx(tick=t)
            module.update(t, ctx)

        state = module.get_state()
        assert len(state.action_history) == 5
        # Each entry should have a tick field
        ticks = [h["tick"] for h in state.action_history]
        assert ticks == [1, 2, 3, 4, 5]
