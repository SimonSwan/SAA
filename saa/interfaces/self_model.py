"""Self-model interface — autobiographical identity and continuity."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class SelfModelInterface(BaseModule):
    """Abstract interface for the self-model module.

    The self-model maintains a narrative autobiography of the agent,
    tracks identity continuity across time, detects threats to
    self-coherence, and holds identity anchors (core beliefs, values,
    or memories) that ground the agent's sense of self.
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "autobiography",
        "continuity_assessment",
        "threat_detection",
        "identity_anchoring",
    ]
    DEPENDENCIES: list[str] = ["memory", "valuation"]

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def update_autobiography(self, tick: int, summary: str) -> None:
        """Append an entry to the autobiographical record.

        Parameters
        ----------
        tick:
            The tick at which the event occurred.
        summary:
            A natural-language summary of what happened.
        """
        ...

    @abstractmethod
    def assess_continuity(self) -> float:
        """Evaluate how continuous the agent's identity feels.

        Returns
        -------
        float:
            A score in ``[0, 1]`` where 1.0 means fully coherent identity
            and 0.0 means severe discontinuity / identity crisis.
        """
        ...

    @abstractmethod
    def detect_threats(self, context: TickContext) -> list[dict[str, Any]]:
        """Detect events or states that threaten self-coherence.

        Parameters
        ----------
        context:
            The current tick context.

        Returns
        -------
        list:
            Each threat is a dict with at least ``threat_type``,
            ``severity``, and ``description`` keys.
        """
        ...

    @abstractmethod
    def get_identity_anchors(self) -> list[dict[str, Any]]:
        """Return the agent's core identity anchors.

        Each anchor is a dict with at least ``anchor_type``, ``content``,
        and ``strength`` keys.
        """
        ...
