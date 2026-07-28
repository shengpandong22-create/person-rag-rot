from __future__ import annotations

from dataclasses import dataclass

from agent_mentor.rag.documents import ParsedSection


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    content: str
    heading_path: list[str]
    page_number: int | None
    block_type: str
    chunk_index: int
    token_count: int


def chunk_sections(sections: list[ParsedSection], size: int, overlap: int) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    for section in sections:
        if section.block_type == "code":
            text = section.text.strip()
        else:
            text = " ".join(section.text.split())
        start = 0
        while start < len(text):
            piece = text[start : start + size].strip()
            if piece:
                chunks.append(
                    ChunkDraft(
                        piece,
                        section.heading_path,
                        section.page_number,
                        section.block_type,
                        len(chunks),
                        len(piece.split()),
                    )
                )
            if start + size >= len(text):
                break
            start += max(1, size - overlap)
    if not chunks:
        from agent_mentor.api.errors import AppError

        raise AppError("EMPTY_DOCUMENT", "The document does not contain extractable text.")
    return chunks
