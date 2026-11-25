"""Ollama protocol tests with httpx MockTransport (no network)."""

import json

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.ollama_client import ModelError, OllamaChatModel
from app.schemas import ChatMessage


def settings():
    return Settings(_env_file=None)


@pytest.mark.parametrize("url", ["https://example.com", "http://192.168.0.10", "http://user@localhost", "http://localhost/path"])
def test_local_only(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ollama_base_url=url)


@pytest.mark.asyncio
async def test_unicode_and_payload():
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, text='{"message":{"content":"你"}}\n'
                              '{"message":{"content":"好"},"done":true}\n')

    model = OllamaChatModel(settings(), httpx.MockTransport(handler))
    output = [token async for token in model.achat([ChatMessage(role="user", content="问")], model="local")]
    assert output == ["你", "好"]
    assert captured[0]["options"]["num_predict"] == 1024


@pytest.mark.asyncio
@pytest.mark.parametrize("body", ['{"message":{"content":"partial"}}\n', 'not-json\n', '{"error":"private server detail"}\n'])
async def test_stream_errors(body):
    model = OllamaChatModel(settings(), httpx.MockTransport(lambda _: httpx.Response(200, text=body)))
    with pytest.raises(ModelError) as result:
        _ = [token async for token in model.achat([], model="local")]
    assert "private server detail" not in str(result.value)


@pytest.mark.asyncio
async def test_connection_failure():
    def handler(request):
        raise httpx.ConnectError("private detail", request=request)
    model = OllamaChatModel(settings(), httpx.MockTransport(handler))
    with pytest.raises(ModelError, match="unavailable"):
        await model.list_models()


@pytest.mark.asyncio
@pytest.mark.parametrize("metadata", [{"capabilities": ["embedding"]},
                                         {"capabilities": ["completion"], "remote_host": "remote"}])
async def test_embedding_and_cloud_blocked(metadata):
    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local"}]})
        return httpx.Response(200, json=metadata)
    model = OllamaChatModel(settings(), httpx.MockTransport(handler))
    with pytest.raises(ModelError, match="blocked"):
        await model.validate_model("local")


@pytest.mark.asyncio
async def test_local_chat_allowed():
    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "local"}]})
        return httpx.Response(200, json={"capabilities": ["completion", "tools"]})
    await OllamaChatModel(settings(), httpx.MockTransport(handler)).validate_model("local")
