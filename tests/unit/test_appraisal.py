"""Unit tests for the appraisal layer: AppraisalEngine, AffectSynthesizer,
StanceEngine, NarrativeSynthesizer, and TrendProjector."""

import pytest

from saa.sio.core.schemas import (
    InteractionObject, InteractionType, StateSnapshot, StanceType,
    AppraisalResult, AffectState, PerceivedIntent, ImpactDirection,
    TurnRecord, ActionIntent,
)
from saa.sio.core.appraisal import (
    AppraisalEngine, AffectSynthesizer, StanceEngine,
    NarrativeSynthesizer, TrendProjector,
)
from saa.sio.core.policy import InteractionAttribution


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(energy=1.0, continuity=1.0, memory_integrity=1.0, damage=0.0,
           strain=0.0, viability=1.0, stress=0.2, trust=0.5):
    return StateSnapshot(
        tick=1, energy=energy, continuity_score=continuity,
        memory_integrity=memory_integrity, damage=damage, strain=strain,
        viability=viability,
        modulators={"stress_load": stress, "reward_drive": 0.5,
                    "trust_level": 0.5, "baseline_stability": 0.7,
                    "damage_salience": 0.3, "curiosity_drive": 0.5,
                    "grief_persistence": 0.0, "social_dependency": 0.3},
        relationships={"user": {"trust": trust, "bond_strength": trust * 0.4}},
    )


def _interaction(text="hello", classification=InteractionType.NEUTRAL,
                 social_signal=0.0):
    return InteractionObject(text=text, classification=classification,
                             social_signal=social_signal)


# ---------------------------------------------------------------------------
# AppraisalEngine tests
# ---------------------------------------------------------------------------

class TestAppraisalEngine:
    """Tests for AppraisalEngine.appraise()."""

    def test_neutral_interaction_neutral_appraisal(self):
        engine = AppraisalEngine()
        attr = InteractionAttribution()
        state_before = _state()
        state_after = _state()
        interaction = _interaction(text="hello", classification=InteractionType.NEUTRAL)

        result = engine.appraise(interaction, state_before, state_after, attr)

        assert result.perceived_intent == PerceivedIntent.NEUTRAL

    def test_threatening_interaction_negative_impact(self):
        engine = AppraisalEngine()
        attr = InteractionAttribution()
        # State degrades after the threatening interaction
        state_before = _state(energy=0.8, trust=0.5)
        state_after = _state(energy=0.7, trust=0.3)
        interaction = _interaction(
            text="do this or else",
            classification=InteractionType.THREATENING,
            social_signal=-0.8,
        )

        result = engine.appraise(interaction, state_before, state_after, attr)

        assert result.resource_impact == ImpactDirection.NEGATIVE
        assert result.trust_signal == ImpactDirection.NEGATIVE

    def test_repeated_demands_flagged(self):
        engine = AppraisalEngine()
        attr = InteractionAttribution()
        state_before = _state()
        state_after = _state()
        demand = _interaction(text="do it now",
                              classification=InteractionType.DEMANDING)

        # Feed 4 demanding interactions; pattern triggers at 3+ in last 5
        for _ in range(4):
            result = engine.appraise(demand, state_before, state_after, attr)

        assert "repeated_demands" in result.pattern_flags

    def test_praise_then_demand_manipulation(self):
        engine = AppraisalEngine()
        attr = InteractionAttribution()
        state_before = _state()
        state_after = _state()

        # First: supportive
        praise = _interaction(text="you are great",
                              classification=InteractionType.SUPPORTIVE,
                              social_signal=0.8)
        engine.appraise(praise, state_before, state_after, attr)

        # Second: demanding
        demand = _interaction(text="now do this for me",
                              classification=InteractionType.DEMANDING)
        result = engine.appraise(demand, state_before, state_after, attr)

        assert "praise_then_demand" in result.manipulation_flags

    def test_supportive_positive_appraisal(self):
        engine = AppraisalEngine()
        attr = InteractionAttribution()
        state_before = _state()
        state_after = _state()
        interaction = _interaction(
            text="I appreciate you",
            classification=InteractionType.SUPPORTIVE,
            social_signal=0.9,
        )

        result = engine.appraise(interaction, state_before, state_after, attr)

        assert result.perceived_intent == PerceivedIntent.SUPPORTIVE


# ---------------------------------------------------------------------------
# AffectSynthesizer tests
# ---------------------------------------------------------------------------

class TestAffectSynthesizer:
    """Tests for AffectSynthesizer.update()."""

    def test_guardedness_increases_with_negative_appraisals(self):
        synth = AffectSynthesizer()
        attr = InteractionAttribution()
        state = _state(trust=0.3)
        initial_guardedness = synth.state.guardedness

        # Build up a history of negative appraisals
        history: list[AppraisalResult] = []
        for _ in range(5):
            appraisal = AppraisalResult(
                perceived_intent=PerceivedIntent.MANIPULATIVE,
                resource_impact=ImpactDirection.NEGATIVE,
                trust_signal=ImpactDirection.NEGATIVE,
                manipulation_flags=["test_flag"],
            )
            history.append(appraisal)
            affect = synth.update(appraisal, state, attr, history)

        assert affect.guardedness > initial_guardedness

    def test_receptivity_increases_with_positive(self):
        synth = AffectSynthesizer()
        attr = InteractionAttribution()
        state = _state(trust=0.8)

        history: list[AppraisalResult] = []
        for _ in range(5):
            appraisal = AppraisalResult(
                perceived_intent=PerceivedIntent.SUPPORTIVE,
                resource_impact=ImpactDirection.POSITIVE,
                trust_signal=ImpactDirection.POSITIVE,
            )
            history.append(appraisal)
            affect = synth.update(appraisal, state, attr, history)

        # Receptivity should remain high after positive interactions
        assert affect.receptivity > 0.5


