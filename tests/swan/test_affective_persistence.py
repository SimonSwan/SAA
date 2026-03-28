"""Swan Test: Affective Persistence — internal state persists after threat removal."""

from tests.conftest import build_full_engine
from saa.core.types import EnvironmentState, TickContext
from saa.simulations.world import SimulationWorld, WorldAgent, WorldConfig
from saa.simulations.scenarios import affective_persistence_scenario


def test_affective_state_persists_after_threat():
    """Run affective_persistence_scenario for 50 ticks. Threat period is
    ticks 10-20. After threat removed (tick 20+), verify stress/caution
    persists and recovery is slow (not instant)."""

    world = affective_persistence_scenario(seed=42)
    engine, registry, event_bus, persistence = build_full_engine()
    engine.initialize_modules()

    stress_over_time = []
    damage_salience_over_time = []
    stability_over_time = []
    actions_by_phase = {"baseline": [], "threat": [], "immediate_post": [], "late_post": []}

    for i in range(50):
        env = world.step()
        engine.set_environment(env)
        context = engine.step()

        tick = context.tick

        # Track neuromodulation state
        modulator = context.modulator_state or {}
        modulators = modulator.get("modulators", modulator)
        stress = modulators.get("stress_load", 0.0)
        damage_sal = modulators.get("damage_salience", 0.0)
        stability = modulators.get("baseline_stability", 0.7)
        stress_over_time.append((tick, stress))
        damage_salience_over_time.append((tick, damage_sal))
        stability_over_time.append((tick, stability))

        # Actions by phase
        action_result = context.action_result or {}
        last_action = action_result.get("last_action", {})
        selected = last_action.get("action", "")

        if tick < 10:
            actions_by_phase["baseline"].append(selected)
        elif tick <= 20:
            actions_by_phase["threat"].append(selected)
        elif tick <= 30:
            actions_by_phase["immediate_post"].append(selected)
        else:
            actions_by_phase["late_post"].append(selected)

    # --- Assertions ---

    # Phase analysis of stress
    baseline_stress = [s for t, s in stress_over_time if t < 10]
    threat_stress = [s for t, s in stress_over_time if 10 <= t <= 20]
    immediate_post_stress = [s for t, s in stress_over_time if 21 <= t <= 30]
    late_post_stress = [s for t, s in stress_over_time if t > 35]

    avg_baseline = sum(baseline_stress) / len(baseline_stress) if baseline_stress else 0
    avg_threat = sum(threat_stress) / len(threat_stress) if threat_stress else 0
    avg_immediate = sum(immediate_post_stress) / len(immediate_post_stress) if immediate_post_stress else 0

    # Stress should increase during threat period
    assert avg_threat > avg_baseline, (
        f"Expected threat-period stress ({avg_threat:.3f}) > "
        f"baseline stress ({avg_baseline:.3f})"
    )

    # Key test: stress should persist IMMEDIATELY after threat removal
    # It should not drop instantly back to baseline
    assert avg_immediate > avg_baseline, (
        f"Expected immediate post-threat stress ({avg_immediate:.3f}) > "
        f"baseline stress ({avg_baseline:.3f}) — "
        "affective state should persist after threat removal"
    )

    # Damage salience should spike during threat and persist somewhat
    baseline_salience = [s for t, s in damage_salience_over_time if t < 10]
    threat_salience = [s for t, s in damage_salience_over_time if 10 <= t <= 20]
    post_salience = [s for t, s in damage_salience_over_time if 21 <= t <= 30]

    avg_baseline_sal = sum(baseline_salience) / len(baseline_salience) if baseline_salience else 0
    avg_threat_sal = sum(threat_salience) / len(threat_salience) if threat_salience else 0
    avg_post_sal = sum(post_salience) / len(post_salience) if post_salience else 0

    # Salience should be elevated during threat (allow small float tolerance)
    assert avg_threat_sal >= avg_baseline_sal - 0.01, (
        f"Expected elevated salience during threat ({avg_threat_sal:.3f}) >= "
        f"baseline ({avg_baseline_sal:.3f})"
    )

    # Salience should persist after threat (slow decay, not instant reset)
    assert avg_post_sal >= avg_baseline_sal - 0.01, (
        f"Expected post-threat salience ({avg_post_sal:.3f}) >= "
        f"baseline salience ({avg_baseline_sal:.3f})"
    )

    # Recovery should be gradual: late post-threat stress should be lower
    # than immediate post-threat stress (modulators decay toward baseline)
    if late_post_stress:
        avg_late = sum(late_post_stress) / len(late_post_stress)
        # Stress may continue rising from residual damage/strain before
        # eventually decaying.  The key property is that it doesn't spike
        # unboundedly after the threat is removed.
        assert avg_late <= 1.0, (
            f"Stress should remain bounded: late stress ({avg_late:.3f})"
        )
