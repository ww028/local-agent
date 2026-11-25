"""SQLite conversation repository; synchronous methods run on the API event loop."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from app.schemas import ChatMessage


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_conversation(self, title: str = "New conversation") -> str:
        key = uuid.uuid4().hex
        timestamp = now()
        with self._conn:
            self._conn.execute(
                "INSERT INTO conversations VALUES (?, ?, ?, ?)",
                (key, title, timestamp, timestamp),
            )
        return key

    def get(self, key: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM conversations WHERE conversation_id = ?", (key,)
        ).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict]:
        return [
            dict(row)
            for row in self._conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
        ]

    def messages(self, key: str) -> list[dict]:
        return [
            {**dict(row), "citations": json.loads(row["citations"] or "[]")}
            for row in self._conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (key,)
            )
        ]

    def delete(self, key: str) -> None:
        with self._conn:
            for row in self._conn.execute(
                "SELECT run_id FROM runs WHERE conversation_id=?", (key,)
            ):
                self._conn.execute("DELETE FROM run_events WHERE run_id=?", (row[0],))
            self._conn.execute("DELETE FROM runs WHERE conversation_id=?", (key,))
            self._conn.execute("DELETE FROM conversations WHERE conversation_id = ?", (key,))

    def start_turn(self, key: str, text: str, model: str) -> int:
        timestamp = now()
        with self._conn:
            self._conn.execute(
                "INSERT INTO messages (conversation_id, role, content, created_at, status, model) "
                "VALUES (?, 'user', ?, ?, 'complete', ?)",
                (key, text, timestamp, model),
            )
            cursor = self._conn.execute(
                "INSERT INTO messages (conversation_id, role, content, created_at, status, model) "
                "VALUES (?, 'assistant', '', ?, 'generating', ?)",
                (key, timestamp, model),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                (timestamp, key),
            )
        return int(cursor.lastrowid)

    def finish(self, message_id: int, text: str, status: str, error: str | None = None) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE messages SET content = ?, status = ?, error = ? WHERE id = ?",
                (text, status, error, message_id),
            )

    def history(self, key: str) -> list[ChatMessage]:
        # Only completed user/assistant pairs enter future prompts. A failed or
        # cancelled assistant reply remains visible, but is not model context.
        rows = self.messages(key)
        result: list[ChatMessage] = []
        for i in range(0, len(rows) - 1, 2):
            user, assistant = rows[i : i + 2]
            if (
                user["role"] == "user"
                and assistant["role"] == "assistant"
                and assistant["status"] == "complete"
            ):
                result.extend(
                    [
                        ChatMessage(role="user", content=user["content"]),
                        ChatMessage(role="assistant", content=assistant["content"]),
                    ]
                )
        return result
