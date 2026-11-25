"""Layered memory.

- Short-term: messages within the current conversation.
- Long-term: persisted preferences and facts, backed by the SQLite repository.

The split keeps conversation context separate from durable knowledge.
"""

from __future__ import annotations

from app.schemas import ChatMessage


class Memory:
    def __init__(self) -> None:
        self._short_term: list[ChatMessage] = []

    def add(self, message: ChatMessage) -> None:
        self._short_term.append(message)

    def recent(self, limit: int = 10) -> list[ChatMessage]:
        return self._short_term[-limit:]

    def clear(self) -> None:
        self._short_term.clear()
