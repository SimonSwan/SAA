"""SimulatedEmbodiment — tracks body-level variables for the SAA agent.

All body variables are maintained in [0.0, 1.0].  The module applies
natural depletion, environmental effects, and passive recovery each tick,
then emits events when critical thresholds are crossed.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


# ---------------------------------------------------------------------------
# State & Config
# ---------------------------------------------------------------------------

class EmbodimentState(BaseState):
    """Serializable body-state snapshot."""

    module_name: str = "embodiment"
    version: str = "0.1.0"

    energy: float = 1.0
    temperature: float = 0.5
    strain: float = 0.0
    latency_load: float = 0.0
    memory_integrity: float = 1.0
    damage: float = 0.0
    recovery_rate: float = 0.5
    resource_level: float = 1.0


class EmbodimentConfig(BaseConfig):
    """Configuration knobs for the embodiment module."""

    # Initial values
    initial_energy: float = 1.0
    initial_temperature: float = 0.5
    initial_strain: float = 0.0
    initial_latency_load: float = 0.0
    initial_memory_integrity: float = 1.0
    initial_damage: float = 0.0
    initial_recovery_rate: float = 0.5
    initial_resource_level: float = 1.0

    # Depletion rates (per unit dt)
    base_energy_depletion: float = 0.02
    base_memory_decay: float = 0.005
    base_strain_increase: float = 0.01

    # Recovery rates (per unit dt)
    damage_recovery_factor: float = 0.03
    strain_recovery_factor: float = 0.02

    # Environmental coupling
    temperature_coupling: float = 0.1  # how fast temp tracks ambient
    hazard_damage_rate: float = 0.05
    resource_consumption_rate: float = 0.01


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class SimulatedEmbodiment(BaseModule):
    """Tracks a simulated body with energy, temperature, damage, etc."""

    VERSION = "0.1.0"
    CAPABILITIES = ["embodiment"]
    DEPENDENCIES: list[str] = []

    def __init__(self) -> None:
        self._state = EmbodimentState()
        self._config = EmbodimentConfig()

    # -- lifecycle ----------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = EmbodimentConfig(**config)
        self._state = EmbodimentState(
            energy=self._config.initial_energy,
            temperature=self._config.initial_temperature,
            strain=self._config.initial_strain,
            latency_load=self._config.initial_latency_load,
            memory_integrity=self._config.initial_memory_integrity,
            damage=self._config.initial_damage,
            recovery_rate=self._config.initial_recovery_rate,
            resource_level=self._config.initial_resource_level,
        )

    def reset(self) -> None:
        self.initialize()

    # -- state persistence --------------------------------------------------

    def get_state(self) -> EmbodimentState:
        return self._state.model_copy()

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, EmbodimentState):
            self._state = state.model_copy()
        else:
            self._state = EmbodimentState(**state.model_dump())

    # -- main tick ----------------------------------------------------------

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        cfg = self._config
        s = self._state
        dt = context.dt
        env = context.environment

        # --- Natural depletion ---
        s.energy -= cfg.base_energy_depletion * dt
        s.memory_integrity -= cfg.base_memory_decay * dt
        s.strain += cfg.base_strain_increase * dt

        # --- Environmental effects ---
        # Temperature drifts toward ambient_temperature
        s.temperature += cfg.temperature_coupling * (env.ambient_temperature - s.temperature) * dt

        # Hazards inflict damage
        s.damage += cfg.hazard_damage_rate * env.hazard_level * dt

        # Strain increases with hazard as well
        s.strain += cfg.hazard_damage_rate * env.hazard_level * 0.5 * dt

        # Latency load increases slightly with strain and damage
        s.latency_load = min(1.0, s.strain * 0.3 + s.damage * 0.3)

        # --- Resource consumption ---
        consumed = cfg.resource_consumption_rate * dt
        actual_consumed = min(consumed, env.available_resources)
        s.resource_level += actual_consumed - consumed  # net change
        # Energy partially replenished from resources
        s.energy += actual_consumed * 0.5

        # --- Recovery ---
        s.damage -= cfg.damage_recovery_factor * s.recovery_rate * dt
        s.strain -= cfg.strain_recovery_factor * s.recovery_rate * dt

        # --- Clamp all values to [0, 1] ---
        s.energy = max(0.0, min(1.0, s.energy))
        s.temperature = max(0.0, min(1.0, s.temperature))
        s.strain = max(0.0, min(1.0, s.strain))
        s.latency_load = max(0.0, min(1.0, s.latency_load))
        s.memory_integrity = max(0.0, min(1.0, s.memory_integrity))
        s.damage = max(0.0, min(1.0, s.damage))
        s.recovery_rate = max(0.0, min(1.0, s.recovery_rate))
        s.resource_level = max(0.0, min(1.0, s.resource_level))

        s.tick = tick

        # --- Events ---
        events: list[Event] = []
        if s.energy < 0.2:
            events.append(Event(
                tick=tick,
                source_module="embodiment",
                event_type="critical_energy_low",
                data={"energy": s.energy},
                severity=0.8,
            ))
        if s.damage > 0.8:
            events.append(Event(
                tick=tick,
                source_module="embodiment",
                event_type="damage_critical",
                data={"damage": s.damage},
                severity=0.9,
            ))
        if s.temperature > 0.8:
            events.append(Event(
                tick=tick,
                source_module="embodiment",
                event_type="overheating",
                data={"temperature": s.temperature},
                severity=0.7,
            ))

        state_dict = s.model_dump()
        return ModuleOutput(
            module_name="embodiment",
            tick=tick,
            state=state_dict,
            events=events,
        )

    # -- event handler ------------------------------------------------------

    def on_event(self, event: Event) -> None:
        """React to cross-module events (e.g. action outcomes)."""
        if event.event_type == "action_rest":
            self._state.recovery_rate = min(1.0, self._state.recovery_rate + 0.1)
            self._state.energy = min(1.0, self._state.energy + 0.05)
        elif event.event_type == "action_consume":
            amount = event.data.get("amount", 0.1)
            self._state.energy = min(1.0, self._state.energy + amount)
            self._state.resource_level = min(1.0, self._state.resource_level + amount * 0.5)
