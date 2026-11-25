"""Compose the prompt context from retrieved chunks.

Retrieved chunks are quoted with their source so the model can ground its
answer, and the same chunks are handed to the frontend for citation links.
"""

from __future__ import annotations

from app.schemas import ChatMessage, RetrievedChunk

SYSTEM_PROMPT = (
    "You are a local assistant. Answer honestly and concisely. "
    "When the provided context is relevant, base your answer on it and cite "
    "the source heading. If the context does not contain the answer, say so "
    "instead of inventing information."
)


def build_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return ""
    lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        heading = f" — {chunk.heading}" if chunk.heading else ""
        lines.append(f"[{idx}] {chunk.document_title}{heading}\n{chunk.text}")
    return "\n\n".join(lines)


def build_messages(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    history: list[ChatMessage] | None = None,
) -> list[ChatMessage]:
    context = build_context(chunks)
    user_content = question if not context else f"Context:\n{context}\n\nQuestion: {question}"
    messages: list[ChatMessage] = [ChatMessage(role="system", content=SYSTEM_PROMPT)]
    if history:
        messages.extend(history)
    messages.append(ChatMessage(role="user", content=user_content))
    return messages
