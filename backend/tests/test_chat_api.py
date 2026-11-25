"""Phase 1 API contract tests. Fake models never call a network or need weights."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.ollama_client import ModelError


class FakeModel:
    def __init__(self):
        self.calls = []
        self.fail = False

    async def list_models(self):
        return [{"name": "test:local", "size": 1}]

    async def validate_model(self, name):
        if name != "test:local":
            raise ModelError("Model is not installed locally.")

    async def achat(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        yield "hello "
        if self.fail:
            raise ModelError("Test model failed.")
        yield "世界"


@pytest.fixture
def setup(tmp_path):
    settings = Settings(_env_file=None, db_path=tmp_path / "chat.db",
                        data_dir=tmp_path, lancedb_dir=tmp_path / "lance", llm_model="test:local")
    model = FakeModel()
    return create_app(settings, model), model


def events(response):
    return [json.loads(frame[6:]) for frame in response.text.strip().split("\n\n")]


def send(client, **kwargs):
    return client.post("/api/chats/stream", json={"message": "你好", **kwargs})


def test_stream_history_and_model(setup):
    app, model = setup
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = send(client, model="test:local")
        assert response.status_code == 200
        frames = events(response)
        assert [f["type"] for f in frames] == ["meta", "token", "token", "done"]
        key = frames[0]["conversation_id"]
        saved = client.get(f"/api/chats/{key}").json()["messages"]
        assert saved[1]["content"] == "hello 世界"
        assert saved[1]["status"] == "complete"
        send(client, conversation_id=key)
        assert [m.role for m in model.calls[1][0]] == ["system", "user", "assistant", "user"]
        assert model.calls[0][1]["model"] == "test:local"
        assert client.get("/api/models").json()["available"][0]["name"] == "test:local"
        assert len(client.get("/api/chats").json()["conversations"]) == 1
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert len(client.get(f"/api/chats/{key}").json()["messages"]) == 4
        assert client.delete(f"/api/chats/{key}").status_code == 200
        assert client.get(f"/api/chats/{key}").status_code == 404


def test_failure_records_partial_and_releases_lock(setup):
    app, model = setup
    with TestClient(app, base_url="http://127.0.0.1") as client:
        model.fail = True
        frames = events(send(client))
        assert frames[-1]["type"] == "error"
        key = frames[0]["conversation_id"]
        saved = client.get(f"/api/chats/{key}").json()["messages"][1]
        assert saved["status"] == "error" and saved["content"] == "hello "
        model.fail = False
        assert send(client, conversation_id=key).status_code == 200
        assert len(model.calls[-1][0]) == 2  # Failed turn excluded from context.


def test_invalid_inputs_and_no_side_effects(setup):
    app, _ = setup
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert send(client, model="missing").status_code == 503
        assert send(client, conversation_id="missing").status_code == 404
        assert send(client, use_knowledge_base=True).status_code == 409
        assert send(client, message=" ").status_code == 422
        assert send(client, message="汉" * 4000).status_code == 413
        assert client.get("/api/chats").json()["conversations"] == []
        assert client.get("/api/documents").status_code == 200
        assert client.post("/api/chats/stream", json={"message": "x"},
                           headers={"Origin": "https://example.com"}).status_code == 403


def test_busy_and_delete_guard(setup):
    app, _ = setup
    with TestClient(app, base_url="http://127.0.0.1") as client:
        key = events(send(client))[0]["conversation_id"]
        client.portal.call(app.state.chat_lock.acquire)
        app.state.active_conversation = key
        assert send(client).status_code == 409
        assert client.delete(f"/api/chats/{key}").status_code == 409
        client.portal.call(lambda: app.state.chat_lock.release())
        app.state.active_conversation = None


@pytest.mark.asyncio
async def test_cancel_closes_generator_and_persists_partial(setup):
    from starlette.requests import Request

    from app.routes.chats import stream_chat
    from app.schemas import ChatRequest

    app, model = setup
    closed = []

    async def slow(messages, **kwargs):
        try:
            yield "partial"
            await asyncio.sleep(60)
        finally:
            closed.append(True)

    model.achat = slow
    async with app.router.lifespan_context(app):
        async def receive():
            await asyncio.sleep(3600)
        request = Request({"type": "http", "app": app, "headers": [], "method": "POST"}, receive=receive)
        response = await stream_chat(request, ChatRequest(message="hi"))
        iterator = response.body_iterator
        meta = json.loads((await anext(iterator))[6:])
        await anext(iterator)
        task = asyncio.create_task(anext(iterator))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await iterator.aclose()
        saved = app.state.chat_repo.messages(meta["conversation_id"])[1]
        assert saved["status"] == "interrupted" and saved["content"] == "partial"
        assert closed and not app.state.chat_lock.locked()
