"""Markdown chunking.

Splits along heading boundaries first, then falls back to character-length
splitting for sections that are too long. Chunks carry their nearest heading
so retrieved answers can cite a location. Sizing is character-based, which
suits Chinese text better than English token counts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Chunk:
    chunk_id: str
    heading: str | None
    text: str
    order: int


def _split_sections(markdown: str) -> list[tuple[str | None, str]]:
    """Return ``(heading, body)`` pairs in document order."""
    sections: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in markdown.splitlines():
        match = HEADING_RE.match(line)
        if match:
            if current_lines or current_heading is not None:
                sections.append((current_heading, current_lines))
            current_heading = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    sections.append((current_heading, current_lines))

    return [(heading, "\n".join(lines).strip()) for heading, lines in sections if lines]


def _split_long_text(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        pieces.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return pieces


def chunk_markdown(
    markdown: str,
    *,
    chunk_size: int,
    overlap: int,
    document_id: str,
) -> list[Chunk]:
    """Chunk a Markdown document into overlapping, heading-aware pieces."""
    chunks: list[Chunk] = []
    order = 0
    for heading, body in _split_sections(markdown):
        for piece in _split_long_text(body, chunk_size, overlap):
            if not piece.strip():
                continue
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}:{order}",
                    heading=heading,
                    text=piece,
                    order=order,
                )
            )
            order += 1
    return chunks
