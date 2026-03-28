"""Basic survival experiment — demonstrates SAA agent under resource pressure.

This experiment:
1. Creates a world with limited resources and a stabilizing social agent
2. Runs the agent for 80 ticks with a resource shock at tick 30
3. Prints key metrics every 10 ticks
4. Shows how internal state affects behavior over time

Run: python experiments/basic_survival.py
"""

import sys
sys.path.insert(0, ".")

from saa.core.types import EnvironmentState
from saa.simulations.runner import build_default_engine
from saa.simulations.world import SimulationWorld, WorldAgent, WorldConfig


def main():
    # Configure world
    config = WorldConfig(
        initial_resources=0.7,
        resource_regen_rate=0.03,
        resource_depletion_rate=0.02,
        base_hazard=0.1,
        hazard_variance=0.05,
        social_agents=[
            WorldAgent(agent_id="companion", disposition="stabilizing", reliability=0.9),
        ],
        random_seed=42,
    )
    world = SimulationWorld(config)

    # Schedule events
    world.schedule_event(30, "resource_shock", {"amount": 0.4})
    world.schedule_event(50, "hazard_spike", {"level": 0.6})
    world.schedule_event(60, "hazard_spike", {"level": 0.1})  # recovery

    # Build engine
    engine, bus = build_default_engine()
    engine.initialize_modules()

    print("=" * 70)
    print("Swan Affective Architecture — Basic Survival Experiment")
    print("=" * 70)
    print()
    print(f"{'Tick':>4} {'Energy':>7} {'Viabil':>7} {'Stress':>7} {'Grief':>7} {'Action':>12} {'Events':>7}")
    print("-" * 70)

    NUM_TICKS = 80

    for i in range(NUM_TICKS):
        env = world.step()
        engine.set_environment(env)
        ctx = engine.step()

        # Extract metrics
        energy = ctx.embodiment_state.get("energy", 0) if ctx.embodiment_state else 0
        viability = ctx.homeostatic_error.get("viability", 0) if ctx.homeostatic_error else 0
        stress = 0
        grief = 0
        if ctx.modulator_state:
            mods = ctx.modulator_state.get("modulators", {})
            stress = mods.get("stress_load", 0)
            grief = mods.get("grief_persistence", 0)
        action = "?"
        if ctx.action_result:
            last = ctx.action_result.get("last_action", {})
            action = last.get("action", "?")

        event_count = len(ctx.events)

        # Print every 5 ticks
        if (i + 1) % 5 == 0 or i == 0:
            print(f"{ctx.tick:>4} {energy:>7.3f} {viability:>7.3f} {stress:>7.3f} {grief:>7.3f} {action:>12} {event_count:>7}")

    print("-" * 70)
    print()

    # Summary
    print("=== Experiment Summary ===")
    print(f"Total ticks: {NUM_TICKS}")
    print(f"Total events: {len(bus.history)}")

    # Final state
    state = engine.save_state()
    if "embodiment" in state:
        print(f"Final energy: {state['embodiment'].get('energy', '?'):.3f}")
    if "homeostasis" in state:
        print(f"Final viability: {state['homeostasis'].get('viability', '?'):.3f}")
    if "neuromodulation" in state:
        mods = state["neuromodulation"].get("modulators", {})
        print(f"Final stress: {mods.get('stress_load', '?'):.3f}")
        print(f"Final curiosity: {mods.get('curiosity_drive', '?'):.3f}")
    if "self_model" in state:
        print(f"Final continuity: {state['self_model'].get('continuity_score', '?'):.3f}")

    # Event type summary
    event_types: dict[str, int] = {}
    for e in bus.history:
        event_types[e.event_type] = event_types.get(e.event_type, 0) + 1
    print(f"\nEvent distribution:")
    for etype, count in sorted(event_types.items(), key=lambda x: -x[1]):
        print(f"  {etype}: {count}")


if __name__ == "__main__":
    main()
