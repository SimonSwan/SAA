"""Allostasis interface — predictive regulation and anticipation."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class AllostasisInterface(BaseModule):
    """Abstract interface for the allostasis module.

    Allostasis extends homeostasis by *anticipating* future regulatory
    demands.  It forecasts how the body and environment will evolve,
    assigns risk scores to potential futures, and recommends anticipatory
    actions the agent can take before a deficit actually arises.
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "forecasting",
        "risk_scoring",
        "anticipatory_action",
    ]
    DEPENDENCIES: list[str] = ["homeostasis", "interoception"]

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def forecast(self, context: TickContext, horizon: int) -> dict[str, Any]:
        """Predict future homeostatic state over *horizon* ticks.

        Parameters
        ----------
        context:
            The current tick context with accumulated module outputs.
        horizon:
            How many ticks ahead to forecast.

        Returns
        -------
        dict:
            Predicted variable trajectories keyed by variable name.
        """
        ...

    @abstractmethod
    def get_risk_scores(self) -> dict[str, float]:
        """Return risk scores for each tracked variable.

        Returns
        -------
        dict:
            Mapping from variable name to a ``[0, 1]`` risk score where
            1.0 indicates imminent viability-zone breach.
        """
        ...

    @abstractmethod
    def get_anticipatory_actions(self) -> list[dict[str, Any]]:
        """Return a list of recommended anticipatory actions.

        Each entry is a dict with at least ``action_type``, ``target``,
        and ``urgency`` keys.
        """
        ...
