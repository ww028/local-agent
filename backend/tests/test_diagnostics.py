"""Read-only diagnostics permissions, result parsing and subprocess cancellation."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.agent import diagnostics
from app.agent.toolbox import Tools


def test_parse():
    assert diagnostics.parse_lsof("p123\ncnode\nn127.0.0.1:8091\n") == [
        {"pid": 123, "process": "node", "listeners": ["127.0.0.1:8091"]}
    ]


@pytest.mark.asyncio
async def test_opt_in_and_parameters():
    tools = Tools(None)
    assert "check_port" not in tools.schemas
    with pytest.raises(ValueError):
        await tools.run("check_port", {"port": 8091})
    tools = Tools(None, allow_diagnostics=True)
    for value in (0, 65536, "8091", True):
        with pytest.raises(ValueError):
            await tools.run("check_port", {"port": value})


@pytest.mark.asyncio
async def test_lookup_success_free_failure(monkeypatch):
    monkeypatch.setattr(diagnostics.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(diagnostics.Path, "is_file", lambda _: True)
    monkeypatch.setattr(diagnostics.os, "access", lambda *_: True)
    runner = AsyncMock(return_value=(0, "p123\ncnode\nn127.0.0.1:8091\n"))
    monkeypatch.setattr(diagnostics, "run_fixed", runner)
    result = await diagnostics.check_port(8091)
    assert result["listening"] and result["processes"][0]["pid"] == 123
    assert runner.call_args.args[0] == [
        "/usr/sbin/lsof",
        "-nP",
        "-iTCP:8091",
        "-sTCP:LISTEN",
        "-Fpcn",
    ]
    runner.return_value = (1, "")
    assert not (await diagnostics.check_port(8091))["listening"]
    runner.return_value = (1, "lsof: permission denied")
    with pytest.raises(diagnostics.DiagnosticError):
        await diagnostics.check_port(8091)


@pytest.mark.asyncio
async def test_process_timeout_and_cancel(monkeypatch):
    class Reader:
        async def read(self, size):
            await asyncio.sleep(60)

    class Process:
        stdout = Reader()
        returncode = None
        terminated = False

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def kill(self):
            self.returncode = -9

        async def wait(self):
            return self.returncode

    first = Process()
    monkeypatch.setattr(
        diagnostics.asyncio, "create_subprocess_exec", AsyncMock(return_value=first)
    )
    with pytest.raises(diagnostics.DiagnosticError, match="timed out"):
        await diagnostics.run_fixed(["fixed"], timeout=0.01)
    assert first.terminated
    second = Process()
    monkeypatch.setattr(
        diagnostics.asyncio, "create_subprocess_exec", AsyncMock(return_value=second)
    )
    task = asyncio.create_task(diagnostics.run_fixed(["fixed"]))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert second.terminated
