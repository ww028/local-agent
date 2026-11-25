"""Tests for heading-aware Markdown chunking."""

from app.ingest.chunker import chunk_markdown


def test_chunks_carry_nearest_heading() -> None:
    markdown = "# Intro\n\nHello.\n\n## Detail\n\nWorld."
    chunks = chunk_markdown(markdown, chunk_size=100, overlap=10, document_id="doc")
    headings = [c.heading for c in chunks]
    assert headings[0] == "Intro"
    assert "Intro / Detail" in headings


def test_long_section_is_split_with_overlap() -> None:
    body = "a" * 250
    markdown = "# Big\n\n" + body
    chunks = chunk_markdown(markdown, chunk_size=100, overlap=20, document_id="doc")
    assert len(chunks) >= 2
    # Overlap region repeats between consecutive pieces.
    assert chunks[1].text[:20] == chunks[0].text[-20:]


def test_empty_text_produces_no_chunks() -> None:
    assert chunk_markdown("", chunk_size=100, overlap=10, document_id="doc") == []
