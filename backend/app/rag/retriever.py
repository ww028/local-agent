"""Hybrid retrieval: embed the query, then search the vector store."""

from __future__ import annotations

from app.interfaces import EmbeddingModel, VectorStore
from app.schemas import RetrievedChunk


class Retriever:
    def __init__(self, embedding: EmbeddingModel, vector_store: VectorStore) -> None:
        self._embedding = embedding
        self._store = vector_store

    async def search(
        self,
        query: str,
        *,
        top_k: int,
        accessible_document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        vectors = await self._embedding.aembed([query])
        if not vectors:
            return []
        return await self._store.search(
            vectors[0],
            top_k=top_k,
            accessible_document_ids=accessible_document_ids,
        )
