"""SQLite persistence layer for agent state and memory."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class PersistenceLayer:
    """SQLite-backed persistence for full agent state snapshots and memory.

    Stores agent state as JSON blobs per tick/episode.
    Provides a general key-value store for module-specific data.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        assert self._conn is not None
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS agent_state (
                agent_id TEXT NOT NULL,
                tick INTEGER NOT NULL,
                state_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (agent_id, tick)
            );

            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                tick INTEGER NOT NULL,
                module_name TEXT NOT NULL,
                event_type TEXT,
                data_json TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                affect_valence REAL DEFAULT 0.0,
                affect_arousal REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_episodes_agent_tick
                ON episodes(agent_id, tick);
            CREATE INDEX IF NOT EXISTS idx_episodes_module
                ON episodes(module_name);
            CREATE INDEX IF NOT EXISTS idx_episodes_importance
                ON episodes(importance DESC);

            CREATE TABLE IF NOT EXISTS kv_store (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (namespace, key)
            );
        """)

    def save_agent_state(self, agent_id: str, tick: int, state: dict[str, Any]) -> None:
        assert self._conn is not None
        self._conn.execute(
            "INSERT OR REPLACE INTO agent_state (agent_id, tick, state_json) VALUES (?, ?, ?)",
            (agent_id, tick, json.dumps(state)),
        )
        self._conn.commit()

    def load_agent_state(self, agent_id: str, tick: int | None = None) -> dict[str, Any] | None:
        assert self._conn is not None
        if tick is not None:
            row = self._conn.execute(
                "SELECT state_json FROM agent_state WHERE agent_id = ? AND tick = ?",
                (agent_id, tick),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT state_json FROM agent_state WHERE agent_id = ? ORDER BY tick DESC LIMIT 1",
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def save_episode(
        self,
        agent_id: str,
        tick: int,
        module_name: str,
        data: dict[str, Any],
        event_type: str | None = None,
        importance: float = 0.5,
        affect_valence: float = 0.0,
        affect_arousal: float = 0.0,
    ) -> int:
        assert self._conn is not None
        cursor = self._conn.execute(
            """INSERT INTO episodes
            (agent_id, tick, module_name, event_type, data_json, importance, affect_valence, affect_arousal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, tick, module_name, event_type, json.dumps(data), importance, affect_valence, affect_arousal),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def query_episodes(
        self,
        agent_id: str,
        module_name: str | None = None,
        min_importance: float = 0.0,
        limit: int = 100,
        since_tick: int = 0,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        query = "SELECT * FROM episodes WHERE agent_id = ? AND tick >= ? AND importance >= ?"
        params: list[Any] = [agent_id, since_tick, min_importance]
        if module_name is not None:
            query += " AND module_name = ?"
            params.append(module_name)
        query += " ORDER BY importance DESC, tick DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        columns = ["id", "agent_id", "tick", "module_name", "event_type",
                    "data_json", "importance", "affect_valence", "affect_arousal", "created_at"]
        results = []
        for row in rows:
            entry = dict(zip(columns, row))
            entry["data"] = json.loads(entry.pop("data_json"))
            results.append(entry)
        return results

    def kv_set(self, namespace: str, key: str, value: Any) -> None:
        assert self._conn is not None
        self._conn.execute(
            "INSERT OR REPLACE INTO kv_store (namespace, key, value_json) VALUES (?, ?, ?)",
            (namespace, key, json.dumps(value)),
        )
        self._conn.commit()

    def kv_get(self, namespace: str, key: str) -> Any | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT value_json FROM kv_store WHERE namespace = ? AND key = ?",
            (namespace, key),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
