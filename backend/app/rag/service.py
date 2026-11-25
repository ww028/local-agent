"""Question-answering service.

Coordinates retrieval (optional) and the chat model, streaming tokens back and
attaching citations from the retrieved chunks.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.config import Settings
from app.interfaces import ChatModel
from app.rag.composer import build_messages
from app.rag.retriever import Retriever
from app.schemas import ChatRequest, ChatStreamEvent, Citation, RetrievedChunk


class RagService:
    def __init__(
        self,
        settings: Settings,
        chat_model: ChatModel,
        retriever: Retriever,
    ) -> None:
        self._settings = settings
        self._chat = chat_model
        self._retriever = retriever

    async def answer(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
        chunks: list[RetrievedChunk] = []
        if request.use_knowledge_base:
            chunks = await self._retriever.search(
                request.message,
                top_k=request.top_k or self._settings.top_k,
            )
            citations = [
                Citation(
                    document_id=c.document_id,
                    document_title=c.document_title,
                    chunk_id=c.chunk_id,
                    heading=c.heading,
                    snippet=c.text,
                )
                for c in chunks
            ]
            yield ChatStreamEvent(type="citation", citations=citations)

        messages = build_messages(request.message, chunks)
        model = request.model or self._settings.llm_model
        async for token in self._chat.achat(messages, model=model, stream=True):
            yield ChatStreamEvent(type="token", content=token)
        yield ChatStreamEvent(type="done")
