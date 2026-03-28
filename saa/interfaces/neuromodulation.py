"""Neuromodulation interface — tonic modulator dynamics."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class NeuromodulationInterface(BaseModule):
    """Abstract interface for the neuromodulation module.

    Neuromodulation tracks tonic levels of virtual neuromodulators
    (e.g. dopamine, serotonin, norepinephrine, cortisol analogues).
    It exposes the current modulator state, computes how those levels
    shift downstream parameters (learning rate, exploration bias, etc.),
    and supports explicit accumulation and passive decay.
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "modulator_tracking",
        "parameter_shifting",
        "accumulation",
        "passive_decay",
    ]
    DEPENDENCIES: list[str] = ["homeostasis", "interoception"]

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def get_modulator_state(self) -> dict[str, float]:
        """Return current levels of all tracked modulators.

        Returns
        -------
        dict:
            Mapping from modulator name to its current level (e.g.
            ``{"dopamine": 0.6, "cortisol": 0.3}``).
        """
        ...

    @abstractmethod
    def get_parameter_shifts(self) -> dict[str, float]:
        """Compute downstream parameter shifts implied by modulator levels.

        Returns
        -------
        dict:
            Mapping from parameter name to its shift value (e.g.
            ``{"learning_rate": +0.1, "exploration_bias": -0.05}``).
        """
        ...

    @abstractmethod
    def accumulate(self, modulator: str, amount: float) -> None:
        """Add *amount* to the named modulator's tonic level.

        Parameters
        ----------
        modulator:
            Name of the modulator (e.g. ``"dopamine"``).
        amount:
            Signed increment; positive raises, negative lowers.
        """
        ...

    @abstractmethod
    def decay_all(self, dt: float) -> None:
        """Apply passive exponential decay to all modulators.

        Parameters
        ----------
        dt:
            Time-step size; larger values produce more decay.
        """
        ...
