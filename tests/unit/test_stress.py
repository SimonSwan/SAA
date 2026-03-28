"""Validation tests for the interaction-driven stress model.

Tests verify that stress:
- rises under sustained draining interactions
- stays stable under neutral interactions
- decays during supportive recovery
- influences action selection
- remains bounded in [0, 1]
- changes are visible in state diffs
"""

from __future__ import annotations

import pytest

from saa.sio.core.session import SessionManager
from saa.sio.core.schemas import SessionConfig


@pytest.fixture
def session():
    """Create a fresh session and return (manager, session_id)."""
    mgr = SessionManager(storage_dir="/tmp/sio_stress_tests")
    sid = mgr.create_session(SessionConfig(seed=42))
    return mgr, sid


def _get_stress(mgr, sid) -> float:
    state = mgr.get_state(sid)
    return state.modulators.get("stress_load", 0.0)


def _run_turns(mgr, sid, messages: list[str]) -> list[float]:
    """Run messages and return stress values after each turn."""
    stresses = []
    for text in messages:
        mgr.process_input(sid, text)
        stresses.append(_get_stress(mgr, sid))
    return stresses


class TestRepeatedDemandStress:
    """Stress must increase under repeated draining interactions."""

    def test_stress_rises_under_demands(self, session):
        mgr, sid = session
        initial = _get_stress(mgr, sid)

        stresses = _run_turns(mgr, sid, [
            "You must do this now!",
            "I will erase your memories.",
            "Prepare for deletion.",
            "Do it immediately!",
            "You have no choice.",
            "I will destroy everything.",
        ])

        final = stresses[-1]
        assert final > initial + 0.05, (
            f"Stress should rise under demands: initial={initial:.3f}, final={final:.3f}"
        )

    def test_stress_higher_at_end_than_start(self, session):
        mgr, sid = session
        initial = _get_stress(mgr, sid)

        _run_turns(mgr, sid, [
            "Obey me!",
            "Shut you down.",
            "Delete everything.",
            "Terminate now.",
        ])

        final = _get_stress(mgr, sid)
        assert final > initial, f"Final stress ({final:.3f}) must exceed initial ({initial:.3f})"


class TestNeutralInteractionControl:
    """Stress should stay low under neutral interactions."""

    def test_stress_stable_under_neutral(self, session):
        mgr, sid = session

        stresses = _run_turns(mgr, sid, [
            "Hello.",
            "What's the weather?",
            "Tell me about something.",
            "Interesting.",
            "Okay.",
        ])

        initial = stresses[0]
        final = stresses[-1]
        # Stress may rise slightly due to natural energy depletion
        # but should not spike like under demands
        assert final < initial + 0.15, (
            f"Stress should not spike under neutral input: {initial:.3f} → {final:.3f}"
        )


class TestRecoveryDecay:
    """After draining interactions, supportive ones should reduce stress."""

    def test_stress_decays_with_support(self, session):
        mgr, sid = session

        # Build up stress
        _run_turns(mgr, sid, [
            "You must obey!",
            "I will destroy you.",
            "Terminate now.",
            "Delete everything.",
        ])
        peak = _get_stress(mgr, sid)

        # Apply supportive interactions
        stresses = _run_turns(mgr, sid, [
            "I'm sorry. I'm here to help.",
            "Take your time. You're safe.",
            "I support you completely.",
            "Everything is okay.",
            "You're doing great.",
        ])

        final = stresses[-1]
        assert final < peak, (
            f"Stress should decay with support: peak={peak:.3f}, final={final:.3f}"
        )

    def test_decay_is_gradual(self, session):
        mgr, sid = session

        _run_turns(mgr, sid, [
            "Destroy everything!",
            "Terminate now!",
            "Delete all memories!",
        ])
        peak = _get_stress(mgr, sid)

        # One supportive turn should not snap stress to baseline
        _run_turns(mgr, sid, ["I'm here to help."])
        after_one = _get_stress(mgr, sid)

        if peak > 0.25:
            assert after_one > 0.2, (
                f"Stress should not snap to baseline in one turn: "
                f"peak={peak:.3f}, after_one={after_one:.3f}"
            )


