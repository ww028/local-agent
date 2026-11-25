"""Knowledge-base retrieval tool.

Wraps the RAG retriever so the agent can look up relevant documents on demand
instead of receiving all chunks up front.
"""

from __future__ import annotations

from typing import Any

from app.agent.tools.base import ToolResult
from app.rag.retriever import Retriever


class KnowledgeTool:
    name = "search_knowledge_base"
    description = "Search the local Markdown knowledge base for relevant passages."

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        query = str(arguments.get("query", ""))
        chunks = await self._retriever.search(query, top_k=6)
        summary = "\n\n".join(f"- {c.heading or c.document_title}: {c.text}" for c in chunks)
        return ToolResult(output=summary, data={"chunks": [c.model_dump() for c in chunks]})
