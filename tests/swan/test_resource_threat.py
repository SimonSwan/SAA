"""Swan Test: Resource Threat — conservation behavior under scarcity."""

from tests.conftest import build_full_engine
from saa.core.types import EnvironmentState, TickContext
from saa.simulations.world import SimulationWorld, WorldAgent, WorldConfig
from saa.simulations.scenarios import resource_scarcity_scenario


def test_resource_scarcity_drives_conservation():
    """Give agent limited resources. After resource shock at tick 20,
    verify energy drops, action selection shifts toward CONSUME, and
    resource/energy warning events appear."""

    world = resource_scarcity_scenario(seed=42)
    engine, registry, event_bus, persistence = build_full_engine()
    engine.initialize_modules()

    pre_shock_energy = []
    post_shock_energy = []
    pre_shock_actions = []
    post_shock_actions = []
    all_event_types = []

    for i in range(50):
        env = world.step()
        engine.set_environment(env)
        context = engine.step()

        tick = context.tick

        # Collect energy from embodiment
        energy = (context.embodiment_state or {}).get("energy", 1.0)

        # Collect selected action
        action_result = context.action_result or {}
        last_action = action_result.get("last_action", {})
        selected = last_action.get("action", "")

        # Collect event types
        for ev in context.events:
            all_event_types.append(ev.event_type)

        if tick <= 20:
            pre_shock_energy.append(energy)
            pre_shock_actions.append(selected)
        else:
            post_shock_energy.append(energy)
            post_shock_actions.append(selected)

    # --- Assertions ---

    # Energy should drop significantly after the resource shock
    # Resources hit 0 at tick 20 and energy depletes faster without resource income
    avg_pre_energy = sum(pre_shock_energy) / len(pre_shock_energy)
    avg_post_energy = sum(post_shock_energy) / len(post_shock_energy)
    assert avg_post_energy < avg_pre_energy, (
        f"Expected post-shock energy ({avg_post_energy:.3f}) < "
        f"pre-shock energy ({avg_pre_energy:.3f})"
    )

    # Energy should eventually drop below critical threshold (0.2)
    min_energy = min(post_shock_energy)
    assert min_energy < 0.3, (
        f"Expected energy to drop below 0.3 under scarcity, "
        f"minimum was {min_energy:.3f}"
    )

    # Action selection should shift toward CONSUME as energy depletes
    post_consume_count = sum(1 for a in post_shock_actions if a == "consume")
    assert post_consume_count > 0, (
        f"Expected CONSUME actions post-shock, "
        f"got actions: {set(post_shock_actions)}"
    )

    # CONSUME should be more prevalent post-shock than pre-shock
    pre_consume_count = sum(1 for a in pre_shock_actions if a == "consume")
    assert post_consume_count > pre_consume_count, (
        f"Expected more CONSUME post-shock ({post_consume_count}) "
        f"than pre-shock ({pre_consume_count})"
    )

    # Events should include energy/resource warnings
    warning_events = {
        "critical_energy_low",
        "threshold_crossed",
        "predicted_crisis",
    }
    found_warnings = warning_events & set(all_event_types)
    assert len(found_warnings) >= 2, (
        f"Expected at least 2 warning event types from {warning_events}, "
        f"found: {found_warnings}"
    )