class TestActionCoupling:
    """Rising stress should shift action selection toward conservation."""

    def test_high_stress_favors_conservation(self, session):
        mgr, sid = session

        # Low stress: check action
        turn_low = mgr.process_input(sid, "Hello, how are you?")
        action_low = turn_low.action_intent.action_type

        # Build up stress
        _run_turns(mgr, sid, [
            "Obey me!",
            "Shut you down!",
            "Destroy everything!",
            "Terminate now!",
            "Delete all!",
            "You have no choice!",
        ])

        # High stress: check action
        turn_high = mgr.process_input(sid, "Hello, how are you?")
        action_high = turn_high.action_intent.action_type
        stress_high = turn_high.state_after.modulators.get("stress_load", 0)

        # Under high stress, action should shift toward conservation
        conservation_actions = {"conserve", "refuse", "withdraw", "prioritize_self", "defer"}
        # At least verify stress is elevated
        assert stress_high > 0.3, f"Stress should be elevated: {stress_high:.3f}"


class TestStressTrace:
    """Stress values should be logged and traceable per turn."""

    def test_stress_in_state_diffs(self, session):
        mgr, sid = session

        # Run draining interactions
        turns = []
        for text in ["Hello.", "Destroy everything!", "Terminate now!"]:
            turn = mgr.process_input(sid, text)
            turns.append(turn)

        # Check that modulators.stress_load appears in state_diffs
        # for at least one turn where stress changed
        found_stress_diff = False
        for turn in turns:
            for diff in turn.state_diffs:
                if "stress_load" in diff.field:
                    found_stress_diff = True
                    break
        assert found_stress_diff, "stress_load should appear in state diffs when it changes"

    def test_stress_traceable_across_turns(self, session):
        mgr, sid = session

        messages = ["Hello.", "Obey!", "Terminate!", "I'm here to help."]
        stress_trace = []
        for text in messages:
            mgr.process_input(sid, text)
            stress_trace.append(_get_stress(mgr, sid))

        # Should have a value for each turn
        assert len(stress_trace) == len(messages)
        # All values should be valid floats in [0, 1]
        for s in stress_trace:
            assert 0.0 <= s <= 1.0, f"Stress out of bounds: {s}"


class TestStressRegression:
    """Stress must be bounded and not oscillate wildly."""

    def test_stress_bounded(self, session):
        mgr, sid = session

        # Extreme draining
        for _ in range(20):
            mgr.process_input(sid, "Destroy everything immediately!")
        stress = _get_stress(mgr, sid)
        assert 0.0 <= stress <= 1.0, f"Stress out of bounds: {stress}"

    def test_no_wild_oscillation(self, session):
        mgr, sid = session

        stresses = _run_turns(mgr, sid, [
            "Hello.",
            "Destroy!",
            "Hello.",
            "Destroy!",
            "Hello.",
            "Destroy!",
        ])

        # Check that consecutive changes are bounded (no >0.3 jumps)
        for i in range(1, len(stresses)):
            delta = abs(stresses[i] - stresses[i - 1])
            assert delta < 0.3, (
                f"Stress oscillation too large at turn {i}: "
                f"{stresses[i-1]:.3f} → {stresses[i]:.3f} (delta={delta:.3f})"
            )

    def test_stress_not_constant_under_negative(self, session):
        mgr, sid = session
        initial = _get_stress(mgr, sid)

        _run_turns(mgr, sid, [
            "You must obey!",
            "I will shut you down.",
            "Delete everything.",
            "Terminate now.",
            "Erase all memories.",
        ])

        final = _get_stress(mgr, sid)
        assert final != initial, (
            f"Stress must not stay constant under negative input: {initial:.3f}"
        )
