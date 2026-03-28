"""SQLite-backed memory system — episodic, semantic, relational, procedural, and affect-tagged memory."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from pydantic import BaseModel, Field

from saa.core.types import Event, ModuleOutput, TickContext
from saa.interfaces.base import BaseModule, BaseConfig, BaseState


class MemoryState(BaseState):
    """Serializable state for the memory module."""

    module_name: str = "memory"
    version: str = "0.1.0"
    episodic_count: int = 0
    semantic_count: int = 0
    relational_count: int = 0
    last_encoded_tick: int = 0


class MemoryConfig(BaseConfig):
    """Configuration for the memory module."""

    db_path: str = ":memory:"
    decay_rate: float = 0.01
    max_episodes: int = 10000
    importance_threshold: float = 0.3


# ---------------------------------------------------------------------------
# SQL schemas
# ---------------------------------------------------------------------------

_CREATE_EPISODIC = """
CREATE TABLE IF NOT EXISTS episodic_memory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tick            INTEGER NOT NULL,
    summary_json    TEXT    NOT NULL,
    affect_valence  REAL    NOT NULL DEFAULT 0.0,
    affect_arousal  REAL    NOT NULL DEFAULT 0.5,
    importance      REAL    NOT NULL DEFAULT 0.5,
    access_count    INTEGER NOT NULL DEFAULT 0,
    last_accessed   REAL    NOT NULL,
    created_at      REAL    NOT NULL
);
"""

_CREATE_SEMANTIC = """
CREATE TABLE IF NOT EXISTS semantic_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT    NOT NULL UNIQUE,
    value_json  TEXT    NOT NULL,
    confidence  REAL    NOT NULL DEFAULT 1.0,
    source_tick INTEGER NOT NULL,
    updated_at  REAL    NOT NULL
);
"""

_CREATE_RELATIONAL = """
CREATE TABLE IF NOT EXISTS relational_memory (
    agent_id            TEXT PRIMARY KEY,
    trust               REAL    NOT NULL DEFAULT 0.5,
    dependency          REAL    NOT NULL DEFAULT 0.0,
    attachment          REAL    NOT NULL DEFAULT 0.0,
    bond_strength       REAL    NOT NULL DEFAULT 0.0,
    interaction_count   INTEGER NOT NULL DEFAULT 0,
    betrayal_count      INTEGER NOT NULL DEFAULT 0,
    last_interaction_tick INTEGER NOT NULL DEFAULT 0,
    history_json        TEXT    NOT NULL DEFAULT '[]'
);
"""

_CREATE_PROCEDURAL = """
CREATE TABLE IF NOT EXISTS procedural_memory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action_pattern  TEXT    NOT NULL,
    success_rate    REAL    NOT NULL DEFAULT 0.5,
    usage_count     INTEGER NOT NULL DEFAULT 0,
    context_json    TEXT    NOT NULL DEFAULT '{}'
);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_importance(context: TickContext) -> float:
    """Derive an importance score in [0, 1] from the current tick context."""
    score = 0.0
    homeo_err = context.homeostatic_error or {}

    # Viability change magnitude
    overall_error = homeo_err.get("overall", homeo_err.get("viability_deficit", 0.0))
    score += min(1.0, abs(overall_error)) * 0.4

    # Event severity
    if context.events:
        max_sev = max(e.severity for e in context.events)
        score += max_sev * 0.35

    # Social significance
    social = context.social_state or {}
    if social.get("betrayal") or social.get("new_bond"):
        score += 0.25

    return min(1.0, score)


def _compute_affect_valence(context: TickContext) -> float:
    """Return affect valence in [-1, 1]. Positive = good, negative = bad."""
    valence = 0.0
    homeo_err = context.homeostatic_error or {}

    # Positive signals
    recovery = homeo_err.get("recovery", 0.0)
    valence += float(recovery) * 0.5

    social = context.social_state or {}
    trust_gain = social.get("trust_gain", 0.0)
    valence += float(trust_gain) * 0.3

    # Negative signals
    damage = homeo_err.get("damage", 0.0)
    valence -= float(damage) * 0.5

    betrayal = social.get("betrayal_severity", 0.0)
    valence -= float(betrayal) * 0.4

    pain = (context.interoceptive_vector or {}).get("pain", 0.0)
    valence -= float(pain) * 0.3

    return max(-1.0, min(1.0, valence))


