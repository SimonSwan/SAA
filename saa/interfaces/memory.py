"""Memory interface — episodic encoding, retrieval, and decay."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class MemoryInterface(BaseModule):
    """Abstract interface for the memory module.

    The memory module stores episodic records, supports cue-based
    retrieval, applies time-based decay, maintains per-agent relational
    memories, and allows selective reinforcement of important episodes.
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "episodic_encoding",
        "cue_retrieval",
        "decay",
        "relational_memory",
        "reinforcement",
    ]
    DEPENDENCIES: list[str] = []

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def encode(self, episode_data: dict[str, Any]) -> None:
        """Encode a new episode into memory.

        Parameters
        ----------
        episode_data:
            A dict describing the episode (tick, summary, emotional
            valence, participants, etc.).
        """
        ...

    @abstractmethod
    def retrieve(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        """Retrieve episodes matching *query*.

        Parameters
        ----------
        query:
            Retrieval cues (e.g. ``{"emotion": "fear", "recency": 10}``).

        Returns
        -------
        list:
            Matching episodes sorted by relevance / activation.
        """
        ...

    @abstractmethod
    def decay(self, tick: int) -> None:
        """Apply time-based decay to all stored episodes.

        Parameters
        ----------
        tick:
            The current tick, used to calculate elapsed time.
        """
        ...

    @abstractmethod
    def get_relational_memory(self, agent_id: str) -> dict[str, Any] | None:
        """Return accumulated relational memory for *agent_id*.

        Parameters
        ----------
        agent_id:
            Identifier of the other agent.

        Returns
        -------
        dict or None:
            Relational memory record, or ``None`` if no interactions
            have been recorded with this agent.
        """
        ...

    @abstractmethod
    def reinforce(self, episode_id: str, amount: float) -> None:
        """Strengthen or weaken a specific episode's trace.

        Parameters
        ----------
        episode_id:
            Unique identifier of the episode.
        amount:
            Positive values strengthen the trace; negative values weaken it.
        """
        ...
