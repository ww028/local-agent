"""Bounded local indexing queue and hybrid retrieval orchestration."""

import asyncio
import hashlib
import re
import uuid
from pathlib import Path

from app.ingest.chunker import chunk_markdown


class KnowledgeService:
    def __init__(self, settings, repository, vector_store, embedding):
        self.settings, self.repo, self.store, self.embedding = (
            settings,
            repository,
            vector_store,
            embedding,
        )
        self.queue = asyncio.Queue(maxsize=32)
        self.worker = None
        self.operation = asyncio.Lock()
        self.files = settings.data_dir / "files"
        self.files.mkdir(parents=True, exist_ok=True)

    async def start(self):
        self.worker = asyncio.create_task(self._work())
        for doc in self.repo.list_all():
            if doc["status"] == "pending":
                await self.queue.put(doc["document_id"])

    async def stop(self):
        self.worker.cancel()
        try:
            await self.worker
        except asyncio.CancelledError:
            pass

    async def ingest(self, filename: str, data: bytes):
        if Path(filename).suffix.lower() not in {".md", ".markdown", ".txt"}:
            raise ValueError("Only Markdown and TXT files are supported")
        if not data or len(data) > 4 * 1024 * 1024:
            raise ValueError("Document must be nonempty and smaller than 4 MB")
        text = data.decode("utf-8-sig")
        if not text.strip() or "\x00" in text:
            raise ValueError("Invalid text document")
        if self.queue.full():
            raise ValueError("Index queue full; wait for current documents")
        digest = hashlib.sha256(data).hexdigest()
        for doc in self.repo.list_all():
            if doc["content_hash"] == digest:
                return doc
        key = uuid.uuid4().hex
        chunks = chunk_markdown(
            text,
            chunk_size=self.settings.chunk_size,
            overlap=self.settings.chunk_overlap,
            document_id=key,
        )
        title = re.search(r"^#\s+(.+)$", text, re.M)
        title = title[1][:200] if title else Path(filename).name[:200]
        path = self.files / (key + ".md")
        path.write_text(text)
        self.repo.add(
            key, title, Path(filename).name, hashlib.sha256(data).hexdigest(), len(data), chunks
        )
        await self.queue.put(key)
        return self.repo.get(key)

    async def reindex(self, key):
        doc = self.repo.get(key)
        if not doc:
            raise KeyError(key)
        if doc["status"] in {"pending", "indexing"}:
            raise ValueError("Document is already queued or indexing")
        if self.queue.full():
            raise ValueError("Index queue full")
        self.repo.status(key, "pending")
        await self.queue.put(key)

    async def _work(self):
        while True:
            key = await self.queue.get()
            try:
                async with self.operation:
                    if not self.repo.get(key):
                        continue
                    chunks = self.repo.chunks(key)
                    self.repo.status(key, "indexing")
                    vectors = []
                    for start in range(0, len(chunks), 8):
                        result = await self.embedding.aembed(
                            [c["text"] for c in chunks[start : start + 8]]
                        )
                        if len(result) != len(chunks[start : start + 8]):
                            raise ValueError("Embedding count mismatch")
                        vectors.extend(result)
                        self.repo.status(key, "indexing", len(vectors))
                    await self.store.upsert(document_id=key, chunks=chunks, vectors=vectors)
                    self.repo.status(key, "ready", len(chunks))
            except asyncio.CancelledError:
                self.repo.status(key, "pending")
                raise
            except Exception:
                self.repo.status(
                    key, "error", error="Index failed. Check local embedding model and retry."
                )
            finally:
                self.queue.task_done()

    async def delete(self, key):
        async with self.operation:
            if not self.repo.get(key):
                raise KeyError(key)
            # Hide from all retrieval before touching the secondary index.
            self.repo.status(key, "deleting")
            await self.store.delete_document(key)
            self.repo.delete(key)
            (self.files / (key + ".md")).unlink(missing_ok=True)

    def preview(self, key):
        doc = self.repo.get(key)
        if not doc:
            raise KeyError(key)
        return {
            "document": doc,
            "content": (self.files / (key + ".md")).read_text(),
            "chunks": self.repo.chunks(key),
        }

    async def search(self, query: str, top_k=6):
        if not self.repo.ready_ids():
            return []
        vector = (await self.embedding.aembed([query]))[0]
        semantic = await self.store.search(
            vector, top_k=top_k * 3, accessible_document_ids=self.repo.ready_ids()
        )
        lexical = self.repo.lexical(query, top_k * 3)
        scores = {}
        for rows in (semantic, lexical):
            for rank, row in enumerate(rows):
                key = row["chunk_id"]
                scores[key] = scores.get(key, 0) + 1 / (60 + rank + 1)
        ordered = sorted(scores, key=scores.get, reverse=True)[:top_k]
        result = []
        for key in ordered:
            row = self.repo.conn.execute(
                "SELECT c.*,d.title document_title FROM chunks c JOIN documents d ON c.document_id=d.document_id WHERE c.chunk_id=? AND d.status='ready'",
                (key,),
            ).fetchone()
            if row:
                result.append({**dict(row), "score": scores[key]})
        return result