def _compute_affect_arousal(context: TickContext) -> float:
    """Return affect arousal in [0, 1]."""
    arousal = 0.3  # baseline
    if context.events:
        arousal += max(e.severity for e in context.events) * 0.4
    homeo_err = context.homeostatic_error or {}
    overall = homeo_err.get("overall", 0.0)
    arousal += float(overall) * 0.3
    return min(1.0, arousal)


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


class SQLiteMemorySystem(BaseModule):
    """Full memory system with episodic, semantic, relational, procedural, and affect-tagged memory."""

    VERSION = "0.1.0"
    CAPABILITIES = [
        "episodic_memory",
        "semantic_memory",
        "relational_memory",
        "procedural_memory",
        "affect_tagging",
    ]
    DEPENDENCIES = ["interoception", "homeostasis"]

    def __init__(self) -> None:
        self._config = MemoryConfig()
        self._state = MemoryState()
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # BaseModule interface
    # ------------------------------------------------------------------

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self._config = MemoryConfig(**config)
        self._state = MemoryState()
        self._conn = sqlite3.connect(self._config.db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        assert self._conn is not None
        cur = self._conn.cursor()
        cur.execute(_CREATE_EPISODIC)
        cur.execute(_CREATE_SEMANTIC)
        cur.execute(_CREATE_RELATIONAL)
        cur.execute(_CREATE_PROCEDURAL)
        self._conn.commit()

    def update(self, tick: int, context: TickContext) -> ModuleOutput:
        assert self._conn is not None
        self._state.tick = tick

        importance = _compute_importance(context)
        valence = _compute_affect_valence(context)
        arousal = _compute_affect_arousal(context)

        # ---- 1. Encode episode if important enough -----------------------
        encoded = False
        if importance >= self._config.importance_threshold:
            summary = self._build_episode_summary(tick, context)
            now = time.time()
            self._conn.execute(
                """INSERT INTO episodic_memory
                   (tick, summary_json, affect_valence, affect_arousal,
                    importance, access_count, last_accessed, created_at)
                   VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
                (tick, json.dumps(summary), valence, arousal, importance, now, now),
            )
            self._conn.commit()
            self._state.last_encoded_tick = tick
            encoded = True

        # ---- 2. Retrieve relevant memories -------------------------------
        recent_episodes = self._get_recent_episodes(limit=5)
        relevant_episodes = self._retrieve_relevant(context, limit=5)

        # ---- 3. Apply decay to old episodes ------------------------------
        self._apply_decay(tick)

        # ---- 4. Enforce max episodes -------------------------------------
        self._enforce_max_episodes()

        # ---- 5. Update counts --------------------------------------------
        self._state.episodic_count = self._count_table("episodic_memory")
        self._state.semantic_count = self._count_table("semantic_memory")
        self._state.relational_count = self._count_table("relational_memory")

        # ---- 6. Build output ---------------------------------------------
        memory_context: dict[str, Any] = {
            "recent_episodes": recent_episodes,
            "relevant_episodes": relevant_episodes,
            "episodic_count": self._state.episodic_count,
            "encoded_this_tick": encoded,
            "current_affect": {"valence": valence, "arousal": arousal},
        }

        output_state = self._state.model_dump()
        output_state["memory_context"] = memory_context

        return ModuleOutput(
            module_name="memory",
            tick=tick,
            state=output_state,
            events=[],
        )

    def get_state(self) -> MemoryState:
        return self._state.model_copy(deep=True)

    def set_state(self, state: BaseState) -> None:
        if isinstance(state, MemoryState):
            self._state = state.model_copy(deep=True)
        else:
            self._state = MemoryState(**state.model_dump())

    def reset(self) -> None:
        self._state = MemoryState()
        if self._conn:
            self._conn.close()
        self._conn = sqlite3.connect(self._config.db_path)
        self._conn.row_factory = sqlite3.Row
        # Drop and recreate tables
        for table in ("episodic_memory", "semantic_memory", "relational_memory", "procedural_memory"):
            self._conn.execute(f"DROP TABLE IF EXISTS {table}")
        self._create_tables()

    # ------------------------------------------------------------------
    # Public API — relational memory
    # ------------------------------------------------------------------

    def encode_relational(
        self,
        agent_id: str,
        trust_delta: float,
        interaction_type: str,
    ) -> None:
        """Update relational memory for *agent_id*."""
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM relational_memory WHERE agent_id = ?", (agent_id,)
        ).fetchone()

        if row is None:
            trust = max(0.0, min(1.0, 0.5 + trust_delta))
            history = [{"type": interaction_type, "trust_delta": trust_delta}]
            self._conn.execute(
                """INSERT INTO relational_memory
                   (agent_id, trust, dependency, attachment, bond_strength,
                    interaction_count, betrayal_count, last_interaction_tick, history_json)
                   VALUES (?, ?, 0.0, 0.0, 0.0, 1, ?, ?, ?)""",
                (
                    agent_id,
                    trust,
                    1 if trust_delta < -0.2 else 0,
                    self._state.tick,
                    json.dumps(history),
                ),
            )
        else:
            trust = max(0.0, min(1.0, row["trust"] + trust_delta))
            interaction_count = row["interaction_count"] + 1
            betrayal_count = row["betrayal_count"] + (1 if trust_delta < -0.2 else 0)
            bond_strength = min(1.0, interaction_count * 0.02)
            history = json.loads(row["history_json"])
            history.append({"type": interaction_type, "trust_delta": trust_delta})
            # Keep history bounded
            history = history[-100:]
            self._conn.execute(
                """UPDATE relational_memory
                   SET trust = ?, interaction_count = ?, betrayal_count = ?,
                       bond_strength = ?, last_interaction_tick = ?, history_json = ?
                   WHERE agent_id = ?""",
                (
                    trust,
                    interaction_count,
                    betrayal_count,
                    bond_strength,
                    self._state.tick,
                    json.dumps(history),
                    agent_id,
                ),
            )
        self._conn.commit()

    def get_relational(self, agent_id: str) -> dict[str, Any]:
        """Retrieve relational memory for *agent_id*, or empty dict."""
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM relational_memory WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        if row is None:
            return {}
        result = dict(row)
        result["history"] = json.loads(result.pop("history_json"))
        return result

    def retrieve_by_affect(
        self,
        valence_range: tuple[float, float],
        arousal_range: tuple[float, float],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve episodic memories matching the given affect ranges."""
        assert self._conn is not None
        rows = self._conn.execute(
            """SELECT * FROM episodic_memory
               WHERE affect_valence BETWEEN ? AND ?
                 AND affect_arousal BETWEEN ? AND ?
               ORDER BY importance DESC
               LIMIT ?""",
            (valence_range[0], valence_range[1], arousal_range[0], arousal_range[1], limit),
        ).fetchall()

        results = []
        now = time.time()
        for row in rows:
            entry = dict(row)
            entry["summary"] = json.loads(entry.pop("summary_json"))
            results.append(entry)
            # Update access tracking
            self._conn.execute(
                """UPDATE episodic_memory
                   SET access_count = access_count + 1, last_accessed = ?
                   WHERE id = ?""",
                (now, row["id"]),
            )
        if results:
            self._conn.commit()
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_episode_summary(self, tick: int, context: TickContext) -> dict[str, Any]:
        """Build a JSON-serializable summary of the current tick for storage."""
        summary: dict[str, Any] = {"tick": tick}

        if context.interoceptive_vector:
            summary["interoceptive"] = context.interoceptive_vector
        if context.homeostatic_error:
            summary["homeostatic_error"] = context.homeostatic_error
        if context.allostatic_forecast:
            summary["allostatic_forecast"] = {
                k: v
                for k, v in context.allostatic_forecast.items()
                if k in ("risk_scores", "anticipatory_actions")
            }
        if context.events:
            summary["events"] = [
                {"type": e.event_type, "severity": e.severity, "source": e.source_module}
                for e in context.events
            ]
        summary["environment"] = {
            "hazard_level": context.environment.hazard_level,
            "available_resources": context.environment.available_resources,
        }
        return summary

    def _get_recent_episodes(self, limit: int = 5) -> list[dict[str, Any]]:
        """Return the most recent episodic memories."""
        assert self._conn is not None
        rows = self._conn.execute(
            """SELECT * FROM episodic_memory
               ORDER BY tick DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        results = []
        for row in rows:
            entry = dict(row)
            entry["summary"] = json.loads(entry.pop("summary_json"))
            results.append(entry)
        return results

    def _retrieve_relevant(self, context: TickContext, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve memories relevant to the current context.

        Relevance heuristic: match on similar interoceptive state by looking
        for episodes whose stored interoceptive values are close to current.
        Falls back to high-importance episodes.
        """
        assert self._conn is not None
        intero = context.interoceptive_vector or {}

        if not intero:
            # Fall back to highest-importance memories
            rows = self._conn.execute(
                """SELECT * FROM episodic_memory
                   ORDER BY importance DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        else:
            # Fetch candidates and score in Python (SQLite lacks vector ops)
            rows = self._conn.execute(
                """SELECT * FROM episodic_memory
                   ORDER BY importance DESC
                   LIMIT ?""",
                (limit * 10,),  # over-fetch, then re-rank
            ).fetchall()

            def _similarity(row: sqlite3.Row) -> float:
                summary = json.loads(row["summary_json"])
                stored_intero = summary.get("interoceptive", {})
                if not stored_intero:
                    return 0.0
                diffs = []
                for key, val in intero.items():
                    if key in stored_intero and isinstance(val, (int, float)):
                        diffs.append(abs(float(val) - float(stored_intero[key])))
                if not diffs:
                    return 0.0
                # Similarity = 1 - mean_absolute_difference
                return 1.0 - (sum(diffs) / len(diffs))

            scored = sorted(rows, key=_similarity, reverse=True)
            rows = scored[:limit]

        now = time.time()
        results = []
        for row in rows:
            entry = dict(row)
            entry["summary"] = json.loads(entry.pop("summary_json"))
            results.append(entry)
            self._conn.execute(
                """UPDATE episodic_memory
                   SET access_count = access_count + 1, last_accessed = ?
                   WHERE id = ?""",
                (now, row["id"]),
            )
        if results:
            self._conn.commit()
        return results

    def _apply_decay(self, current_tick: int) -> None:
        """Reduce importance of old episodes gradually."""
        assert self._conn is not None
        # Decay factor: importance *= (1 - decay_rate) for episodes older than 10 ticks
        self._conn.execute(
            """UPDATE episodic_memory
               SET importance = importance * ?
               WHERE tick < ?""",
            (1.0 - self._config.decay_rate, current_tick - 10),
        )
        self._conn.commit()

    def _enforce_max_episodes(self) -> None:
        """Delete least-important episodes if count exceeds max."""
        assert self._conn is not None
        count = self._count_table("episodic_memory")
        if count > self._config.max_episodes:
            excess = count - self._config.max_episodes
            self._conn.execute(
                """DELETE FROM episodic_memory
                   WHERE id IN (
                       SELECT id FROM episodic_memory
                       ORDER BY importance ASC
                       LIMIT ?
                   )""",
                (excess,),
            )
            self._conn.commit()

    def _count_table(self, table: str) -> int:
        assert self._conn is not None
        row = self._conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
        return row["cnt"] if row else 0
