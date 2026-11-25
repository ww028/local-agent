"""Ollama implementation of the chat and embedding interfaces.

Talks to a local Ollama instance over HTTP. This is the default backend; the
interfaces in ``app.interfaces`` allow swapping in another inference provider.
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Sequence

import httpx

from app.config import Settings
from app.schemas import ChatMessage


class OllamaChatModel:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def achat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str,
        stream: bool = True,
        num_ctx: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "stream": stream,
            "options": {
                "num_ctx": num_ctx or self._settings.num_ctx,
                **({"temperature": temperature} if temperature is not None else {}),
            },
        }
        async with httpx.AsyncClient(base_url=self._settings.ollama_base_url) as client:
            if not stream:
                resp = await client.post("/api/chat", json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                yield data.get("message", {}).get("content", "")
                return

            async with client.stream("POST", "/api/chat", json=payload, timeout=120) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content")
                    if content:
                        yield content
                    if chunk.get("done"):
                        break


class OllamaEmbeddingModel:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def aembed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {"model": self._settings.embedding_model, "input": list(texts)}
        async with httpx.AsyncClient(base_url=self._settings.ollama_base_url) as client:
            resp = await client.post("/api/embed", json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json().get("embeddings", [])
