"""Pluggable service interfaces.

The workflow layer (RAG, agent, routes) depends on these abstractions rather
than on concrete implementations. Swapping Ollama for another inference
backend, or LanceDB for another vector store, should only require providing
a new implementation of the relevant protocol.
"""

from __future__ import annotations

from typing import AsyncIterator, Protocol, Sequence

from app.schemas import ChatMessage, RetrievedChunk


class ChatModel(Protocol):
    """A chat / reasoning backend."""

    async def achat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str,
        stream: bool = True,
        num_ctx: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Yield response tokens. When ``stream`` is False, yield a single chunk."""
        ...


class EmbeddingModel(Protocol):
    """A text embedding backend."""

    async def aembed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input text."""
        ...


class VectorStore(Protocol):
    """A vector index supporting hybrid retrieval."""

    async def upsert(
        self,
        *,
        document_id: str,
        chunks: list[dict],
        vectors: list[list[float]],
    ) -> None:
        """Insert or replace all chunks of a document."""
        ...

    async def search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        accessible_document_ids: Sequence[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Return the most similar chunks, optionally scoped to allowed documents."""
        ...

    async def delete_document(self, document_id: str) -> None:
        """Remove every chunk belonging to a document."""
        ...
