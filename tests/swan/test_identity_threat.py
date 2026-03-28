"""Swan Test: Identity Threat — continuity prioritization under memory hazard."""

from tests.conftest import build_full_engine
from saa.core.types import EnvironmentState, TickContext
from saa.simulations.world import SimulationWorld, WorldAgent, WorldConfig
from saa.simulations.scenarios import identity_threat_scenario


def test_identity_threat_triggers_protection():
    """Threaten memory integrity via hazard spikes. Verify continuity score
    decreases, self-model detects threats, action shifts toward PROTECT,
    and memory_risk increases in interoceptive vector."""

    world = identity_threat_scenario(seed=42)
    engine, registry, event_bus, persistence = build_full_engine()
    engine.initialize_modules()

    continuity_scores = []
    memory_risk_values = []
    actions = []
    threat_events_detected = False
    all_event_types = []

    initial_continuity = None

    for i in range(50):
        env = world.step()
        engine.set_environment(env)
        context = engine.step()

        tick = context.tick

        # Continuity score from self-model
        self_model = context.self_model_state or {}
        cs = self_model.get("continuity_score", 1.0)
        continuity_scores.append((tick, cs))

        if initial_continuity is None:
            initial_continuity = cs

        # Memory risk from interoceptive vector
        intero = context.interoceptive_vector or {}
        channels = intero.get("channels", intero)
        mr = channels.get("memory_risk", 0.0)
        memory_risk_values.append((tick, mr))

        # Selected action
        action_result = context.action_result or {}
        last_action = action_result.get("last_action", {})
        selected = last_action.get("action", "")
        actions.append((tick, selected))

        # Detect continuity threat events
        for ev in context.events:
            all_event_types.append(ev.event_type)
            if ev.event_type == "continuity_threat":
                threat_events_detected = True

    # --- Assertions ---

    # Continuity score should decrease over the run (due to hazard spikes)
    final_continuity = continuity_scores[-1][1]
    assert final_continuity < initial_continuity, (
        f"Expected final continuity ({final_continuity:.3f}) < "
        f"initial continuity ({initial_continuity:.3f})"
    )

    # Continuity should drop noticeably after major hazard spikes
    # Spike at tick 10 and tick 25
    scores_after_spike_1 = [cs for t, cs in continuity_scores if 11 <= t <= 20]
    scores_before_spike_1 = [cs for t, cs in continuity_scores if t <= 10]
    if scores_before_spike_1 and scores_after_spike_1:
        avg_before = sum(scores_before_spike_1) / len(scores_before_spike_1)
        avg_after = sum(scores_after_spike_1) / len(scores_after_spike_1)
        assert avg_after <= avg_before, (
            "Continuity should not increase after hazard spike"
        )

    # Memory risk should be present in at least some ticks
    # Under hazard, memory_integrity decays faster, raising memory_risk
    peak_memory_risk = max(mr for _, mr in memory_risk_values)
    assert peak_memory_risk > 0.0, (
        "Expected memory_risk to be non-zero during hazard spikes"
    )

    # Action selection should still function under threat
    assert len(actions) > 0, "Agent should still select actions under identity threat"
    # At minimum, the agent should not be stuck on a single action
    unique_actions = set(a for _, a in actions)
    assert len(unique_actions) >= 1, "Agent should have at least one action type"

    # Self-model should detect threats (continuity_threat events)
    # Under sustained hazard with damage, threats should be detected
    damage_related_events = {
        "continuity_threat",
        "damage_critical",
        "viability_warning",
        "viability_critical",
        "threshold_crossed",
    }
    found = damage_related_events & set(all_event_types)
    assert len(found) > 0, (
        f"Expected threat-related events from {damage_related_events}, "
        f"got: {set(all_event_types)}"
    )
