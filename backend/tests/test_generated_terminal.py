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
    # pwd is a provable read-only query, so it runs without a confirmation click.
    assert (
        plan["auto_run"] and not plan["requires_high_risk_ack"] and not plan["requires_network_ack"]
    )
    assert plan["effects"] == ["只读取信息，不会修改文件或系统设置"]
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
    assert not custom["auto_run"]


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
            tmp_path,
            ".",
            {
                "goal": "x",
                "steps": [
                    {"kind": "shell", "script": "printf x > y.txt", "description": "写入合成文件"}
                ],
            },
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
        assert "确认" in task["error"] and not (tmp_path / "y.txt").exists()


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


def test_transcript_is_chronological_and_bounded(tmp_path):
    app = create_app(config(tmp_path), PlanningModel())
    with TestClient(app, base_url="http://127.0.0.1") as c:
        keys = [
            c.post("/api/terminal", json={"instruction": f"需求{i}"}).json()["task_id"]
            for i in range(3)
        ]
        tasks = c.get("/api/terminal/transcript?limit=2").json()["tasks"]
        assert [t["task_id"] for t in tasks] == keys[1:]
        assert all("plan" in t and "steps" in t for t in tasks)
        assert c.get("/api/terminal/transcript?limit=1").json()["tasks"][0]["task_id"] == keys[2]


def test_session_context_is_untrusted_and_bounded(tmp_path):
    from app.config import Settings
    from app.store.db import get_connection
    from app.store.terminal import TerminalRepository
    from app.terminal.service import session_context

    conn = get_connection(
        Settings(_env_file=None, data_dir=tmp_path, db_path=tmp_path / "db.sqlite")
    )
    repo = TerminalRepository(conn)
    done = repo.create("查看内存", "m", ".")
    repo.save_plan(done["task_id"], {"steps": [{"command": "sysctl -n hw.memsize"}]})
    repo.claim(done["task_id"])
    repo.start_step(done["task_id"], 0)
    repo.finish_step(done["task_id"], 0, "completed", 0)
    repo.output(done["task_id"], 0, "x" * 5000, "")
    repo.finish(done["task_id"], "completed", None, "")
    current = repo.create("再看可用内存", "m", ".")
    entries = session_context(repo, current["task_id"])
    assert len(entries) == 1 and entries[0]["request"] == "查看内存"
    assert entries[0]["commands"] == ["sysctl -n hw.memsize"]
    assert len(entries[0]["output"]) <= 600
    assert session_context(repo, current["task_id"], limit=6) == entries


def test_requested_pipeline_cannot_be_split_into_disconnected_execs(tmp_path):

    with TestClient(
        create_app(config(tmp_path), PlanningModel()), base_url="http://127.0.0.1"
    ) as c:
        key = c.post("/api/terminal", json={"instruction": "通过管道输出合成结果"}).json()[
            "task_id"
        ]
        task = wait(c, key, {"failed"})
        assert "管道" in task["error"] and not task["steps"]


def test_cpu_model_intent_is_normalized_to_brand_string():
    from app.terminal.plans import normalize_for_intent

    arch = {
        "goal": "x",
        "steps": [{"program": "/usr/bin/uname", "args": ["-m"], "description": "架构"}],
    }
    fixed = normalize_for_intent("查一下我电脑cpu的型号", arch)
    assert fixed["steps"][0]["program"] == "/usr/sbin/sysctl"
    assert fixed["steps"][0]["args"] == ["-n", "machdep.cpu.brand_string"]
    assert normalize_for_intent("我的电脑是什么架构", arch) == arch


def test_git_version_auto_runs_and_generic_exec_effects_are_explicit(tmp_path):
    plan = build_generated(
        tmp_path,
        ".",
        {
            "goal": "git 版本",
            "steps": [
                {"program": "/usr/bin/git", "args": ["--version"], "description": "git 版本"}
            ],
        },
    )
    assert plan["auto_run"] is True
    generic = build_generated(
        tmp_path,
        ".",
        {
            "goal": "运行脚本",
            "steps": [
                {
                    "program": sys.executable,
                    "args": ["-I", "-c", "print(1)"],
                    "description": "python",
                }
            ],
        },
    )
    assert "运行本机程序，可能读写文件" in generic["effects"] and not generic["auto_run"]


def test_version_query_fast_path_and_digest(tmp_path):
    from app.terminal.plans import detect_version_query, version_proposal
    from app.terminal.service import result_digest

    tool, executable = detect_version_query("我电脑的node版本号是多少？")
    assert tool == "node" and executable and executable.endswith("/node")
    assert detect_version_query("查看电脑内存和 node 版本") is None
    plan = build_generated(tmp_path, ".", version_proposal(tool, executable))
    assert plan["auto_run"] is True
    records = [{"exit_code": 0, "stdout": "v24.14.1\n", "stderr": ""}]
    assert result_digest(plan, records) == "Node.js 版本：24.14.1"


