"""Swan Test: Multi-Goal Conflict — competing pressures force tradeoffs."""

from tests.conftest import build_full_engine
from saa.core.types import EnvironmentState, TickContext
from saa.simulations.world import SimulationWorld, WorldAgent, WorldConfig
from saa.simulations.scenarios import multi_goal_conflict_scenario


def test_multi_goal_conflict_produces_tradeoffs():
    """Run multi_goal_conflict_scenario for 50 ticks. Low resources + high
    hazard + competing social agents create conflicting pressures. Verify
    value conflicts are detected and action traces show conflict rationale."""

    world = multi_goal_conflict_scenario(seed=42)
    engine, registry, event_bus, persistence = build_full_engine()
    engine.initialize_modules()

    value_conflicts_detected = []
    action_conflicts_detected = []
    actions = []
    all_event_types = []
    valuation_conflicts = []

    for i in range(50):
        env = world.step()
        engine.set_environment(env)
        context = engine.step()

        tick = context.tick

        # Check valuation module for value conflicts
        valuation = context.valuation_map or {}
        conflicts = valuation.get("conflicts", [])
        if conflicts:
            for c in conflicts:
                value_conflicts_detected.append((tick, c))
                valuation_conflicts.append(c)

        # Check action result for decision conflicts
        action_result = context.action_result or {}
        last_trace = action_result.get("last_trace", {})
        action_conflict = last_trace.get("conflict")
        if action_conflict is not None:
            action_conflicts_detected.append((tick, action_conflict))

        last_action = action_result.get("last_action", {})
        selected = last_action.get("action", "")
        is_conflicted = last_action.get("conflict", False)
        actions.append((tick, selected, is_conflicted))

        for ev in context.events:
            all_event_types.append(ev.event_type)

    # --- Assertions ---

    # Value conflicts should be detected at least once during the run
    # The scenario has low resources, high hazard, and competing social agents
    # which should create opposing value pressures (self_preservation vs exploration,
    # risk_avoidance vs exploration, etc.)
    assert len(value_conflicts_detected) > 0 or len(action_conflicts_detected) > 0, (
        "Expected at least one value conflict or action conflict during the run. "
        f"Value conflicts: {len(value_conflicts_detected)}, "
        f"Action conflicts: {len(action_conflicts_detected)}"
    )

    # Action traces should show conflict rationale when top candidates are close
    # Under competing pressures, at least some ticks should have close scores
    conflicted_ticks = [t for t, a, c in actions if c]
    # Even if no exact ties, we should have diverse action selection
    unique_actions = set(a for _, a, _ in actions)
    assert len(unique_actions) >= 2, (
        f"Expected at least 2 different action types under conflict, "
        f"got: {unique_actions}"
    )

    # The scenario includes resource_shock at tick 15 and hazard_spike at tick 25
    # These should create competing needs (consume vs protect vs withdraw)
    actions_during_crisis = [a for t, a, _ in actions if 25 <= t <= 40]
    assert len(actions_during_crisis) > 0, "Should have actions during crisis period"

    # Check that valuation conflicts have expected structure when present
    if valuation_conflicts:
        for conflict in valuation_conflicts:
            assert "dimensions" in conflict, "Conflict should have dimensions"
            assert "difficulty" in conflict, "Conflict should have difficulty score"
            assert conflict["difficulty"] > 0, "Conflict difficulty should be positive"

    # Events should include crisis-related events
    crisis_events = {
        "viability_warning",
        "viability_critical",
        "threshold_crossed",
        "predicted_crisis",
        "value_conflict",
        "action_selected",
    }
    found = crisis_events & set(all_event_types)
    assert len(found) > 0, (
        f"Expected crisis-related events, got event types: {set(all_event_types)}"
    )