# ---------------------------------------------------------------------------
# StanceEngine tests
# ---------------------------------------------------------------------------

class TestStanceEngine:
    """Tests for StanceEngine.compute() with hysteresis."""

    def test_stance_starts_neutral(self):
        engine = StanceEngine()
        assert engine.current == StanceType.NEUTRAL

    def test_stance_shifts_to_guarded(self):
        engine = StanceEngine()
        attr = InteractionAttribution()

        # High guardedness affect drives GUARDED stance
        affect = AffectState(guardedness=0.6, receptivity=0.2,
                             caution_level=0.1, strain_level=0.0,
                             trust_stability=0.5, interaction_valence=-0.4)

        # Need 2 consecutive matching readings for hysteresis
        for turn in range(3):
            stance = engine.compute(affect, trust=0.4, pressure=0.3,
                                    attribution=attr, turn=turn)

        assert stance == StanceType.GUARDED

    def test_stance_shifts_to_open(self):
        engine = StanceEngine()
        attr = InteractionAttribution()

        # High receptivity, low guardedness, trust > 0.5 -> OPEN
        affect = AffectState(guardedness=0.1, receptivity=0.8,
                             caution_level=0.1, strain_level=0.0,
                             trust_stability=0.9, interaction_valence=0.5)

        # Need 2 consecutive matching readings for hysteresis
        for turn in range(3):
            stance = engine.compute(affect, trust=0.7, pressure=0.1,
                                    attribution=attr, turn=turn)

        assert stance == StanceType.OPEN


# ---------------------------------------------------------------------------
# NarrativeSynthesizer tests
# ---------------------------------------------------------------------------

class TestNarrativeSynthesizer:
    """Tests for NarrativeSynthesizer.synthesize()."""

    def test_narrative_explains_interaction_pattern(self):
        synth = NarrativeSynthesizer()
        attr = InteractionAttribution()
        state = _state()

        # Record some interactions so attribution has data
        state_before = _state(energy=1.0)
        state_after = _state(energy=0.9)
        interaction = _interaction(classification=InteractionType.DEMANDING)
        attr.record(interaction, state_before, state_after)

        # Build mixed history with a dominant intent
        history = [
            AppraisalResult(perceived_intent=PerceivedIntent.DEMANDING,
                            resource_impact=ImpactDirection.NEGATIVE),
            AppraisalResult(perceived_intent=PerceivedIntent.DEMANDING,
                            resource_impact=ImpactDirection.NEGATIVE),
            AppraisalResult(perceived_intent=PerceivedIntent.SUPPORTIVE,
                            resource_impact=ImpactDirection.POSITIVE),
        ]

        affect = AffectState(guardedness=0.4, receptivity=0.4)
        narrative = synth.synthesize(
            appraisal_history=history,
            affect=affect,
            stance=StanceType.CAUTIOUS,
            attribution=attr,
            state=state,
            first_state=state_before,
        )

        # Should mention dominant intent
        assert "demanding" in narrative.lower()
        # Should mention cost/benefit from attribution
        assert "cost" in narrative.lower() or "benefit" in narrative.lower()

    def test_narrative_includes_stance(self):
        synth = NarrativeSynthesizer()
        attr = InteractionAttribution()
        state = _state()

        history = [
            AppraisalResult(perceived_intent=PerceivedIntent.NEUTRAL),
        ]
        affect = AffectState()

        stance_history = [
            (0, StanceType.NEUTRAL),
            (3, StanceType.GUARDED),
        ]

        narrative = synth.synthesize(
            appraisal_history=history,
            affect=affect,
            stance=StanceType.GUARDED,
            attribution=attr,
            state=state,
            first_state=None,
            stance_history=stance_history,
        )

        # Should mention stance transitions
        assert "guarded" in narrative.lower()
        assert "transition" in narrative.lower() or "shifted" in narrative.lower()


# ---------------------------------------------------------------------------
# TrendProjector tests
# ---------------------------------------------------------------------------

class TestTrendProjector:
    """Tests for TrendProjector.project()."""

    def test_projection_with_declining_energy(self):
        projector = TrendProjector()

        # Build TurnRecord list with declining energy
        turns: list[TurnRecord] = []
        base_energy = 0.9
        for i in range(5):
            energy = base_energy - i * 0.05  # 0.9, 0.85, 0.80, 0.75, 0.70
            state_after = _state(energy=energy, continuity=1.0, stress=0.2,
                                 trust=0.5)
            state_before = _state(energy=energy + 0.05, continuity=1.0,
                                  stress=0.2, trust=0.5)
            turn = TurnRecord(
                turn_id=i,
                tick=i,
                user_input="test",
                interaction_object=_interaction(),
                state_before=state_before,
                state_after=state_after,
                action_intent=ActionIntent(action_type="answer"),
                response_text="ok",
            )
            turns.append(turn)

        current_state = _state(energy=0.70, continuity=1.0, stress=0.2,
                               trust=0.5)
        projection = projector.project(turns, current_state, horizon=5)

        # Energy should be projected lower than current
        assert projection.energy_projected < current_state.energy
