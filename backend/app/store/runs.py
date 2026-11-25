"""Durable Agent run/event records."""

import json
import uuid

from app.store.chats import now


class RunRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, conversation_id, message_id, model):
        key = uuid.uuid4().hex
        with self.conn:
            self.conn.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?,?)",
                (key, conversation_id, message_id, "running", model, now(), now()),
            )
            self.conn.execute("UPDATE messages SET run_id=? WHERE id=?", (key, message_id))
        return key

    def event(self, key, kind, data):
        seq = (
            self.conn.execute("SELECT count(*) FROM run_events WHERE run_id=?", (key,)).fetchone()[
                0
            ]
            + 1
        )
        record = {"seq": seq, "kind": kind, "data": data, "created_at": now()}
        with self.conn:
            self.conn.execute(
                "INSERT INTO run_events VALUES (?,?,?,?,?)",
                (key, seq, kind, json.dumps(data, ensure_ascii=False), record["created_at"]),
            )
        return record

    def finish(self, key, status):
        with self.conn:
            self.conn.execute(
                "UPDATE runs SET status=?,updated_at=? WHERE run_id=?", (status, now(), key)
            )

    def get(self, key):
        row = self.conn.execute("SELECT * FROM runs WHERE run_id=?", (key,)).fetchone()
        if not row:
            return None
        events = [
            {**dict(e), "data": json.loads(e["data"])}
            for e in self.conn.execute(
                "SELECT * FROM run_events WHERE run_id=? ORDER BY seq", (key,)
            )
        ]
        return {**dict(row), "events": events}
