"""Integrated API tests for knowledge citations, Agent records and session rename."""

import json

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.test_chat_api import FakeModel
from tests.test_knowledge import Embedding


class ToolModel(FakeModel):
    tool_count = 0

    async def tool_chat(self, messages, **kwargs):
        self.tool_count += 1
        if self.tool_count % 2 == 1:
            return {
                "content": "",
                "tool_calls": [
                    {"function": {"name": "calculator", "arguments": {"expression": "2+3"}}}
                ],
            }
        return {"content": "5"}


def test_end_to_end_mock(tmp_path):
    s = Settings(
        _env_file=None,
        data_dir=tmp_path,
        db_path=tmp_path / "test.db",
        lancedb_dir=tmp_path / "lance",
        llm_model="test:local",
    )
    app = create_app(s, ToolModel())
    with TestClient(app, base_url="http://127.0.0.1") as c:
        app.state.knowledge.embedding = Embedding()
        uploaded = c.post("/api/documents", files={"file": ("test.md", "# 参数\n蓝莓超时73秒。")})
        assert uploaded.status_code == 200
        key = uploaded.json()["document_id"]
        c.portal.call(app.state.knowledge.queue.join)
        result = c.post("/api/chats/stream", json={"message": "蓝莓超时", "mode": "knowledge"})
        assert result.status_code == 200
        frames = [
            json.loads(line[6:]) for line in result.text.splitlines() if line.startswith("data: ")
        ]
        assert any(f["type"] == "citation" for f in frames)
        conversation = frames[0]["conversation_id"]
        assert c.get("/api/chats/" + conversation).json()["messages"][-1]["citations"]
        assert (
            c.patch("/api/chats/" + conversation, json={"title": "新标题"}).json()["title"]
            == "新标题"
        )
        assert c.patch("/api/chats/" + conversation, json={"title": " "}).status_code == 422
        result = c.post("/api/chats/stream", json={"message": "2+3", "mode": "agent"})
        frames = [
            json.loads(line[6:]) for line in result.text.splitlines() if line.startswith("data: ")
        ]
        run = frames[0]["run_id"]
        assert c.get("/api/runs/" + run).json()["status"] == "complete"
        assert c.get("/api/runs/" + run).json()["events"][1]["data"]["tool"] == "calculator"
        assert (
            c.post("/api/chats/stream", json={"message": "x", "temperature": 5}).status_code == 422
        )
        assert c.get("/api/documents/../../etc/passwd").status_code == 404
        assert c.delete("/api/documents/" + key).status_code == 200
        assert c.post("/api/knowledge/search", json={"query": "蓝莓"}).json()["chunks"] == []
