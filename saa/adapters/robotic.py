from __future__ import annotations

"""Robotic embodiment adapter — stub for future hardware integration.

This adapter replaces SimulatedEmbodiment with real sensor data from
robotic hardware. When implemented, it should:

1. Read battery telemetry -> energy
2. Read thermal sensors -> temperature
3. Read motor load / wear sensors -> strain, damage
4. Read camera/environment sensors -> environment state
5. Translate actuator commands back to the robot

Interface contract:
- Must implement EmbodimentInterface
- Must produce BodyState-compatible output
- Must handle sensor noise, dropouts, and calibration
- Must support graceful degradation if sensors fail

Integration steps:
1. Subclass BaseModule (or EmbodimentInterface when available)
2. Initialize hardware connection in initialize()
3. Read real sensor values in update() instead of simulating them
4. Map hardware telemetry to normalized 0-1 body state variables
5. Register as "embodiment" in the ModuleRegistry to replace the default
"""

from saa.interfaces.base import BaseModule, BaseState
from saa.core.types import ModuleOutput, TickContext


class RoboticEmbodimentAdapter(BaseModule):
    """Stub adapter for robotic hardware telemetry.

    Replace the body of each method with actual hardware communication
    when integrating with a physical robot.
    """

    VERSION = "0.1.0-stub"
    CAPABILITIES = ["hardware_telemetry", "real_sensors", "actuator_control"]
    DEPENDENCIES = []

    def initialize(self, config=None):
        raise NotImplementedError(
            "RoboticEmbodimentAdapter requires hardware integration. "
            "Implement sensor connection setup here."
        )

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        raise NotImplementedError("Implement hardware sensor reading here.")

    def get_state(self) -> BaseState:
        return BaseState(module_name="robotic_embodiment", version=self.VERSION)

    def set_state(self, state: BaseState) -> None:
        pass

    def reset(self) -> None:
        pass
