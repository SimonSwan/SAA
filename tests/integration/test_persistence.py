"""Integration tests for persistence — save, load, resume agent state."""

import tempfile
from pathlib import Path

import pytest

from saa.core.persistence import PersistenceLayer
from tests.conftest import build_full_engine


class TestPersistence:
    """Test state persistence across sessions."""

    def test_save_and_load_agent_state(self):
        p = PersistenceLayer(":memory:")
        p.connect()

        state = {"energy": 0.5, "temperature": 0.3}
        p.save_agent_state("agent_0", 1, state)

        loaded = p.load_agent_state("agent_0", 1)
        assert loaded == state

        p.close()

    def test_load_latest_state(self):
        p = PersistenceLayer(":memory:")
        p.connect()

        p.save_agent_state("agent_0", 1, {"tick": 1})
        p.save_agent_state("agent_0", 2, {"tick": 2})
        p.save_agent_state("agent_0", 3, {"tick": 3})

        latest = p.load_agent_state("agent_0")
        assert latest["tick"] == 3

        p.close()

    def test_episode_storage(self):
        p = PersistenceLayer(":memory:")
        p.connect()

        ep_id = p.save_episode(
            agent_id="agent_0",
            tick=5,
            module_name="memory",
            data={"summary": "test event"},
            importance=0.8,
            affect_valence=-0.3,
        )
        assert ep_id is not None

        results = p.query_episodes("agent_0", min_importance=0.5)
        assert len(results) == 1
        assert results[0]["data"]["summary"] == "test event"

        p.close()

    def test_kv_store(self):
        p = PersistenceLayer(":memory:")
        p.connect()

        p.kv_set("config", "learning_rate", 0.05)
        val = p.kv_get("config", "learning_rate")
        assert val == 0.05

        p.close()

    def test_full_engine_persistence_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"

            # Run first session
            engine1, _, _, p1 = build_full_engine()
            engine1.persistence = PersistenceLayer(str(db_path))
            engine1.persistence.connect()
            engine1.initialize_modules()
            engine1.run(10)
            state1 = engine1.save_state()
            engine1.persistence.save_agent_state("test_agent", 10, state1)
            engine1.persistence.close()

            # Resume from disk
            p2 = PersistenceLayer(str(db_path))
            p2.connect()
            loaded = p2.load_agent_state("test_agent", 10)
            assert loaded is not None
            assert "embodiment" in loaded
            p2.close()

    def test_missing_agent_returns_none(self):
        p = PersistenceLayer(":memory:")
        p.connect()

        result = p.load_agent_state("nonexistent")
        assert result is None

        p.close()
