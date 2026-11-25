"""Ingestion pipeline: parse -> chunk -> embed -> index -> persist metadata.

The pipeline depends on the interfaces in ``app.interfaces`` so the embedding
model and vector store can be replaced independently.
"""

from __future__ import annotations

import uuid

from app.config import Settings
from app.ingest.chunker import chunk_markdown
from app.ingest.parser import parse_markdown
from app.interfaces import EmbeddingModel, VectorStore


class IngestPipeline:
    def __init__(
        self,
        settings: Settings,
        embedding: EmbeddingModel,
        vector_store: VectorStore,
    ) -> None:
        self._settings = settings
        self._embedding = embedding
        self._vector_store = vector_store

    async def ingest_markdown(self, content: str, *, source_name: str) -> str:
        document_id = uuid.uuid4().hex
        parsed = parse_markdown(content, fallback_title=source_name)

        chunks = chunk_markdown(
            parsed.body,
            chunk_size=self._settings.chunk_size,
            overlap=self._settings.chunk_overlap,
            document_id=document_id,
        )
        vectors = await self._embedding.aembed([c.text for c in chunks])

        records = [
            {
                "chunk_id": c.chunk_id,
                "heading": c.heading,
                "text": c.text,
                "order": c.order,
                "document_title": parsed.title,
            }
            for c in chunks
        ]
        await self._vector_store.upsert(
            document_id=document_id,
            chunks=records,
            vectors=vectors,
        )
        # TODO: persist document metadata and chunk rows to the SQLite repository.
        return document_id
