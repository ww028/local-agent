"""Knowledge pipeline integration tests using a deterministic embedding."""

import asyncio

import pytest

from app.config import Settings
from app.ingest.chunker import chunk_markdown
from app.knowledge import KnowledgeService
from app.store.db import get_connection
from app.store.documents import DocumentRepository
from app.store.vector_store import LanceDBStore


class Embedding:
    fail = False

    async def aembed(self, texts):
        if self.fail:
            raise ValueError("unavailable")
        return [[1.0, 0.0, 0.0] if "蓝莓" in text else [0.0, 1.0, 0.0] for text in texts]


@pytest.mark.asyncio
async def test_ingest_search_delete_rebuild(tmp_path):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        db_path=tmp_path / "test.db",
        lancedb_dir=tmp_path / "lance",
    )
    conn = get_connection(settings)
    service = KnowledgeService(
        settings, DocumentRepository(conn), LanceDBStore(settings), Embedding()
    )
    await service.start()
    try:
        doc = await service.ingest(
            "test.md", "# 项目\n\n## 参数\n\n蓝莓项目的超时时间是73秒。".encode()
        )
        await asyncio.wait_for(service.queue.join(), 5)
        assert service.repo.get(doc["document_id"])["status"] == "ready"
        result = await service.search("蓝莓超时时间")
        assert "73秒" in result[0]["text"]
        assert "参数" in service.preview(doc["document_id"])["chunks"][-1]["heading"]
        await service.reindex(doc["document_id"])
        await service.queue.join()
        await service.delete(doc["document_id"])
        assert await service.search("蓝莓") == []
        assert not list(service.files.iterdir())
    finally:
        await service.stop()
        conn.close()


@pytest.mark.asyncio
async def test_failure_then_retry(tmp_path):
    s = Settings(
        _env_file=None,
        data_dir=tmp_path,
        db_path=tmp_path / "test.db",
        lancedb_dir=tmp_path / "lance",
    )
    conn = get_connection(s)
    embedding = Embedding()
    embedding.fail = True
    service = KnowledgeService(s, DocumentRepository(conn), LanceDBStore(s), embedding)
    await service.start()
    try:
        doc = await service.ingest("x.md", b"hello")
        await service.queue.join()
        assert service.repo.get(doc["document_id"])["status"] == "error"
        embedding.fail = False
        await service.reindex(doc["document_id"])
        await service.queue.join()
        assert service.repo.get(doc["document_id"])["status"] == "ready"
        with pytest.raises(ValueError):
            await service.ingest("bad.exe", b"hello")
        with pytest.raises(ValueError):
            await service.ingest("x.md", b"a" * (4 * 1024 * 1024 + 1))
    finally:
        await service.stop()
        conn.close()


def test_fences_and_invalid_overlap():
    chunks = chunk_markdown(
        "# H\n```python\n# not heading\n```\n## D\ntext", chunk_size=200, overlap=0, document_id="x"
    )
    assert len(chunks) == 2
    assert chunks[0].heading == "H" and chunks[1].heading == "H / D"
    with pytest.raises(ValueError):
        chunk_markdown("x", chunk_size=10, overlap=10, document_id="x")
