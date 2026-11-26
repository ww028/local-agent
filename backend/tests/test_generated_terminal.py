"""Generated plans have no functional action enum; authorization stays immutable."""

import asyncio
import sys

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.terminal.catalog import digest
from app.terminal.plans import build_generated, verify_generated
from app.terminal.runner import execute_step
from tests.test_terminal import PlanningModel, config, wait


class ScriptModel(PlanningModel):
    async def tool_chat(self, *args, **kwargs):
        return {
            "tool_calls": [
                {
                    "function": {
                        "name": "propose_terminal_plan",
                        "arguments": {
                            "goal": "合成脚本输出",
                            "steps": [
                                {
                                    "kind": "shell",
                                    "script": "printf 'synthetic\\n' | tr a-z A-Z > result.txt; cat result.txt",
                                    "description": "临时测试管道和写入",
                                }
                            ],
                        },
                    }
                }
            ]
        }


def test_generated_exec_no_action_catalog(tmp_path):
    plan = build_generated(
        tmp_path,
        ".",
        {"goal": "query", "steps": [{"program": "/bin/pwd", "args": ["-P"], "description": "pwd"}]},
    )
    assert plan["requires_risk_ack"] and not plan["requires_high_risk_ack"]
    assert verify_generated(tmp_path, plan, digest(plan)) == plan
    plan["steps"][0]["args"].append("other")
    with pytest.raises(ValueError):
        verify_generated(tmp_path, plan, digest(plan))
    custom = build_generated(
        tmp_path,
        ".",
        {
            "goal": "code",
            "steps": [
                {
                    "program": sys.executable,
                    "args": ["-I", "-c", "print('synthetic')"],
                    "description": "Python脚本",
                }
            ],
        },
    )
    assert custom["requires_high_risk_ack"] and custom["requires_network_ack"]


def test_shell_requires_all_acks_and_runs_once(tmp_path):
    app = create_app(config(tmp_path), ScriptModel())
    with TestClient(app, base_url="http://127.0.0.1") as c:
        key = c.post("/api/terminal", json={"instruction": "写合成结果"}).json()["task_id"]
        task = wait(c, key, {"awaiting_confirmation"})
        assert not (tmp_path / "result.txt").exists() and not task["steps"]
        body = {"plan_hash": task["plan_hash"]}
        assert c.post(f"/api/terminal/{key}/confirm", json=body).status_code == 409
        body["risk_acknowledged"] = True
        assert c.post(f"/api/terminal/{key}/confirm", json=body).status_code == 409
        body["high_risk_acknowledged"] = True
        assert c.post(f"/api/terminal/{key}/confirm", json=body).status_code == 409
        body["network_acknowledged"] = True
        assert c.post(f"/api/terminal/{key}/confirm", json=body).status_code == 200
        assert c.post(f"/api/terminal/{key}/confirm", json=body).status_code == 200
        done = wait(c, key, {"completed", "failed"})
        assert done["status"] == "completed" and len(done["steps"]) == 1
        assert (tmp_path / "result.txt").read_text() == "SYNTHETIC\n"
        assert done["steps"][0]["stdout"] == "SYNTHETIC\n"


@pytest.mark.parametrize("script", ["sudo anything", "cat ~/.ssh/id_rsa"])
def test_obvious_privilege_credential_inputs_rejected(tmp_path, script):
    with pytest.raises(ValueError):
        build_generated(
            tmp_path,
            ".",
            {"goal": "x", "steps": [{"kind": "shell", "script": script, "description": "test"}]},
        )


@pytest.mark.asyncio
async def test_non_whitelisted_exec_real_run(tmp_path):
    plan = build_generated(
        tmp_path,
        ".",
        {
            "goal": "custom",
            "steps": [
                {
                    "program": sys.executable,
                    "args": ["-I", "-c", "print(7*11)"],
                    "description": "运行Python合成表达式",
                }
            ],
        },
    )
    result = await execute_step(plan["steps"][0], plan, lambda out, err: None)
    assert result["stdout"] == "77\n" and result["exit_code"] == 0


def test_unknown_program_and_shell_mutation(tmp_path):
    with pytest.raises(ValueError, match="不可用"):
        build_generated(
            tmp_path,
            ".",
            {"goal": "x", "steps": [{"program": "missing-synthetic-program", "description": "x"}]},
        )
    plan = build_generated(
        tmp_path,
        ".",
        {"goal": "shell", "steps": [{"kind": "shell", "script": "printf ok", "description": "x"}]},
    )
    old = digest(plan)
    plan["steps"][0]["script"] = "printf changed"
    with pytest.raises(ValueError):
        verify_generated(tmp_path, plan, old)
    with pytest.raises(ValueError):
        verify_generated(tmp_path, plan, digest(plan))


@pytest.mark.asyncio
async def test_generated_without_saved_approval_never_executes(tmp_path):
    app = create_app(config(tmp_path), PlanningModel())
    async with app.router.lifespan_context(app):
        plan = build_generated(
            tmp_path, ".", {"goal": "x", "steps": [{"program": "/bin/pwd", "description": "x"}]}
        )
        key = app.state.terminal.repo.create("x", "test:local", ".")["task_id"]
        app.state.terminal.repo.save_plan(key, plan)
        # Repository-level fixture bypass still cannot reach process launch.
        app.state.terminal.repo.confirm(key, digest(plan))
        for _ in range(200):
            task = app.state.terminal.repo.get(key)
            if task["status"] == "failed":
                break
            await asyncio.sleep(0.01)
        assert task["status"] == "failed" and task["steps"] == []
        assert "账号权限" in task["error"]


def test_memory_unit_explanation_is_deterministic():
    from app.terminal.service import memory_summary

    plan = {"steps": [{"executable": "/usr/sbin/sysctl", "args": ["-n", "hw.memsize"]}]}
    text = memory_summary(plan, [{"exit_code": 0, "stdout": "51539607552\n"}])
    assert "48 GiB" in text and "51.54 GB" in text
    assert memory_summary(plan, [{"exit_code": 1, "stdout": "51539607552"}]) is None


@pytest.mark.asyncio
async def test_shell_pipefail_and_relative_executable(tmp_path):
    script = tmp_path / "demo.sh"
    script.write_text("#!/bin/sh\nprintf 'relative-ok\\n'\n")
    script.chmod(0o700)
    plan = build_generated(
        tmp_path,
        ".",
        {"goal": "relative", "steps": [{"program": "./demo.sh", "description": "synthetic"}]},
    )
    assert verify_generated(tmp_path, plan, digest(plan)) == plan
    result = await execute_step(plan["steps"][0], plan, lambda out, err: None)
    assert result["stdout"] == "relative-ok\n"
    piped = build_generated(
        tmp_path,
        ".",
        {
            "goal": "pipefail",
            "steps": [
                {"kind": "shell", "script": "false | cat", "description": "synthetic failure"}
            ],
        },
    )
    result = await execute_step(piped["steps"][0], piped, lambda out, err: None)
    assert result["status"] == "failed" and result["exit_code"] != 0


def test_requested_pipeline_cannot_be_split_into_disconnected_execs(tmp_path):
    with TestClient(
        create_app(config(tmp_path), PlanningModel()), base_url="http://127.0.0.1"
    ) as c:
        key = c.post("/api/terminal", json={"instruction": "通过管道输出合成结果"}).json()[
            "task_id"
        ]
        task = wait(c, key, {"failed"})
        assert "管道" in task["error"] and not task["steps"]
