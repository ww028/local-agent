"""Durable immutable plans and one-shot confirmation."""

import json
import uuid
from datetime import datetime, timedelta, timezone

from app.store.chats import now
from app.terminal.catalog import digest

TERMINAL = {"completed", "failed", "cancelled", "interrupted", "expired"}


class TerminalRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, instruction, model, relative):
        key = uuid.uuid4().hex
        with self.conn:
            count = self.conn.execute(
                "SELECT count(*) FROM terminal_tasks WHERE status NOT IN ('completed','failed','cancelled','interrupted','expired')"
            ).fetchone()[0]
            if count >= 16:
                raise ValueError("AI终端任务已达16个，请取消等待任务")
            self.conn.execute(
                "INSERT INTO terminal_tasks (task_id,instruction,model,relative_dir,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                (key, instruction, model, relative, "planning", now(), now()),
            )
        return self.get(key)

    def expire(self):
        with self.conn:
            self.conn.execute(
                "UPDATE terminal_tasks SET status='expired',error='确认已过期，请重新规划',updated_at=? WHERE status='awaiting_confirmation' AND expires_at<=?",
                (now(), now()),
            )

    def get(self, key):
        self.expire()
        row = self.conn.execute("SELECT * FROM terminal_tasks WHERE task_id=?", (key,)).fetchone()
        if not row:
            return None
        task = dict(row)
        task["plan"] = json.loads(task["plan"]) if task["plan"] else None
        task["steps"] = [
            dict(r)
            for r in self.conn.execute(
                "SELECT * FROM terminal_steps WHERE task_id=? ORDER BY step_index", (key,)
            )
        ]
        for step in task["steps"]:
            step["facts"] = json.loads(step["facts"]) if step.get("facts") else None
        return task

    def list(self, limit, offset):
        self.expire()
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT task_id,instruction,status,error,created_at FROM terminal_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        ]

    def transcript(self, limit):
        """Chronological recent tasks for a single console transcript view."""
        self.expire()
        keys = [
            row[0]
            for row in self.conn.execute(
                "SELECT task_id FROM terminal_tasks ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (limit,),
            )
        ]
        return [self.get(key) for key in reversed(keys)]

    def next(self, status):
        self.expire()
        row = self.conn.execute(
            "SELECT task_id FROM terminal_tasks WHERE status=? ORDER BY created_at LIMIT 1",
            (status,),
        ).fetchone()
        return self.get(row[0]) if row else None

    def save_plan(self, key, plan):
        expiry = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        with self.conn:
            self.conn.execute(
                "UPDATE terminal_tasks SET plan=?,plan_hash=?,expires_at=?,status='awaiting_confirmation',updated_at=? WHERE task_id=? AND status='planning'",
                (json.dumps(plan, ensure_ascii=False), digest(plan), expiry, now(), key),
            )

    def confirm(self, key, expected_hash, approval=None):
        task = self.get(key)
        if task is None:
            raise KeyError(key)
        if not task["plan_hash"] or expected_hash != task["plan_hash"]:
            raise ValueError("确认不对应当前计划")
        if (
            task["status"]
            in {
                "queued",
                "running",
                "completed",
                "failed",
                "cancelling",
                "interrupted",
                "cancelled",
            }
            and task["confirmed_at"]
        ):
            return task
        if task["status"] != "awaiting_confirmation":
            raise ValueError("计划不能确认或已过期")
        with self.conn:
            self.conn.execute(
                "UPDATE terminal_tasks SET status='queued',confirmed_at=?,updated_at=?,approval=? WHERE task_id=? AND status='awaiting_confirmation'",
                (now(), now(), json.dumps(approval or {}), key),
            )
        return self.get(key)

    def auto_confirm(self, key, approval=None):
        """Read-only plans may run without a click; recorded for audit."""
        with self.conn:
            self.conn.execute(
                "UPDATE terminal_tasks SET status='queued',confirmed_at=?,updated_at=?,approval=? WHERE task_id=? AND status='awaiting_confirmation'",
                (now(), now(), json.dumps(approval or {"auto_readonly": True}), key),
            )
        return self.get(key)

    def claim(self, key):
        with self.conn:
            r = self.conn.execute(
                "UPDATE terminal_tasks SET status='running',started_at=?,updated_at=? WHERE task_id=? AND status='queued'",
                (now(), now(), key),
            )
        return r.rowcount == 1

    def finish(self, key, status, error=None, summary="", digest=None):
        assert status in TERMINAL
        with self.conn:
            self.conn.execute(
                "UPDATE terminal_tasks SET status=?,error=?,summary=?,digest=?,finished_at=?,updated_at=? WHERE task_id=? AND status NOT IN ('completed','failed','cancelled','interrupted','expired')",
                (status, error, summary, digest, now(), now(), key),
            )

    def cancel(self, key):
        task = self.get(key)
        if task is None:
            raise KeyError(key)
        if task["status"] == "running":
            with self.conn:
                self.conn.execute(
                    "UPDATE terminal_tasks SET status='cancelling',updated_at=? WHERE task_id=?",
                    (now(), key),
                )
        elif task["status"] not in TERMINAL:
            self.finish(key, "cancelled")
        return self.get(key)

    def start_step(self, key, index):
        with self.conn:
            self.conn.execute(
                "INSERT INTO terminal_steps (task_id,step_index,status,started_at) VALUES (?,?,'running',?)",
                (key, index, now()),
            )

    def output(self, key, index, stdout, stderr):
        with self.conn:
            self.conn.execute(
                "UPDATE terminal_steps SET stdout=?,stderr=? WHERE task_id=? AND step_index=? AND status='running'",
                (stdout, stderr, key, index),
            )

    def save_facts(self, key, index, facts):
        with self.conn:
            self.conn.execute(
                "UPDATE terminal_steps SET facts=? WHERE task_id=? AND step_index=? AND status='running'",
                (json.dumps(facts, ensure_ascii=False), key, index),
            )

    def finish_step(self, key, index, status, exit_code=None, error=None):
        with self.conn:
            self.conn.execute(
                "UPDATE terminal_steps SET status=?,exit_code=?,error=?,finished_at=? WHERE task_id=? AND step_index=? AND status='running'",
                (status, exit_code, error, now(), key, index),
            )
