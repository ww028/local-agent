"""SQLite document/chunk source of truth with Chinese-aware lexical search."""

import re
import sqlite3

from app.store.chats import now


def terms(text: str) -> str:
    result = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    for word in re.findall(r"[\u4e00-\u9fff]+", text):
        result.extend(word[i : i + 2] for i in range(max(1, len(word) - 1)))
    return " ".join(result)


class DocumentRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def add(
        self, key: str, title: str, filename: str, digest: str, size: int, chunks: list
    ) -> None:
        timestamp = now()
        with self.conn:
            self.conn.execute(
                "INSERT INTO documents (document_id,title,source_path,created_at,updated_at,content_hash,byte_size) "
                "VALUES (?,?,?,?,?,?,?)",
                (key, title, filename, timestamp, timestamp, digest, size),
            )
            for c in chunks:
                self.conn.execute(
                    'INSERT INTO chunks (chunk_id,document_id,heading,text,"order",start_line,end_line) '
                    "VALUES (?,?,?,?,?,?,?)",
                    (c.chunk_id, key, c.heading, c.text, c.order, c.start_line, c.end_line),
                )
                self.conn.execute(
                    "INSERT INTO chunks_fts VALUES (?,?)", (c.chunk_id, terms(c.text))
                )

    def list_all(self) -> list[dict]:
        return [
            dict(row)
            for row in self.conn.execute(
                "SELECT d.*, (SELECT count(*) FROM chunks c WHERE c.document_id=d.document_id) chunk_count "
                "FROM documents d ORDER BY d.updated_at DESC"
            )
        ]

    def get(self, key: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM documents WHERE document_id=?", (key,)).fetchone()
        return dict(row) if row else None

    def chunks(self, key: str) -> list[dict]:
        return [
            dict(row)
            for row in self.conn.execute(
                'SELECT * FROM chunks WHERE document_id=? ORDER BY "order"', (key,)
            )
        ]

    def ready_ids(self) -> list[str]:
        return [
            row[0]
            for row in self.conn.execute("SELECT document_id FROM documents WHERE status='ready'")
        ]

    def status(self, key: str, status: str, progress: int = 0, error: str | None = None):
        with self.conn:
            self.conn.execute(
                "UPDATE documents SET status=?,indexed_chunks=?,error=?,updated_at=? WHERE document_id=?",
                (status, progress, error, now(), key),
            )

    def delete(self, key: str):
        with self.conn:
            for c in self.chunks(key):
                self.conn.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (c["chunk_id"],))
            self.conn.execute("DELETE FROM documents WHERE document_id=?", (key,))

    def lexical(self, query: str, limit: int) -> list[dict]:
        tokens = list(dict.fromkeys(terms(query).split()))[:64]
        if not tokens:
            return []
        expression = " OR ".join('"' + t + '"' for t in tokens)
        return [
            dict(row)
            for row in self.conn.execute(
                "SELECT c.*,d.title document_title FROM chunks_fts f JOIN chunks c ON f.chunk_id=c.chunk_id "
                "JOIN documents d ON c.document_id=d.document_id WHERE chunks_fts MATCH ? AND d.status='ready' "
                "ORDER BY bm25(chunks_fts) LIMIT ?",
                (expression, limit),
            )
        ]
