"""Social interface — relationship tracking and attachment."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class SocialInterface(BaseModule):
    """Abstract interface for the social module.

    The social module maintains per-agent relationship records, updates
    them after every interaction, exposes bond strengths, and assesses
    attachment-related risk (e.g. isolation, betrayal vulnerability).
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "relationship_tracking",
        "bond_strength",
        "attachment_risk",
    ]
    DEPENDENCIES: list[str] = ["memory", "valuation"]

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def update_relationship(
        self, agent_id: str, interaction_data: dict[str, Any]
    ) -> None:
        """Update the relationship record for *agent_id*.

        Parameters
        ----------
        agent_id:
            Identifier of the other agent.
        interaction_data:
            Dict describing the interaction (valence, type, outcome, etc.).
        """
        ...

    @abstractmethod
    def get_relationship(self, agent_id: str) -> dict[str, Any] | None:
        """Return the relationship record for *agent_id*.

        Returns
        -------
        dict or None:
            The relationship record, or ``None`` if no relationship
            exists with this agent.
        """
        ...

    @abstractmethod
    def get_bond_strengths(self) -> dict[str, float]:
        """Return bond strengths for all known agents.

        Returns
        -------
        dict:
            Mapping from agent_id to a ``[0, 1]`` bond strength.
        """
        ...

    @abstractmethod
    def assess_attachment_risk(self) -> float:
        """Assess the agent's current attachment-related risk.

        Returns
        -------
        float:
            A score in ``[0, 1]`` where 0.0 means secure attachment
            and 1.0 means severe attachment distress.
        """
        ...
