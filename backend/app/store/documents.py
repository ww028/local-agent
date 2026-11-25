"""Document and chunk metadata repository (SQLite)."""

from __future__ import annotations

import sqlite3
from datetime import datetime


class DocumentRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(
        self,
        *,
        document_id: str,
        title: str,
        source_path: str | None,
        chunk_count: int,
    ) -> None:
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "INSERT INTO documents (document_id, title, source_path, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (document_id, title, source_path, now, now),
        )
        self._conn.commit()

    def list_all(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT document_id, title, source_path, created_at, updated_at "
            "FROM documents ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, document_id: str) -> None:
        self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        self._conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
        self._conn.commit()
