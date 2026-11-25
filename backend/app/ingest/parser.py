"""Document parsing.

Currently handles Markdown with YAML frontmatter. PDF/Word parsers are reserved
as pluggable additions (see ``docs/roadmap.md``).
"""

from __future__ import annotations

from dataclasses import dataclass

import frontmatter


@dataclass
class ParsedDocument:
    title: str
    body: str
    metadata: dict


def parse_markdown(content: str, *, fallback_title: str) -> ParsedDocument:
    """Parse Markdown text, extracting frontmatter metadata and body."""
    post = frontmatter.loads(content)
    metadata = dict(post.metadata)
    title = str(metadata.get("title") or fallback_title).strip()
    return ParsedDocument(title=title, body=post.content.strip(), metadata=metadata)
