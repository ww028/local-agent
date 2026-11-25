"""Budgeting and schema migration regression tests."""

import sqlite3

import pytest

from app.chat_context import compose_chat
from app.config import Settings
from app.schemas import ChatMessage
from app.store.db import SCHEMA, get_connection


def test_budget_preserves_pairs_and_latest_message():
    config = Settings(_env_file=None, num_ctx=2048, num_predict=128)
    history = [ChatMessage(role=role, content="x" * 500)
               for role in ["user", "assistant", "user", "assistant"]]
    messages = compose_chat("now", history, config)
    assert [m.role for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[-1].content == "now"
    with pytest.raises(ValueError):
        compose_chat("字" * 5000, [], config)


def test_old_database_migrates_without_losing_history(tmp_path):
    config = Settings(_env_file=None, db_path=tmp_path / "old.db", data_dir=tmp_path)
    conn = sqlite3.connect(config.db_path)
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO conversations VALUES ('old', 'title', 'date', 'date')")
    conn.execute("INSERT INTO messages (conversation_id, role, content, created_at) "
                 "VALUES ('old', 'user', 'keep me', 'date')")
    conn.commit()
    conn.close()
    conn = get_connection(config)
    row = conn.execute("SELECT * FROM messages").fetchone()
    assert row["content"] == "keep me" and row["status"] == "complete"
    conn.execute("UPDATE messages SET status = 'generating'")
    conn.commit()
    conn.close()
    conn = get_connection(config)
    assert conn.execute("SELECT status FROM messages").fetchone()[0] == "interrupted"
    conn.close()
