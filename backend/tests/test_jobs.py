"""Job lifecycle tests: HTTP returns first; worker owns execution and cancellation."""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.store.db import get_connection
from app.store.jobs import JobRepository
from tests.test_chat_api import FakeModel


class SlowModel(FakeModel):
    delay = 0.1
    fail_validation = False

    async def validate_model(self, name):
        if self.fail_validation:
            raise ValueError("Model unavailable")
        await super().validate_model(name)

    async def tool_chat(self, messages, **kwargs):
        await asyncio.sleep(self.delay)
        return {"content": "后台完成"}


def config(tmp_path):
    return Settings(
        _env_file=None,
        data_dir=tmp_path,
        db_path=tmp_path / "db",
        lancedb_dir=tmp_path / "lance",
        llm_model="test:local",
    )


def wait(client, key, statuses={"completed", "failed", "cancelled"}):
    for _ in range(100):
        result = client.get("/api/jobs/" + key).json()
        if result["status"] in statuses:
            return result
        time.sleep(0.01)
    raise AssertionError("Job did not finish")


def test_submit_finish_independent_and_persistent(tmp_path):
    app = create_app(config(tmp_path), SlowModel())
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post("/api/jobs", json={"instruction": "处理这个任务"})
        assert response.status_code == 202
        key = response.json()["job_id"]
        assert response.json()["status"] == "queued"
        # The submitting request has ended; unrelated reads do not own its worker.
        assert client.get("/api/models").status_code == 200
        result = wait(client, key)
        assert result["status"] == "completed" and result["result"] == "后台完成"
        assert result["events"]
        assert client.delete("/api/chats/" + result["conversation_id"]).status_code == 409
    with TestClient(
        create_app(config(tmp_path), SlowModel()), base_url="http://127.0.0.1"
    ) as client:
        assert client.get("/api/jobs/" + key).json()["result"] == "后台完成"


def test_cancel_queued_running_and_retry(tmp_path):
    model = SlowModel()
    model.delay = 3
    app = create_app(config(tmp_path), model)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        client.portal.call(app.state.chat_lock.acquire)
        key = client.post("/api/jobs", json={"instruction": "等待"}).json()["job_id"]
        assert client.post(f"/api/jobs/{key}/cancel").json()["status"] == "cancelled"
        client.portal.call(lambda: app.state.chat_lock.release())
        response = client.post(f"/api/jobs/{key}/retry")
        assert response.status_code == 202 and response.json()["job_id"] != key
        retried = response.json()["job_id"]
        wait(client, retried, {"running"})
        client.post(f"/api/jobs/{retried}/cancel")
        assert wait(client, retried)["status"] == "cancelled"
        model.delay = 0.01
        next_key = client.post("/api/jobs", json={"instruction": "新任务"}).json()["job_id"]
        assert wait(client, next_key)["status"] == "completed"
        assert client.post(f"/api/jobs/{next_key}/retry").status_code == 409


def test_validation_failure_and_scope(tmp_path):
    model = SlowModel()
    model.fail_validation = True
    with TestClient(create_app(config(tmp_path), model), base_url="http://127.0.0.1") as client:
        assert client.post("/api/jobs", json={"instruction": " "}).status_code == 422
        assert client.post("/api/jobs", json={"instruction": "x" * 2001}).status_code == 422
        key = client.post("/api/jobs", json={"instruction": "你好"}).json()["job_id"]
        assert wait(client, key)["status"] == "failed"
        model.fail_validation = False
        key = client.post("/api/jobs", json={"instruction": "8091端口占用"}).json()["job_id"]
        assert "未授权" in wait(client, key)["error"]
        assert client.get("/api/jobs?limit=1000").status_code == 422
        assert client.get("/api/jobs/missing").status_code == 404


def test_restart_marks_active_interrupted_and_keeps_queued(tmp_path):
    s = config(tmp_path)
    conn = get_connection(s)
    repo = JobRepository(conn)
    active = repo.create("x", "test:local")
    repo.claim(active["job_id"])
    queued = repo.create("y", "test:local")
    conn.close()
    conn = get_connection(s)
    repo = JobRepository(conn)
    assert repo.get(active["job_id"])["status"] == "interrupted"
    assert repo.get(queued["job_id"])["status"] == "queued"
    conn.close()


@pytest.mark.asyncio
async def test_shutdown_records_interruption(tmp_path):
    model = SlowModel()
    model.delay = 30
    app = create_app(config(tmp_path), model)
    async with app.router.lifespan_context(app):
        key = app.state.jobs.submit("hi", "test:local")["job_id"]
        for _ in range(100):
            if app.state.jobs.repo.get(key)["status"] == "running":
                break
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.01)
    conn = get_connection(config(tmp_path))
    assert JobRepository(conn).get(key)["status"] == "interrupted"
    conn.close()
