"""Persistent job queue. Only explicit retry creates a new execution."""

import uuid

from app.store.chats import now

TERMINAL = {"completed", "failed", "cancelled", "interrupted"}


class JobRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, instruction, model, allow_diagnostics=False, parent=None):
        timestamp = now()
        key = uuid.uuid4().hex
        with self.conn:
            count = self.conn.execute(
                "SELECT count(*) FROM jobs WHERE status IN ('queued','running','cancelling')"
            ).fetchone()[0]
            if count >= 32:
                raise ValueError("Task queue is full; wait or cancel queued work")
            self.conn.execute(
                "INSERT INTO jobs (job_id,instruction,model,allow_diagnostics,status,summary,parent_job_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    key,
                    instruction,
                    model,
                    int(allow_diagnostics),
                    "queued",
                    "等待后台执行",
                    parent,
                    timestamp,
                    timestamp,
                ),
            )
        return self.get(key)

    def get(self, key):
        row = self.conn.execute("SELECT * FROM jobs WHERE job_id=?", (key,)).fetchone()
        if row is None:
            return None
        return {**dict(row), "allow_diagnostics": bool(row["allow_diagnostics"])}

    def list(self, limit=50, offset=0):
        return [
            dict(row)
            for row in self.conn.execute(
                "SELECT job_id,instruction,model,allow_diagnostics,status,summary,error,created_at,updated_at,started_at,finished_at,parent_job_id FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        ]

    def next(self):
        row = self.conn.execute(
            "SELECT job_id FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1"
        ).fetchone()
        return self.get(row[0]) if row else None

    def claim(self, key):
        with self.conn:
            cursor = self.conn.execute(
                "UPDATE jobs SET status='running',summary='模型正在执行',started_at=?,updated_at=? WHERE job_id=? AND status='queued'",
                (now(), now(), key),
            )
        return cursor.rowcount == 1

    def attach(self, key, conversation_id, run_id):
        with self.conn:
            self.conn.execute(
                "UPDATE jobs SET conversation_id=?,run_id=?,updated_at=? WHERE job_id=?",
                (conversation_id, run_id, now(), key),
            )

    def progress(self, key, summary):
        with self.conn:
            self.conn.execute(
                "UPDATE jobs SET summary=?,updated_at=? WHERE job_id=? AND status='running'",
                (summary, now(), key),
            )

    def finish(self, key, status, result="", error=None):
        assert status in TERMINAL
        with self.conn:
            self.conn.execute(
                "UPDATE jobs SET status=?,result=?,error=?,summary=?,finished_at=?,updated_at=? WHERE job_id=? AND status IN ('queued','running','cancelling')",
                (
                    status,
                    result,
                    error,
                    {
                        "completed": "任务完成",
                        "failed": "执行失败",
                        "cancelled": "已取消",
                        "interrupted": "服务停止，任务中断",
                    }[status],
                    now(),
                    now(),
                    key,
                ),
            )

    def request_cancel(self, key):
        job = self.get(key)
        if job is None:
            raise KeyError(key)
        if job["status"] == "queued":
            self.finish(key, "cancelled")
        elif job["status"] == "running":
            with self.conn:
                self.conn.execute(
                    "UPDATE jobs SET status='cancelling',summary='正在取消',updated_at=? WHERE job_id=? AND status='running'",
                    (now(), key),
                )
        return self.get(key)
