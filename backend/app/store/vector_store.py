"""LanceDB-backed vector store.

Implements the ``VectorStore`` interface. LanceDB handles semantic retrieval;
keyword (BM25) hybrid search can be layered on top later. The implementation
is wired to the interface so another store could replace it without touching
the RAG or agent layers.
"""

from __future__ import annotations

from typing import Sequence

from app.config import Settings
from app.schemas import RetrievedChunk


class LanceDBStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._db = None

    def _connect(self) -> None:
        if self._db is None:
            import lancedb

            self._settings.ensure_dirs()
            self._db = lancedb.connect(str(self._settings.lancedb_dir))

    async def upsert(
        self,
        *,
        document_id: str,
        chunks: list[dict],
        vectors: list[list[float]],
    ) -> None:
        self._connect()
        # TODO: open (or create) the chunks table, delete existing rows for this
        # document_id, then insert chunk metadata + vector columns.
        raise NotImplementedError("LanceDB upsert is not implemented yet.")

    async def search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        accessible_document_ids: Sequence[str] | None = None,
    ) -> list[RetrievedChunk]:
        self._connect()
        # TODO: run vector search, apply document-id filter when provided, map
        # rows back to RetrievedChunk.
        raise NotImplementedError("LanceDB search is not implemented yet.")

    async def delete_document(self, document_id: str) -> None:
        self._connect()
        # TODO: delete all rows matching document_id.
        raise NotImplementedError("LanceDB delete is not implemented yet.")
