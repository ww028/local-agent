"""Confirmation boundary tests; fixtures are public synthetic project data."""

import asyncio
import sys
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.store.db import get_connection
from app.store.terminal import TerminalRepository
from app.terminal import runner
from app.terminal.catalog import build_plan, digest, resolve_directory, verify_plan, workspace_path
from tests.test_chat_api import FakeModel


class PlanningModel(FakeModel):
    async def tool_chat(self, messages, **kwargs):
        return {
            "tool_calls": [
                {
                    "function": {
                        "name": "propose_terminal_plan",
                        "arguments": {
                            "goal": "检查当前目录",
                            "actions": ["show_directory", "list_directory"],
                        },
                    }
                }
            ]
        }


def config(tmp_path):
    return Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data/db",
        lancedb_dir=tmp_path / "lance",
        terminal_workspace=tmp_path,
        llm_model="test:local",
    )


def wait(client, key, states):
    for _ in range(200):
        task = client.get("/api/terminal/" + key).json()
        if task["status"] in states:
            return task
        time.sleep(0.01)
    raise AssertionError(task)


def test_no_execution_before_confirmation_and_idempotency(tmp_path):
    app = create_app(config(tmp_path), PlanningModel())
    with TestClient(app, base_url="http://127.0.0.1") as c:
        r = c.post("/api/terminal", json={"instruction": "查看目录"})
        assert r.status_code == 202
        key = r.json()["task_id"]
        planned = wait(c, key, {"awaiting_confirmation"})
        assert planned["steps"] == []
        assert (
            c.post(f"/api/terminal/{key}/confirm", json={"plan_hash": "0" * 64}).status_code == 409
        )
        confirmed = c.post(f"/api/terminal/{key}/confirm", json={"plan_hash": planned["plan_hash"]})
        assert confirmed.status_code == 200
        assert (
            c.post(
                f"/api/terminal/{key}/confirm", json={"plan_hash": planned["plan_hash"]}
            ).status_code
            == 200
        )
        done = wait(c, key, {"completed", "failed"})
        assert done["status"] == "completed" and len(done["steps"]) == 2
        assert str(tmp_path) in done["steps"][0]["stdout"]
        assert all(step["exit_code"] == 0 for step in done["steps"])
        assert (
            c.post("/api/terminal", json={"instruction": "x", "command": "anything"}).status_code
            == 422
        )
    with TestClient(
        create_app(config(tmp_path), PlanningModel()), base_url="http://127.0.0.1"
    ) as c:
        assert c.get("/api/terminal/" + key).json()["status"] == "completed"


@pytest.mark.parametrize("relative", ["..", "../escape", "/", ".git", "data", ".ssh", ".env"])
def test_directory_boundaries(tmp_path, relative):
    with pytest.raises((ValueError, OSError)):
        resolve_directory(tmp_path, relative)


def test_symlink_and_plan_mutation(tmp_path):
    (tmp_path / "linked").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        resolve_directory(tmp_path, "linked")
    plan = build_plan(tmp_path, ".", {"goal": "cwd", "actions": ["show_directory"]})
    original = digest(plan)
    plan["steps"][0]["args"].append("unexpected")
    with pytest.raises(ValueError):
        verify_plan(tmp_path, plan, original)
    with pytest.raises(ValueError):
        verify_plan(tmp_path, plan, digest(plan))
    for root in ("/", str(__import__("pathlib").Path.home())):
        with pytest.raises(ValueError):
            workspace_path(root)
    with pytest.raises(ValueError):
        build_plan(tmp_path, ".", {"goal": "x", "actions": ["shell"]})


def test_expiry_cancel_and_recovery(tmp_path):
    settings = config(tmp_path)
    conn = get_connection(settings)
    repo = TerminalRepository(conn)
    task = repo.create("x", "local", ".")
    plan = build_plan(tmp_path, ".", {"goal": "x", "actions": ["show_directory"]})
    repo.save_plan(task["task_id"], plan)
    conn.execute(
        "UPDATE terminal_tasks SET expires_at='2000-01-01' WHERE task_id=?", (task["task_id"],)
    )
    conn.commit()
    with pytest.raises(ValueError):
        repo.confirm(task["task_id"], digest(plan))
    assert repo.get(task["task_id"])["status"] == "expired"
    active = repo.create("x", "local", ".")
    repo.save_plan(active["task_id"], plan)
    repo.confirm(active["task_id"], digest(plan))
    repo.claim(active["task_id"])
    queued = repo.create("y", "local", ".")
    repo.save_plan(queued["task_id"], plan)
    repo.confirm(queued["task_id"], digest(plan))
    conn.close()
    conn = get_connection(settings)
    repo = TerminalRepository(conn)
    assert repo.get(active["task_id"])["status"] == "interrupted"
    assert repo.get(queued["task_id"])["status"] == "queued"
    repo.cancel(queued["task_id"])
    repo.finish(queued["task_id"], "completed")
    assert repo.get(queued["task_id"])["status"] == "cancelled"
    conn.close()


