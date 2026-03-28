"""Valuation interface — value assessment, conflicts, and preferences."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class ValuationInterface(BaseModule):
    """Abstract interface for the valuation module.

    The valuation module assigns hedonic / motivational value to the
    agent's current situation, detects value conflicts (e.g. competing
    drives), and exposes the agent's preference ordering over possible
    outcomes so that action selection can make informed choices.
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "situation_evaluation",
        "conflict_detection",
        "preference_ordering",
    ]
    DEPENDENCIES: list[str] = ["homeostasis", "interoception"]

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def evaluate(self, context: TickContext) -> dict[str, Any]:
        """Evaluate the current situation and return a valuation map.

        Parameters
        ----------
        context:
            The current tick context.

        Returns
        -------
        dict:
            Valuation map with keys such as ``valence``, ``arousal``,
            ``motivational_salience``, etc.
        """
        ...

    @abstractmethod
    def get_conflicts(self) -> list[dict[str, Any]]:
        """Return currently active value conflicts.

        Each conflict is a dict with at least ``drives``, ``severity``,
        and ``description`` keys.
        """
        ...

    @abstractmethod
    def get_preference_ordering(self) -> list[dict[str, Any]]:
        """Return the agent's current preference ordering.

        Each entry is a dict with at least ``outcome`` and ``utility``
        keys, sorted from most to least preferred.
        """
        ...
