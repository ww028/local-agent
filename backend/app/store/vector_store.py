"""Embedded LanceDB adapter with serialized writes and threaded blocking calls."""

import asyncio

import lancedb

from app.config import Settings


class LanceDBStore:
    def __init__(self, settings: Settings):
        self.db = lancedb.connect(str(settings.lancedb_dir))
        self.lock = asyncio.Lock()

    def table(self):
        try:
            return self.db.open_table("chunks")
        except (ValueError, FileNotFoundError):
            return None

    async def upsert(self, *, document_id: str, chunks: list[dict], vectors: list[list[float]]):
        if len(chunks) != len(vectors) or not chunks:
            raise ValueError("Embedding count mismatch")
        rows = [
            {"chunk_id": c["chunk_id"], "document_id": document_id, "text": c["text"], "vector": v}
            for c, v in zip(chunks, vectors)
        ]
        async with self.lock:

            def write():
                table = self.table()
                if table is None:
                    self.db.create_table("chunks", data=rows)
                else:
                    table.delete(f"document_id = '{document_id}'")
                    table.add(rows)

            await asyncio.to_thread(write)

    async def search(self, vector: list[float], *, top_k: int, accessible_document_ids: list[str]):
        if not accessible_document_ids:
            return []
        async with self.lock:

            def query():
                table = self.table()
                if table is None:
                    return []
                scope = ",".join("'" + key + "'" for key in accessible_document_ids)
                return (
                    table.search(vector)
                    .metric("cosine")
                    .where(f"document_id IN ({scope})", prefilter=True)
                    .limit(top_k)
                    .to_list()
                )

            return await asyncio.to_thread(query)

    async def delete_document(self, key: str):
        async with self.lock:

            def remove():
                table = self.table()
                if table is not None:
                    table.delete(f"document_id = '{key}'")

            await asyncio.to_thread(remove)
