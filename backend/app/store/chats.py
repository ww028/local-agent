"""Conversation and message repository (SQLite)."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime

from app.schemas import ChatMessage


class ChatRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_conversation(self, title: str | None = None) -> str:
        conversation_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "INSERT INTO conversations (conversation_id, title, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (conversation_id, title, now, now),
        )
        self._conn.commit()
        return conversation_id

    def add_message(self, conversation_id: str, message: ChatMessage) -> None:
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (conversation_id, message.role, message.content, now),
        )
        self._conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
            (now, conversation_id),
        )
        self._conn.commit()

    def history(self, conversation_id: str, limit: int = 20) -> list[ChatMessage]:
        rows = self._conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        return [ChatMessage(role=row["role"], content=row["content"]) for row in reversed(rows)]
