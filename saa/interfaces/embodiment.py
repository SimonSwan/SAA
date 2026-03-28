"""Embodiment interface — virtual body simulation for the agent."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class EmbodimentInterface(BaseModule):
    """Abstract interface for the embodiment module.

    The embodiment module maintains a virtual body with physiological
    variables (energy, arousal, pain, fatigue, etc.).  It applies costs
    when the agent acts, integrates environmental effects, and exposes
    the current body state so downstream modules (interoception,
    homeostasis) can read it.

    The ``update()`` implementation must return a ``ModuleOutput`` whose
    ``state`` dict contains a ``body_state`` key with the current
    physiological snapshot.
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "body_simulation",
        "action_cost",
        "environment_effects",
    ]
    DEPENDENCIES: list[str] = []

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def apply_action_cost(self, action_type: str, intensity: float) -> None:
        """Deduct resources from the body based on an action.

        Parameters
        ----------
        action_type:
            The kind of action being performed (e.g. ``"explore"``).
        intensity:
            A 0-1 scalar indicating how vigorous the action is.
        """
        ...

    @abstractmethod
    def apply_environment_effects(self, env: dict[str, Any]) -> None:
        """Integrate environmental conditions into the body state.

        Parameters
        ----------
        env:
            Dictionary describing the current environment (temperature,
            hazard level, available resources, etc.).
        """
        ...

    @abstractmethod
    def get_body_state(self) -> dict[str, Any]:
        """Return the current body-state snapshot as a plain dict.

        The dict should contain at minimum keys for ``energy``,
        ``arousal``, ``pain``, and ``fatigue``.
        """
        ...
