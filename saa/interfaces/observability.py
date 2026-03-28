"""Observability interface — tracing and snapshotting."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


class ObservabilityInterface(BaseModule):
    """Abstract interface for the observability module.

    The observability module records per-tick snapshots of the full
    system state, supports time-range queries over the trace, and
    allows filtering by individual module name.  It is intended for
    debugging, analysis, and post-hoc explanation.
    """

    VERSION: str = "0.1.0"
    CAPABILITIES: list[str] = [
        "snapshot_recording",
        "trace_query",
        "module_trace",
    ]
    DEPENDENCIES: list[str] = []

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def record_snapshot(self, tick: int, context: TickContext) -> None:
        """Record a full snapshot of the system at *tick*.

        Parameters
        ----------
        tick:
            The tick number.
        context:
            The fully populated tick context after all modules have run.
        """
        ...

    @abstractmethod
    def get_trace(
        self, start_tick: int, end_tick: int
    ) -> list[dict[str, Any]]:
        """Return snapshots for ticks in ``[start_tick, end_tick]``.

        Parameters
        ----------
        start_tick:
            First tick (inclusive).
        end_tick:
            Last tick (inclusive).

        Returns
        -------
        list:
            Ordered list of snapshot dicts.
        """
        ...

    @abstractmethod
    def get_module_trace(
        self, module_name: str, start: int, end: int
    ) -> list[dict[str, Any]]:
        """Return trace entries for a single module over a tick range.

        Parameters
        ----------
        module_name:
            Name of the module to filter by.
        start:
            First tick (inclusive).
        end:
            Last tick (inclusive).

        Returns
        -------
        list:
            Ordered list of per-module state dicts.
        """
        ...
