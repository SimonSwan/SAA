"""Action selection interface — candidate generation and selection."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class ActionSelectionInterface(BaseModule):
    """Abstract interface for the action selection module.

    Action selection is the final decision-making stage of each tick.
    It generates candidate actions from the accumulated context,
    selects the best candidate according to the current valuation and
    regulatory priorities, and retains a decision trace for
    observability.
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "candidate_generation",
        "action_selection",
        "decision_trace",
    ]
    DEPENDENCIES: list[str] = [
        "valuation",
        "homeostasis",
        "allostasis",
        "neuromodulation",
    ]

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def generate_candidates(self, context: TickContext) -> list[dict[str, Any]]:
        """Generate a set of candidate actions from *context*.

        Parameters
        ----------
        context:
            The current tick context with all upstream module outputs.

        Returns
        -------
        list:
            Each candidate is a dict with at least ``action_type``,
            ``target``, and ``expected_utility`` keys.
        """
        ...

    @abstractmethod
    def select_action(
        self, candidates: list[dict[str, Any]], context: TickContext
    ) -> dict[str, Any]:
        """Choose the best action from *candidates*.

        Parameters
        ----------
        candidates:
            The list returned by ``generate_candidates``.
        context:
            The current tick context.

        Returns
        -------
        dict:
            The selected action dict, augmented with a ``rationale`` key.
        """
        ...

    @abstractmethod
    def get_last_trace(self) -> dict[str, Any] | None:
        """Return the decision trace from the most recent selection.

        Returns
        -------
        dict or None:
            A dict with ``candidates``, ``selected``, ``scores``, and
            ``rationale`` keys, or ``None`` if no selection has been
            made yet.
        """
        ...
