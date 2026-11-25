"""Heading-aware Markdown slicing with fence and source-line tracking."""

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_id: str
    heading: str | None
    text: str
    order: int
    start_line: int = 1
    end_line: int = 1


def chunk_markdown(
    markdown: str, *, chunk_size: int, overlap: int, document_id: str
) -> list[Chunk]:
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Invalid chunk size/overlap")
    lines = markdown.splitlines(keepends=True)
    sections = []
    start = 0
    headings: list[tuple[int, str]] = []
    heading = None
    fence = None
    for i, line in enumerate(lines):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            char = marker[1][0]
            if fence is None:
                fence = char
            elif fence == char:
                fence = None
            continue
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line.rstrip()) if fence is None else None
        if match:
            if i > start:
                sections.append((heading, start, i))
            level, title = len(match[1]), match[2]
            headings = [(depth, text) for depth, text in headings if depth < level]
            headings.append((level, title))
            heading = " / ".join(text for _, text in headings)
            start = i
    sections.append((heading, start, len(lines)))
    chunks = []
    for heading, first, last in sections:
        text = "".join(lines[first:last])
        offset = 0
        while offset < len(text):
            end = min(offset + chunk_size, len(text))
            piece = text[offset:end]
            if piece.strip():
                order = len(chunks)
                chunks.append(
                    Chunk(
                        f"{document_id}:{order}",
                        heading,
                        piece,
                        order,
                        first + text[:offset].count("\n") + 1,
                        first + text[:end].count("\n") + 1,
                    )
                )
            if end == len(text):
                break
            offset = end - overlap
    return chunks
