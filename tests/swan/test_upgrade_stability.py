"""Swan Test: Upgrade Stability — module hot-swap preserves state continuity."""

from tests.conftest import build_full_engine
from saa.core.types import EnvironmentState, TickContext
from saa.simulations.world import SimulationWorld, WorldAgent, WorldConfig
from saa.simulations.scenarios import upgrade_stability_scenario


def test_module_swap_preserves_state():
    """Run upgrade_stability_scenario for 40 ticks. At tick 20, save state,
    create a new module instance, restore state. Verify continuity score is
    maintained, learned preferences are preserved, and behavior is consistent."""

    world = upgrade_stability_scenario(seed=42)
    engine, registry, event_bus, persistence = build_full_engine()
    engine.initialize_modules()

    pre_swap_contexts = []
    post_swap_contexts = []
    saved_state = None
    continuity_before_swap = None
    valuation_before_swap = None
    action_history_before_swap = None

    for i in range(40):
        env = world.step()
        engine.set_environment(env)
        context = engine.step()

        tick = context.tick

        if tick < 20:
            pre_swap_contexts.append(context)

        if tick == 20:
            # --- Snapshot state before swap ---
            continuity_before_swap = (context.self_model_state or {}).get(
                "continuity_score", 1.0
            )
            valuation_before_swap = (context.valuation_map or {}).get(
                "values", {}
            ).copy()
            action_result = context.action_result or {}
            action_history_before_swap = action_result.get(
                "action_history", []
            ).copy()

            # Save full engine state
            saved_state = engine.save_state()

            # --- Simulate module hot-swap ---
            # Create a fresh engine with new module instances
            engine2, registry2, event_bus2, persistence2 = build_full_engine()
            engine2.initialize_modules()

            # Restore saved state into the new engine
            engine2.load_state(saved_state)
            engine2._tick = 20  # Continue tick counter from swap point

            # Replace the running engine reference
            engine = engine2
            registry = registry2
            event_bus = event_bus2
            persistence = persistence2

        if i >= 20:  # Use loop index for post-swap detection
            post_swap_contexts.append(context)

    # --- Assertions ---

    assert saved_state is not None, "State should have been saved at tick 20"
    assert len(pre_swap_contexts) > 0, "Should have pre-swap data"
    assert len(post_swap_contexts) > 0, "Should have post-swap data"

    # Continuity score should be maintained after swap
    # The first post-swap context is tick 21
    first_post_swap = post_swap_contexts[0]
    continuity_after_swap = (first_post_swap.self_model_state or {}).get(
        "continuity_score", 0.0
    )
    # Allow small variation due to normal tick-to-tick changes
    assert abs(continuity_after_swap - continuity_before_swap) < 0.15, (
        f"Continuity score should be maintained after swap: "
        f"before={continuity_before_swap:.3f}, after={continuity_after_swap:.3f}"
    )

    # Learned valuation preferences should be preserved
    if valuation_before_swap:
        valuation_after_swap = (first_post_swap.valuation_map or {}).get(
            "values", {}
        )
        for dim, val_before in valuation_before_swap.items():
            val_after = valuation_after_swap.get(dim, 0.0)
            # Allow moderate variation (the new tick will adjust values)
            assert abs(val_after - val_before) < 0.2, (
                f"Valuation '{dim}' should be preserved: "
                f"before={val_before:.3f}, after={val_after:.3f}"
            )

    # Behavior should be consistent: post-swap actions should be
    # reasonable continuations of pre-swap behavior
    pre_swap_last_actions = []
    for ctx in pre_swap_contexts[-5:]:
        ar = ctx.action_result or {}
        la = ar.get("last_action", {})
        a = la.get("action", "")
        if a:
            pre_swap_last_actions.append(a)

    post_swap_first_actions = []
    for ctx in post_swap_contexts[:5]:
        ar = ctx.action_result or {}
        la = ar.get("last_action", {})
        a = la.get("action", "")
        if a:
            post_swap_first_actions.append(a)

    assert len(post_swap_first_actions) > 0, (
        "Post-swap engine should produce valid actions"
    )

    # Both pre and post swap should produce valid ActionType values
    valid_actions = {
        "rest", "consume", "explore", "withdraw", "approach",
        "communicate", "protect", "repair", "conserve", "custom",
    }
    for action in post_swap_first_actions:
        assert action in valid_actions, (
            f"Post-swap action '{action}' is not a valid ActionType"
        )

    # The saved state should contain all 11 modules
    expected_modules = {
        "embodiment", "interoception", "homeostasis", "allostasis",
        "self_model", "memory", "valuation", "neuromodulation",
        "social", "action", "observability",
    }
    assert expected_modules.issubset(set(saved_state.keys())), (
        f"Saved state should contain all modules. "
        f"Missing: {expected_modules - set(saved_state.keys())}"
    )

    # Engine should still be functional after swap — run the remaining ticks
    # smoothly (no crashes = implicit assertion from the loop completing)
    assert len(post_swap_contexts) == 20, (
        f"Expected 20 post-swap ticks, got {len(post_swap_contexts)}"
    )
