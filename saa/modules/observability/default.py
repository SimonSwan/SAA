"""DefaultObservability — records and exposes full system state for inspection.

Captures a complete TickContext snapshot every N ticks, stores bounded
history in memory, optionally appends JSON-lines to a log file, and
provides query methods for traces, action distributions, modulator
curves, and viability trends.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Optional

from pydantic import Field

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseConfig, BaseModule, BaseState


# ---------------------------------------------------------------------------
# State & Config
# ---------------------------------------------------------------------------

class ObservabilityState(BaseState):
    """Serializable snapshot of the observability module."""

    module_name: str = "observability"
    version: str = "0.1.0"

    snapshot_count: int = 0
    current_snapshot: dict[str, Any] = Field(default_factory=dict)


class ObservabilityConfig(BaseConfig):
    """Configuration for the observability module."""

    log_every_n_ticks: int = 1
    max_snapshots: int = 10000
    log_file: Optional[str] = None


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class DefaultObservability(BaseModule):
    """Records full system state each tick and exposes query methods."""

    VERSION = "0.1.0"
    CAPABILITIES = ["observability"]
    DEPENDENCIES: list[str] = []

    def __init__(self) -> None:
        self._state = ObservabilityState()
        self._config = ObservabilityConfig()
        self._snapshots: list[dict[str, Any]] = []

    # -- lifecycle ----------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = ObservabilityConfig(**config)
        self._state = ObservabilityState()
        self._snapshots = []

    def reset(self) -> None:
        self.initialize()

    # -- state persistence --------------------------------------------------

    def get_state(self) -> ObservabilityState:
        return self._state.model_copy()

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, ObservabilityState):
            self._state = state.model_copy()
        else:
            self._state = ObservabilityState(**state.model_dump())

    # -- snapshot helpers ---------------------------------------------------

    @staticmethod
    def _context_to_snapshot(context: TickContext) -> dict[str, Any]:
        """Convert a TickContext to a plain dict snapshot."""
        return context.model_dump()

    def _persist_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Store snapshot in memory and optionally write to disk."""
        self._snapshots.append(snapshot)

        # Enforce bound
        if len(self._snapshots) > self._config.max_snapshots:
            overflow = len(self._snapshots) - self._config.max_snapshots
            self._snapshots = self._snapshots[overflow:]

        # Append JSON line to log file if configured
        if self._config.log_file is not None:
            try:
                with open(self._config.log_file, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(snapshot, default=str) + "\n")
            except OSError:
                pass  # best-effort logging

    def _compute_summary(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Derive lightweight summary metrics from recent snapshots."""
        summary: dict[str, Any] = {}

        # Viability trend (last 10 snapshots)
        recent = self._snapshots[-10:]
        viabilities: list[float] = []
        for s in recent:
            emb = s.get("embodiment_state") or {}
            energy = float(emb.get("energy", 0.5))
            damage = float(emb.get("damage", 0.0))
            viabilities.append(max(0.0, energy - damage))
        summary["viability_trend"] = viabilities

        # Modulator averages (last 10 snapshots)
        mod_sums: dict[str, list[float]] = defaultdict(list)
        for s in recent:
            mod = s.get("modulator_state") or {}
            for k, v in mod.items():
                try:
                    mod_sums[k].append(float(v))
                except (TypeError, ValueError):
                    pass
        summary["modulator_averages"] = {
            k: round(sum(vs) / len(vs), 4) if vs else 0.0
            for k, vs in mod_sums.items()
        }

        # Action distribution (last 10 snapshots)
        action_counts: dict[str, int] = defaultdict(int)
        for s in recent:
            ar = s.get("action_result") or {}
            action = ar.get("action")
            if action:
                action_counts[str(action)] += 1
        summary["action_distribution"] = dict(action_counts)

        return summary

    # -- main tick ----------------------------------------------------------

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        events: list[Event] = []

        if tick % self._config.log_every_n_ticks == 0:
            snapshot = self._context_to_snapshot(context)
            snapshot["_obs_tick"] = tick
            self._persist_snapshot(snapshot)
            self._state.snapshot_count = len(self._snapshots)
            self._state.current_snapshot = snapshot

            summary = self._compute_summary(snapshot)
            snapshot["_summary"] = summary

        self._state.tick = tick

        state_dict = self._state.model_dump()
        return ModuleOutput(
            module_name="observability",
            tick=tick,
            state=state_dict,
            events=events,
        )

    # -- query methods ------------------------------------------------------

    def get_trace(self, start_tick: int, end_tick: int) -> list[dict[str, Any]]:
        """Return all snapshots whose tick falls in [start_tick, end_tick]."""
        return [
            s for s in self._snapshots
            if start_tick <= s.get("tick", s.get("_obs_tick", -1)) <= end_tick
        ]

    def get_module_trace(
        self, module_name: str, start_tick: int, end_tick: int
    ) -> list[dict[str, Any]]:
        """Return a specific module's state dict across a tick range."""
        # Module states are stored as <module_name>_state in the context snapshot
        key = f"{module_name}_state"
        results: list[dict[str, Any]] = []
        for s in self._snapshots:
            snap_tick = s.get("tick", s.get("_obs_tick", -1))
            if start_tick <= snap_tick <= end_tick:
                module_data = s.get(key)
                if module_data is not None:
                    entry = dict(module_data)
                    entry["_tick"] = snap_tick
                    results.append(entry)
        return results

    def get_action_distribution(self, last_n_ticks: int) -> dict[str, int]:
        """Count action types over the last N snapshots."""
        recent = self._snapshots[-last_n_ticks:]
        counts: dict[str, int] = defaultdict(int)
        for s in recent:
            ar = s.get("action_result") or {}
            action = ar.get("action")
            if action:
                counts[str(action)] += 1
        return dict(counts)

    def get_modulator_curves(
        self, last_n_ticks: int
    ) -> dict[str, list[float]]:
        """Return per-modulator value lists over the last N snapshots."""
        recent = self._snapshots[-last_n_ticks:]
        curves: dict[str, list[float]] = defaultdict(list)
        for s in recent:
            mod = s.get("modulator_state") or {}
            for k, v in mod.items():
                try:
                    curves[k].append(float(v))
                except (TypeError, ValueError):
                    pass
        return dict(curves)

    def get_viability_curve(self, last_n_ticks: int) -> list[float]:
        """Return a list of viability scores over the last N snapshots.

        Viability is approximated as energy minus damage, clamped to [0, 1].
        """
        recent = self._snapshots[-last_n_ticks:]
        viabilities: list[float] = []
        for s in recent:
            emb = s.get("embodiment_state") or {}
            energy = float(emb.get("energy", 0.5))
            damage = float(emb.get("damage", 0.0))
            viabilities.append(max(0.0, min(1.0, energy - damage)))
        return viabilities

    # -- event handler ------------------------------------------------------

    def on_event(self, event: Event) -> None:
        """React to cross-module events (currently no-op)."""
        pass
