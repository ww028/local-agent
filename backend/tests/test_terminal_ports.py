"""Port plan confirmation and consistent offline diagnostic facts."""

import sys

import pytest
from fastapi.testclient import TestClient

from app.agent.diagnostics import DiagnosticError, port_result
from app.main import create_app
from app.terminal.catalog import build_plan, digest, verify_plan
from app.terminal.runner import execute_step
from app.terminal.service import requested_port
from tests.test_terminal import PlanningModel, config, wait


class PortModel(PlanningModel):
    async def tool_chat(self, messages, **kwargs):
        return {
            "tool_calls": [
                {
                    "function": {
                        "name": "propose_terminal_plan",
                        "arguments": {
                            "goal": "查询本机8092 TCP监听",
                            "actions": ["check_port"],
                            "port": 8092,
                        },
                    }
                }
            ]
        }


@pytest.mark.parametrize("value", [None, 0, 65536, True, "8092", "8092;anything"])
def test_strict_port_parameter(tmp_path, value):
    with pytest.raises(ValueError):
        build_plan(tmp_path, ".", {"goal": "test", "actions": ["check_port"], "port": value})


def test_port_bound_to_confirmation(tmp_path):
    plan = build_plan(tmp_path, ".", {"goal": "query", "actions": ["check_port"], "port": 8092})
    assert plan["steps"][0]["args"] == ["-nP", "-iTCP:8092", "-sTCP:LISTEN", "-Fpcn"]
    assert plan["steps"][0]["timeout_seconds"] == 5
    old = digest(plan)
    plan["steps"][0]["port"] = 8093
    with pytest.raises(ValueError):
        verify_plan(tmp_path, plan, old)
    with pytest.raises(ValueError):
        verify_plan(tmp_path, plan, digest(plan))
    assert requested_port("8092端口运行了什么服务？") == 8092
    for text in ("端口是什么服务", "8092和8093端口", "端口65536", "端口-8092", "端口8092.5"):
        with pytest.raises(ValueError):
            requested_port(text)


def test_port_result_success_empty_and_fail_closed():
    facts = port_result(8092, 0, "p123\ncnode\nf9\nn127.0.0.1:8092\n")
    assert facts["listening"] and facts["processes"][0]["pid"] == 123
    assert not port_result(8092, 1, "")["listening"]
    for code, out, err in (
        (1, "", "warning"),
        (0, "p123\ncnode\nn*:8092\n", "warning"),
        (0, "warning\np123\ncnode\nn*:8092\n", ""),
        (0, "p123\ncnode\n", ""),
    ):
        with pytest.raises(DiagnosticError):
            port_result(8092, code, out, err)


@pytest.mark.parametrize("mismatch", ["reject", "omit", "wrong_port"])
def test_model_cannot_skip_or_change_port_target(tmp_path, mismatch):
    class Wrong(PortModel):
        async def tool_chat(self, *args, **kwargs):
            proposal = {"goal": "wrong", "actions": ["check_port"], "port": 8093}
            if mismatch == "reject":
                proposal = {
                    "goal": "wrong",
                    "actions": [],
                    "unsupported_reason": "需要网络访问权限",
                }
            if mismatch == "omit":
                proposal = {"goal": "wrong", "actions": ["show_directory"]}
            return {
                "tool_calls": [
                    {"function": {"name": "propose_terminal_plan", "arguments": proposal}}
                ]
            }

    with TestClient(create_app(config(tmp_path), Wrong()), base_url="http://127.0.0.1") as c:
        key = c.post("/api/terminal", json={"instruction": "8092端口是什么服务"}).json()["task_id"]
        task = wait(c, key, {"failed"})
        assert "无需联网" in task["error"] and "需要网络访问权限" not in task["error"]
        assert not task["plan"] and not task["steps"]


def test_unconfirmed_port_does_not_execute_and_facts_persist(tmp_path, monkeypatch):
    with TestClient(create_app(config(tmp_path), PortModel()), base_url="http://127.0.0.1") as c:
        invented = c.post("/api/terminal", json={"instruction": "查看项目状态"}).json()["task_id"]
        rejected = wait(c, invented, {"failed"})
        assert not rejected["steps"] and "猜测" in rejected["error"]
    from app.terminal import service

    calls = []

    async def run(step, plan, output):
        calls.append(step)
        output("p123\ncnode\nn*:8092\n", "")
        return {
            "status": "completed",
            "exit_code": 0,
            "error": None,
            "facts": port_result(8092, 0, "p123\ncnode\nn*:8092\n"),
        }

    monkeypatch.setattr(service, "execute_step", run)
    app = create_app(config(tmp_path), PortModel())
    with TestClient(app, base_url="http://127.0.0.1") as c:
        key = c.post("/api/terminal", json={"instruction": "8092端口是什么服务"}).json()["task_id"]
        task = wait(c, key, {"awaiting_confirmation"})
        assert calls == [] and task["steps"] == []
        c.post(f"/api/terminal/{key}/confirm", json={"plan_hash": task["plan_hash"]})
        done = wait(c, key, {"completed"})
        assert len(calls) == 1
        assert done["steps"][0]["facts"]["port"] == 8092
    with TestClient(create_app(config(tmp_path), PortModel()), base_url="http://127.0.0.1") as c:
        assert c.get(f"/api/terminal/{key}").json()["steps"][0]["facts"]["listening"]


@pytest.mark.asyncio
async def test_runner_empty_listener_code_one_is_not_failure(tmp_path):
    step = {
        "executable": sys.executable,
        "args": ["-I", "-c", "import sys;sys.exit(1)"],
        "timeout_seconds": 1,
        "action": "check_port",
        "port": 8092,
    }
    result = await execute_step(
        step, {"cwd": str(tmp_path), "environment": {}}, lambda out, err: None
    )
    assert result["status"] == "completed" and result["exit_code"] == 1
    assert not result["facts"]["listening"]


def test_unsupported_reason_is_backend_owned(tmp_path):
    with pytest.raises(ValueError) as error:
        build_plan(
            tmp_path,
            ".",
            {"goal": "install", "actions": [], "unsupported_reason": "需要网络访问权限"},
        )
    assert "支持范围" in str(error.value) and "需要网络访问权限" not in str(error.value)
