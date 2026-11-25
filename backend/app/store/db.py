"""SQLite connection and schema initialization.

Business records live here; vector embeddings live in LanceDB. The schema
already carries owner/tenant columns reserved for future ACL/multi-tenant
support, even though the local build treats everything as public.
"""

from __future__ import annotations

import sqlite3

from app.config import Settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_path TEXT,
    owner_id TEXT,
    tenant_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    heading TEXT,
    text TEXT NOT NULL,
    \"order\" INTEGER NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);
"""


def get_connection(settings: Settings) -> sqlite3.Connection:
    settings.ensure_dirs()
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.executescript(SCHEMA)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)")}
    for name, declaration in {
        "status": "TEXT NOT NULL DEFAULT 'complete'",
        "model": "TEXT",
        "error": "TEXT",
    }.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE messages ADD COLUMN {name} {declaration}")
    for table, additions in {
        "documents": {"status": "TEXT NOT NULL DEFAULT 'pending'", "error": "TEXT",
                      "content_hash": "TEXT", "byte_size": "INTEGER DEFAULT 0",
                      "indexed_chunks": "INTEGER DEFAULT 0", "version": "INTEGER DEFAULT 1"},
        "chunks": {"start_line": "INTEGER DEFAULT 1", "end_line": "INTEGER DEFAULT 1"},
        "messages": {"citations": "TEXT NOT NULL DEFAULT '[]'"},
    }.items():
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, declaration in additions.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, terms)")
    conn.execute("UPDATE documents SET status = 'pending' WHERE status = 'indexing'")
    conn.execute("UPDATE messages SET status = 'interrupted' WHERE status = 'generating'")
    conn.commit()
    return conn
