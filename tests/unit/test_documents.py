from __future__ import annotations

from io import BytesIO

from docx import Document

from agent_mentor.rag.chunking import chunk_sections
from agent_mentor.rag.documents import DocumentParser


def test_markdown_parser_preserves_heading_path() -> None:
    sections = DocumentParser(200).parse(
        "guide.md", b"# RAG\nGrounded answers.\n## Citations\nShow sources."
    )

    assert sections[0].heading_path == ["RAG"]
    assert sections[1].heading_path == ["RAG", "Citations"]


def test_docx_parser_and_chunker() -> None:
    document = Document()
    document.add_heading("Agent", level=1)
    document.add_paragraph("A personal learning assistant should retain evidence.")
    buffer = BytesIO()
    document.save(buffer)

    chunks = chunk_sections(DocumentParser(200).parse("guide.docx", buffer.getvalue()), 30, 5)

    assert chunks[0].heading_path == ["Agent"]
    assert chunks[0].content
