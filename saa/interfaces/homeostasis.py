"""Homeostasis interface — maintaining physiological balance."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class HomeostasisInterface(BaseModule):
    """Abstract interface for the homeostasis module.

    Homeostasis compares interoceptive readings against set-point
    targets and computes error signals.  It exposes an overall viability
    score (how far the organism is from a viable state) and a priority
    list that tells downstream modules which variables most urgently
    need correcting.
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "error_computation",
        "viability_scoring",
        "regulation_priority",
    ]
    DEPENDENCIES: list[str] = ["interoception"]

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def compute_error(self, interoceptive_dict: dict[str, Any]) -> dict[str, Any]:
        """Compute the signed error for each homeostatic variable.

        Parameters
        ----------
        interoceptive_dict:
            Normalised interoceptive vector from the interoception module.

        Returns
        -------
        dict:
            Mapping from variable name to signed error (positive means
            above set-point, negative means below).
        """
        ...

    @abstractmethod
    def get_viability(self) -> float:
        """Return the current viability score in ``[0, 1]``.

        1.0 means all variables are at their set-points; 0.0 means the
        organism is at the boundary of its viability zone.
        """
        ...

    @abstractmethod
    def get_regulation_priorities(self) -> list[dict[str, Any]]:
        """Return an ordered list of regulation priorities.

        Each entry is a dict with at least ``variable``, ``error``, and
        ``urgency`` keys, sorted from most to least urgent.
        """
        ...
