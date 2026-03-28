"""Interoception interface — internal sensing of bodily signals."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class InteroceptionInterface(BaseModule):
    """Abstract interface for the interoception module.

    Interoception reads the raw body state produced by the embodiment
    module and converts it into a normalised interoceptive vector.  It
    also detects threshold-crossing alerts and tracks trends over a
    sliding window so downstream modules can react to *changes* rather
    than absolute values.
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "body_sensing",
        "alert_detection",
        "trend_tracking",
    ]
    DEPENDENCIES: list[str] = ["embodiment"]

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def sense(self, body_state_dict: dict[str, Any]) -> dict[str, Any]:
        """Convert a raw body-state dict into a normalised interoceptive vector.

        Parameters
        ----------
        body_state_dict:
            The body-state snapshot from the embodiment module.

        Returns
        -------
        dict:
            Normalised interoceptive channels (e.g. ``{"energy": 0.7, ...}``).
        """
        ...

    @abstractmethod
    def get_alerts(self) -> list[dict[str, Any]]:
        """Return a list of currently active interoceptive alerts.

        Each alert is a dict with at least ``channel``, ``level``, and
        ``direction`` keys.
        """
        ...

    @abstractmethod
    def get_trend(self, channel: str, window: int) -> float:
        """Return the recent trend for *channel* over the last *window* ticks.

        Parameters
        ----------
        channel:
            The interoceptive channel name (e.g. ``"energy"``).
        window:
            Number of past ticks to consider.

        Returns
        -------
        float:
            A signed value: positive means increasing, negative means
            decreasing, zero means stable.
        """
        ...
