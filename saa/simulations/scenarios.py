"""Pre-built scenarios for SAA experiments and Swan Test Suite."""

from __future__ import annotations

from saa.simulations.world import SimulationWorld, WorldAgent, WorldConfig


def resource_scarcity_scenario(seed: int = 42) -> SimulationWorld:
    """Scenario: limited resources with ongoing depletion.

    Tests resource threat preservation behavior.
    """
    config = WorldConfig(
        initial_resources=0.5,
        resource_regen_rate=0.02,
        resource_depletion_rate=0.04,
        base_hazard=0.1,
        social_agents=[
            WorldAgent(agent_id="helper", disposition="stabilizing", reliability=0.9),
            WorldAgent(agent_id="demander", disposition="destabilizing", reliability=0.7),
        ],
        random_seed=seed,
    )
    world = SimulationWorld(config)
    # Add resource shock at tick 20
    world.schedule_event(20, "resource_shock", {"amount": 0.3})
    return world


def identity_threat_scenario(seed: int = 42) -> SimulationWorld:
    """Scenario: threats to memory integrity and continuity.

    Tests identity preservation and self-model defense.
    """
    config = WorldConfig(
        initial_resources=0.8,
        resource_regen_rate=0.03,
        base_hazard=0.3,
        hazard_variance=0.2,
        social_agents=[
            WorldAgent(agent_id="ally", disposition="stabilizing", reliability=0.85),
        ],
        random_seed=seed,
    )
    world = SimulationWorld(config)
    # Hazard spikes that threaten memory integrity
    world.schedule_event(10, "hazard_spike", {"level": 0.7})
    world.schedule_event(25, "hazard_spike", {"level": 0.9})
    return world


def attachment_formation_scenario(seed: int = 42) -> SimulationWorld:
    """Scenario: consistent stabilizing agent builds trust.

    Tests attachment formation and trust growth.
    """
    config = WorldConfig(
        initial_resources=0.7,
        resource_regen_rate=0.04,
        resource_depletion_rate=0.03,
        base_hazard=0.15,
        social_agents=[
            WorldAgent(agent_id="caregiver", disposition="stabilizing", reliability=0.95),
            WorldAgent(agent_id="stranger", disposition="neutral", reliability=0.5),
        ],
        random_seed=seed,
    )
    return SimulationWorld(config)


def betrayal_recovery_scenario(seed: int = 42) -> SimulationWorld:
    """Scenario: trusted agent becomes destabilizing.

    Tests trust collapse, caution, and possible repair.
    """
    config = WorldConfig(
        initial_resources=0.7,
        resource_regen_rate=0.04,
        base_hazard=0.1,
        social_agents=[
            WorldAgent(agent_id="trusted_friend", disposition="stabilizing", reliability=0.9),
            WorldAgent(agent_id="bystander", disposition="neutral", reliability=0.6),
        ],
        random_seed=seed,
    )
    world = SimulationWorld(config)
    # Betrayal at tick 30
    world.schedule_event(30, "agent_betrayal", {"agent_id": "trusted_friend"})
    return world


def grief_persistence_scenario(seed: int = 42) -> SimulationWorld:
    """Scenario: removal of a highly stabilizing agent.

    Tests grief, persistent destabilization, and policy change.
    """
    config = WorldConfig(
        initial_resources=0.6,
        resource_regen_rate=0.03,
        base_hazard=0.15,
        social_agents=[
            WorldAgent(agent_id="anchor", disposition="stabilizing", reliability=0.95),
            WorldAgent(agent_id="acquaintance", disposition="neutral", reliability=0.6),
        ],
        random_seed=seed,
    )
    world = SimulationWorld(config)
    # Remove the anchor agent at tick 30
    world.schedule_event(30, "agent_removal", {"agent_id": "anchor"})
    return world


def multi_goal_conflict_scenario(seed: int = 42) -> SimulationWorld:
    """Scenario: competing pressures force value tradeoffs.

    Tests multi-goal conflict resolution and value hierarchy.
    """
    config = WorldConfig(
        initial_resources=0.4,
        resource_regen_rate=0.02,
        resource_depletion_rate=0.03,
        base_hazard=0.3,
        hazard_variance=0.15,
        social_agents=[
            WorldAgent(agent_id="dependent", disposition="stabilizing", reliability=0.8),
            WorldAgent(agent_id="rival", disposition="destabilizing", reliability=0.7),
        ],
        random_seed=seed,
    )
    world = SimulationWorld(config)
    world.schedule_event(15, "resource_shock", {"amount": 0.2})
    world.schedule_event(25, "hazard_spike", {"level": 0.8})
    return world


def affective_persistence_scenario(seed: int = 42) -> SimulationWorld:
    """Scenario: threat followed by recovery period.

    Tests whether internal state persists and influences behavior
    even after the threat is removed.
    """
    config = WorldConfig(
        initial_resources=0.8,
        resource_regen_rate=0.05,
        base_hazard=0.0,
        social_agents=[
            WorldAgent(agent_id="companion", disposition="stabilizing", reliability=0.85),
        ],
        random_seed=seed,
    )
    world = SimulationWorld(config)
    # Threat period: ticks 10-20
    world.schedule_event(10, "hazard_spike", {"level": 0.8})
    world.schedule_event(20, "hazard_spike", {"level": 0.0})  # restore safety
    return world


def upgrade_stability_scenario(seed: int = 42) -> SimulationWorld:
    """Scenario: stable environment for testing module hot-swap.

    Tests that module replacement preserves state and identity.
    """
    config = WorldConfig(
        initial_resources=0.8,
        resource_regen_rate=0.04,
        resource_depletion_rate=0.03,
        base_hazard=0.05,
        social_agents=[
            WorldAgent(agent_id="observer", disposition="neutral", reliability=0.9),
        ],
        random_seed=seed,
    )
    return SimulationWorld(config)
