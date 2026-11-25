"""Safe tool and model-driven Agent loop regressions."""

import pytest

from app.agent.executor import Executor
from app.agent.toolbox import Tools, calculate
from app.config import Settings
from app.schemas import ChatMessage
from app.store.db import get_connection
from app.store.runs import RunRepository


@pytest.mark.parametrize("expression", ["__import__('os')", "x+1", "2**10000", "[1]", "1/0"])
def test_calculator_rejects(expression):
    with pytest.raises((ValueError, SyntaxError, ZeroDivisionError)):
        calculate(expression)


def test_calculator():
    assert calculate("(73 * 4) + 8 / 2") == 296


@pytest.mark.asyncio
async def test_model_tools_and_run_persistence(tmp_path):
    class Model:
        count = 0

        async def tool_chat(self, messages, **kwargs):
            self.count += 1
            if self.count == 1:
                return {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "calculator", "arguments": {"expression": "73*4"}}}
                    ],
                }
            assert "292" in messages[-1]["content"]
            return {"role": "assistant", "content": "结果为292"}

    settings = Settings(_env_file=None, data_dir=tmp_path, db_path=tmp_path / "test.db")
    conn = get_connection(settings)
    runs = RunRepository(conn)
    key = runs.create("x", 1, "local")
    executor = Executor(Model(), Tools(None), runs)
    events = [
        e
        async for e in executor.run(
            key,
            [ChatMessage(role="system", content="local"), ChatMessage(role="user", content="73*4")],
            "local",
        )
    ]
    assert events[-1]["content"] == "结果为292"
    assert any(e.get("event", {}).get("kind") == "tool_result" for e in events)
    runs.finish(key, "complete")
    assert runs.get(key)["status"] == "complete"
    assert len(runs.get(key)["events"]) == 4
    conn.close()


@pytest.mark.asyncio
async def test_unknown_tool():
    with pytest.raises(ValueError):
        await Tools(None).run("shell", {"cmd": "anything"})