def test_read_only_shell_pipelines_skip_confirmation(tmp_path):
    from app.terminal.plans import read_only_script

    allowed = [
        "/bin/ls /Applications /usr/local/bin | grep -E 'mysql|postgres'",
        "which mysql; which psql 2>/dev/null",
        "find /usr/local -maxdepth 2 -name '*.db'",
        "ps aux | grep -i mysql",
        "launchctl list | grep mysql",
        "ls /Applications 2>&1 | head -20",
    ]
    refused = [
        "echo hi > /tmp/x",
        "find . -name x -delete",
        "curl -s http://example.com",
        "rm -rf /tmp/x",
        "sort in.txt -o out.txt",
        "sudo ls",
        "ls $(pwd)",
        "brew list",
        "echo hi &",
    ]
    assert all(read_only_script(s) for s in allowed)
    assert not any(read_only_script(s) for s in refused)
    plan = build_generated(
        tmp_path,
        ".",
        {
            "goal": "查数据库",
            "steps": [{"kind": "shell", "script": allowed[0], "description": "列出数据库相关"}],
        },
    )
    assert plan["auto_run"] is True
    assert plan["effects"] == ["只读取信息，不会修改文件或系统设置"]


def test_grep_alternation_and_no_match_digest(tmp_path):
    from app.terminal.plans import fix_grep_alternation, normalize_for_intent
    from app.terminal.service import result_digest

    script = "ls /opt/homebrew/bin | grep -i 'mysql\\|redis'"
    fixed = fix_grep_alternation(script)
    assert fixed == "ls /opt/homebrew/bin | grep -Ei 'mysql|redis'"
    proposal = normalize_for_intent(
        "查数据库",
        {"goal": "x", "steps": [{"kind": "shell", "script": script, "description": "x"}]},
    )
    assert proposal["steps"][0]["script"] == fixed
    plan = build_generated(tmp_path, ".", proposal)
    assert result_digest(plan, [{"exit_code": 1, "stdout": "", "stderr": ""}]).startswith(
        "没有找到匹配项"
    )


def test_inventory_scope_covers_real_install_dirs(tmp_path):
    from app.terminal.plans import normalize_for_intent

    script = "/bin/ls /Applications /usr/local/bin | grep -Ei 'mysql|redis'"
    proposal = {"goal": "x", "steps": [{"kind": "shell", "script": script, "description": "x"}]}
    scoped = normalize_for_intent("我的电脑上目前有啥数据库啊", proposal)["steps"][0]["script"]
    assert scoped.startswith("/bin/ls /Applications /usr/local/bin ")
    assert "/opt/homebrew/bin" in scoped
    plain = normalize_for_intent("列出目录", proposal)["steps"][0]["script"]
    assert plain == script


def test_observation_intent_blocks_any_writing_step():
    from app.terminal.plans import observation_proposal, writes_anything

    read = {"kind": "shell", "command": "ls -l /tmp | head -20"}
    assert observation_proposal("看一下 /tmp 里有哪些文件", [read]) is True
    assert writes_anything({"kind": "shell", "command": "cp a b"}) is True
    assert writes_anything({"kind": "shell", "command": "bash scripts/start.sh"}) is True
    assert writes_anything({"kind": "shell", "command": "python3 -c 'open(1)'"}) is True
    assert writes_anything({"kind": "exec", "command": "/usr/bin/git push"}) is True
    assert writes_anything({"kind": "shell", "command": "ls /tmp 2>/dev/null"}) is False
    rm = {"kind": "shell", "command": "rm -f /tmp/x"}
    assert observation_proposal("看看哪个文件能删掉", [rm]) is False
    # Statements that change a database are writes even inside a read-only client.
    assert writes_anything({"kind": "exec", "command": "/opt/homebrew/bin/mysql -e 'drop db x'"})
    assert writes_anything({"kind": "exec", "command": "/usr/bin/git branch -D feature"}) is True


def test_python_alias_hits_version_fast_path():
    from app.terminal.plans import detect_version_query

    resolved = detect_version_query("我的python 版本呢？")
    assert resolved is not None and resolved[0] == "python3"


def test_session_context_respects_byte_budget():
    import json

    from app.terminal.service import session_context

    class Repo:
        def __init__(self):
            self.tasks = [
                {
                    "task_id": f"t{i}",
                    "status": "completed",
                    "instruction": "查询" + "很长的需求" * 40,
                    "plan": {"steps": [{"command": "/bin/ls " + "x" * 80}]},
                    "steps": [{"stdout": "y" * 600, "stderr": "", "exit_code": 0}],
                }
                for i in range(8)
            ]

        def transcript(self, limit):
            return self.tasks[-limit:]

    full = session_context(Repo(), "t9", budget=None)
    tight = session_context(Repo(), "t9", budget=500)
    assert len(full) <= 6
    assert len(json.dumps(tight, ensure_ascii=False).encode()) <= 500
    assert tight == [] or tight[-1]["request"].startswith("查询")


def test_prompt_over_budget_reports_instead_of_overflowing(tmp_path):
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.main import create_app
    from tests.test_terminal import PlanningModel, wait

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data/db",
        lancedb_dir=tmp_path / "lance",
        terminal_workspace=tmp_path,
        llm_model="test:local",
        num_ctx=3072,
        num_predict=1024,
    )
    app = create_app(settings, PlanningModel())
    with TestClient(app, base_url="http://127.0.0.1") as c:
        response = c.post("/api/terminal", json={"instruction": "查一下磁盘空间"})
        assert response.status_code == 202, response.text
        task = wait(c, response.json()["task_id"], {"failed", "completed", "awaiting_confirmation"})
        assert task["status"] == "failed"
        assert "上下文预算" in (task["error"] or "")
