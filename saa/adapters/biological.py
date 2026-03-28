"""Biological telemetry adapter — stub for biohybrid signal interfaces.

This adapter provides abstraction layers for biological signal sources.
When implemented, it should support:

1. Abstract organoid signal channel interfaces
2. Cell-culture telemetry ingestion
3. Electrophysiological signal processing (EEG-like, MEA-like)
4. Biohybrid control layer abstraction

Ethical note:
This adapter defines interface specifications only.
No biological systems should be connected without proper ethical review,
institutional approval, and safety protocols.

Integration steps:
1. Define signal channel protocol for biological data sources
2. Implement signal conditioning (filtering, normalization, artifact rejection)
3. Map biological signals to SAA interoceptive channels
4. Support bidirectional interfaces (read biological state, send stimulation)
5. Register appropriate modules in ModuleRegistry
"""

from saa.interfaces.base import BaseModule, BaseState
from saa.core.types import ModuleOutput, TickContext


class BiologicalTelemetryAdapter(BaseModule):
    """Stub adapter for biological signal telemetry.

    Requires ethical review before connecting to biological systems.
    """

    VERSION = "0.1.0-stub"
    CAPABILITIES = ["bio_telemetry", "signal_conditioning", "electrophysiology"]
    DEPENDENCIES = []

    def initialize(self, config=None):
        raise NotImplementedError(
            "BiologicalTelemetryAdapter requires biological signal source. "
            "Implement signal channel setup and ethical compliance checks here."
        )

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        raise NotImplementedError("Implement biological signal reading here.")

    def get_state(self) -> BaseState:
        return BaseState(module_name="biological_telemetry", version=self.VERSION)

    def set_state(self, state: BaseState) -> None:
        pass

    def reset(self) -> None:
        pass