def test_model_cannot_expand_catalog(tmp_path):
    class Unsupported(PlanningModel):
        async def tool_chat(self, *args, **kwargs):
            return {
                "tool_calls": [
                    {
                        "function": {
                            "name": "propose_terminal_plan",
                            "arguments": {"goal": "x", "actions": ["shell"]},
                        }
                    }
                ]
            }

    with TestClient(create_app(config(tmp_path), Unsupported()), base_url="http://127.0.0.1") as c:
        key = c.post("/api/terminal", json={"instruction": "unsupported"}).json()["task_id"]
        task = wait(c, key, {"failed"})
        assert not task["steps"] and not task["plan"]


@pytest.mark.asyncio
async def test_runner_real_output_failure_timeout_limit_and_cancel(tmp_path):
    # Direct unit-level runner fixture only; API catalog never exposes -c.
    def step(script, timeout=1):
        return {
            "executable": sys.executable,
            "args": ["-I", "-c", script],
            "timeout_seconds": timeout,
        }

    plan = {"cwd": str(tmp_path), "environment": {}}
    outputs = []

    def record(out, err):
        outputs.append((out, err))

    result = await runner.execute_step(step('print("synthetic")'), plan, record)
    assert result["stdout"] == "synthetic\n" and result["exit_code"] == 0
    result = await runner.execute_step(
        step('import sys;sys.stderr.write("failure");sys.exit(2)'), plan, record
    )
    assert result["status"] == "failed" and result["exit_code"] == 2
    result = await runner.execute_step(step("import time;time.sleep(60)", 0.02), plan, record)
    assert result["status"] == "failed" and "预算" in result["error"]
    result = await runner.execute_step(step('print("x"*200000)'), plan, record)
    assert "128KiB" in result["error"] and len(result["stdout"]) <= runner.LIMIT
    task = asyncio.create_task(
        runner.execute_step(step("import time;time.sleep(60)"), plan, record)
    )
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert runner.display_text(b"\x1b[31mplain\x00\x1b[0m") == "plain"


@pytest.mark.asyncio
async def test_service_running_cancel_and_shutdown(tmp_path, monkeypatch):
    from app.terminal import service

    entered = asyncio.Event()
    closed = asyncio.Event()

    async def slow(step, plan, output):
        entered.set()
        try:
            await asyncio.sleep(60)
        finally:
            closed.set()

    monkeypatch.setattr(service, "execute_step", slow)
    app = create_app(config(tmp_path), PlanningModel())
    async with app.router.lifespan_context(app):
        plan = build_plan(tmp_path, ".", {"goal": "cwd", "actions": ["show_directory"]})
        task = app.state.terminal.repo.create("x", "test:local", ".")
        key = task["task_id"]
        app.state.terminal.repo.save_plan(key, plan)
        app.state.terminal.confirm(key, digest(plan))
        await asyncio.wait_for(entered.wait(), 2)
        await app.state.terminal.cancel(key)
        await asyncio.wait_for(closed.wait(), 2)
        for _ in range(100):
            if app.state.terminal.repo.get(key)["status"] == "cancelled":
                break
            await asyncio.sleep(0.01)
        assert app.state.terminal.repo.get(key)["steps"][0]["status"] == "cancelled"
        entered.clear()
        closed.clear()
        next_task = app.state.terminal.repo.create("y", "test:local", ".")
        next_key = next_task["task_id"]
        app.state.terminal.repo.save_plan(next_key, plan)
        app.state.terminal.confirm(next_key, digest(plan))
        await asyncio.wait_for(entered.wait(), 2)
    conn = get_connection(config(tmp_path))
    assert TerminalRepository(conn).get(next_key)["status"] == "interrupted"
    assert closed.is_set()
    conn.close()


def test_cancel_unconfirmed_and_queue_capacity(tmp_path):
    with TestClient(
        create_app(config(tmp_path), PlanningModel()), base_url="http://127.0.0.1"
    ) as c:
        key = c.post("/api/terminal", json={"instruction": "list"}).json()["task_id"]
        planned = wait(c, key, {"awaiting_confirmation"})
        assert c.post(f"/api/terminal/{key}/cancel").json()["status"] == "cancelled"
        assert (
            c.post(
                f"/api/terminal/{key}/confirm", json={"plan_hash": planned["plan_hash"]}
            ).status_code
            == 409
        )
        assert c.get(f"/api/terminal/{key}").json()["steps"] == []
    conn = get_connection(config(tmp_path))
    repo = TerminalRepository(conn)
    for _ in range(16):
        repo.create("x", "local", ".")
    with pytest.raises(ValueError):
        repo.create("extra", "local", ".")
    conn.close()
