"""Local-only Ollama adapter. Never uses proxies or downloads models implicitly."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence

import httpx

from app.config import Settings
from app.schemas import ChatMessage


class ModelError(Exception):
    """Safe user-facing error, without upstream paths or response bodies."""


class OllamaChatModel:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._settings = settings
        self._transport = transport

    def _client(self, *, discovery: bool = False) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._settings.ollama_base_url, transport=self._transport,
            trust_env=False, follow_redirects=False,
            timeout=httpx.Timeout(5 if discovery else self._settings.model_timeout_seconds,
                                  connect=3, pool=3),
        )

    async def list_models(self) -> list[dict]:
        try:
            async with self._client(discovery=True) as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
                if response.is_redirect:
                    raise ModelError("Ollama redirects are not allowed.")
                data = response.json()
                return [{"name": m["name"], "size": m.get("size", 0)}
                        for m in data["models"] if isinstance(m.get("name"), str)]
        except httpx.HTTPError as exc:
            raise ModelError("Ollama unavailable. Start the local service and retry.") from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise ModelError("Invalid model list from Ollama.") from exc

    async def validate_model(self, name: str) -> None:
        models = await self.list_models()
        if name not in {m["name"] for m in models}:
            raise ModelError("Model is not installed locally. Select an installed model.")
        # Reject downloaded cloud stubs and embedding-only models.
        try:
            async with self._client(discovery=True) as client:
                response = await client.post("/api/show", json={"model": name})
                response.raise_for_status()
                data = response.json()
                capabilities = data.get("capabilities", [])
                if (data.get("remote_model") or data.get("remote_host")
                        or "cloud" in name.lower() or "completion" not in capabilities):
                    raise ModelError("Select a local chat model; cloud and embedding models are blocked.")
        except httpx.HTTPError as exc:
            raise ModelError("Could not verify the local model capabilities.") from exc
        except (ValueError, TypeError) as exc:
            raise ModelError("Invalid model metadata from Ollama.") from exc

    async def achat(
        self, messages: Sequence[ChatMessage], *, model: str, stream: bool = True,
        num_ctx: int | None = None, temperature: float | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "stream": stream,
            "think": False,  # Phase 1 renders answers only, not reasoning streams.
            "options": {"num_ctx": num_ctx or self._settings.num_ctx,
                        "num_predict": self._settings.num_predict,
                        **({"temperature": temperature} if temperature is not None else {})},
        }
        try:
            async with self._client() as client:
                if not stream:
                    response = await client.post("/api/chat", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    if data.get("error"):
                        raise ModelError("Local model rejected the request.")
                    yield data["message"]["content"]
                    return
                async with client.stream("POST", "/api/chat", json=payload) as response:
                    response.raise_for_status()
                    completed = False
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        if data.get("error"):
                            raise ModelError("Local model failed during generation.")
                        text = data.get("message", {}).get("content", "")
                        if text:
                            yield text
                        if data.get("done"):
                            completed = True
                            break
                    if not completed:
                        raise ModelError("Model stream ended before completion. Please retry.")
        except httpx.TimeoutException as exc:
            raise ModelError("Local model timed out. Try a shorter prompt or smaller model.") from exc
        except httpx.HTTPError as exc:
            raise ModelError("Local model request failed. Check Ollama and the installed model.") from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise ModelError("Invalid response from the local model.") from exc


class OllamaEmbeddingModel:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def aembed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(
            base_url=self._settings.ollama_base_url, trust_env=False, timeout=120
        ) as client:
            response = await client.post("/api/embed", json={
                "model": self._settings.embedding_model, "input": list(texts), "truncate": False,
            })
            response.raise_for_status()
            return response.json()["embeddings"]
