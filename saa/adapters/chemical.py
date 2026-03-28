"""Chemical signaling adapter — stub for synthetic hormone / analog computation.

This adapter extends the neuromodulation layer with chemical-analog backends.
When implemented, it should:

1. Map synthetic modulators to simulated chemical concentrations
2. Support diffusion-based signaling models (slow spatial spread)
3. Model dynamic concentration fields with production/degradation kinetics
4. Interface with analog hardware or wet-lab chemical systems

Integration steps:
1. Subclass NeuromodulationInterface
2. Replace discrete modulator values with continuous concentration fields
3. Model reaction-diffusion dynamics for multi-modulator interaction
4. Support time-delayed signaling (chemicals diffuse, not instant)
5. Register as "neuromodulation" in ModuleRegistry to replace the default
"""

from saa.interfaces.base import BaseModule, BaseState
from saa.core.types import ModuleOutput, TickContext


class ChemicalSignalingAdapter(BaseModule):
    """Stub adapter for synthetic chemical signaling.

    Replace with actual chemical simulation or hardware interface.
    """

    VERSION = "0.1.0-stub"
    CAPABILITIES = ["chemical_signaling", "diffusion_model", "concentration_fields"]
    DEPENDENCIES = []

    def initialize(self, config=None):
        raise NotImplementedError(
            "ChemicalSignalingAdapter requires chemical simulation backend. "
            "Implement reaction-diffusion model or hardware connection here."
        )

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        raise NotImplementedError("Implement chemical concentration update here.")

    def get_state(self) -> BaseState:
        return BaseState(module_name="chemical_signaling", version=self.VERSION)

    def set_state(self, state: BaseState) -> None:
        pass

    def reset(self) -> None:
        pass
