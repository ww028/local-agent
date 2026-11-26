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
        "documents": {
            "status": "TEXT NOT NULL DEFAULT 'pending'",
            "error": "TEXT",
            "content_hash": "TEXT",
            "byte_size": "INTEGER DEFAULT 0",
            "indexed_chunks": "INTEGER DEFAULT 0",
            "version": "INTEGER DEFAULT 1",
        },
        "chunks": {"start_line": "INTEGER DEFAULT 1", "end_line": "INTEGER DEFAULT 1"},
        "messages": {"citations": "TEXT NOT NULL DEFAULT '[]'"},
    }.items():
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, declaration in additions.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, terms)"
    )
    conn.execute("UPDATE documents SET status = 'pending' WHERE status = 'indexing'")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, conversation_id TEXT,
      message_id INTEGER, status TEXT, model TEXT, created_at TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS run_events (run_id TEXT, seq INTEGER, kind TEXT, data TEXT,
      created_at TEXT, PRIMARY KEY(run_id,seq));
    """)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)")}
    if "run_id" not in columns:
        conn.execute("ALTER TABLE messages ADD COLUMN run_id TEXT")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS jobs (
      job_id TEXT PRIMARY KEY, instruction TEXT NOT NULL, model TEXT NOT NULL,
      allow_diagnostics INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL,
      summary TEXT, result TEXT NOT NULL DEFAULT '', error TEXT,
      run_id TEXT, conversation_id TEXT, parent_job_id TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL, started_at TEXT, finished_at TEXT);
    CREATE INDEX IF NOT EXISTS jobs_status_created ON jobs(status,created_at);
    """)
    conn.execute(
        "UPDATE jobs SET status='interrupted', error='Backend stopped during execution; retry explicitly', finished_at=CURRENT_TIMESTAMP WHERE status IN ('running','cancelling')"
    )
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS terminal_tasks (
      task_id TEXT PRIMARY KEY, instruction TEXT NOT NULL, model TEXT NOT NULL,
      relative_dir TEXT NOT NULL, status TEXT NOT NULL, plan TEXT, plan_hash TEXT,
      expires_at TEXT, confirmed_at TEXT, summary TEXT NOT NULL DEFAULT '', error TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL, started_at TEXT, finished_at TEXT);
    CREATE INDEX IF NOT EXISTS terminal_status_created ON terminal_tasks(status,created_at);
    CREATE TABLE IF NOT EXISTS terminal_steps (
      task_id TEXT NOT NULL, step_index INTEGER NOT NULL, status TEXT NOT NULL,
      stdout TEXT NOT NULL DEFAULT '', stderr TEXT NOT NULL DEFAULT '', exit_code INTEGER,
      error TEXT, started_at TEXT, finished_at TEXT, PRIMARY KEY(task_id,step_index));
    """)
    conn.execute(
        "UPDATE terminal_tasks SET status='interrupted',error='Service stopped; replan and confirm again' WHERE status IN ('planning','running','cancelling')"
    )
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(terminal_tasks)")}
    if "approval" not in columns:
        conn.execute("ALTER TABLE terminal_tasks ADD COLUMN approval TEXT")
    if "digest" not in columns:
        conn.execute("ALTER TABLE terminal_tasks ADD COLUMN digest TEXT")
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(terminal_steps)")}
    if "facts" not in columns:
        conn.execute("ALTER TABLE terminal_steps ADD COLUMN facts TEXT")
    conn.execute("UPDATE terminal_steps SET status='interrupted' WHERE status='running'")
    conn.execute("UPDATE runs SET status='interrupted' WHERE status='running'")
    conn.execute("UPDATE messages SET status = 'interrupted' WHERE status = 'generating'")
    conn.commit()
    return conn
