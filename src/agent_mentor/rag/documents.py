from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath

from docx import Document as DocxDocument
from pypdf import PdfReader

from agent_mentor.api.errors import AppError


@dataclass(frozen=True, slots=True)
class ParsedSection:
    text: str
    heading_path: list[str]
    page_number: int | None = None
    block_type: str = "paragraph"


class DocumentParser:
    supported_extensions = {".md", ".txt", ".pdf", ".docx"}

    def __init__(self, max_pdf_pages: int) -> None:
        self._max_pdf_pages = max_pdf_pages

    def parse(self, filename: str, content: bytes) -> list[ParsedSection]:
        suffix = PurePath(filename).suffix.lower()
        if suffix not in self.supported_extensions:
            raise AppError(
                "UNSUPPORTED_DOCUMENT", "Only Markdown, TXT, PDF and DOCX are supported."
            )
        if suffix in {".md", ".txt"}:
            return self._parse_text(
                content.decode("utf-8", errors="replace"), markdown=suffix == ".md"
            )
        if suffix == ".pdf":
            return self._parse_pdf(content)
        return self._parse_docx(content)

    @staticmethod
    def _parse_text(text: str, *, markdown: bool) -> list[ParsedSection]:
        text = text.lstrip("\ufeff")
        current_path: list[str] = []
        buffer: list[str] = []
        sections: list[ParsedSection] = []
        in_fenced_code = False
        for line in text.splitlines():
            if markdown and line.strip().startswith("```"):
                in_fenced_code = not in_fenced_code
                buffer.append(line)
                continue
            if (
                markdown
                and not in_fenced_code
                and line.startswith("#")
                and line.lstrip("#").startswith(" ")
            ):
                if buffer:
                    sections.append(
                        ParsedSection(
                            "\n".join(buffer).strip(),
                            current_path.copy(),
                            block_type=infer_block_type("\n".join(buffer)),
                        )
                    )
                    buffer = []
                level = len(line) - len(line.lstrip("#"))
                title = line[level:].strip()
                current_path = current_path[: level - 1] + [title]
            else:
                buffer.append(line)
        if buffer:
            sections.append(
                ParsedSection(
                    "\n".join(buffer).strip(),
                    current_path.copy(),
                    block_type=infer_block_type("\n".join(buffer)),
                )
            )
        return [section for section in sections if section.text]

    def _parse_pdf(self, content: bytes) -> list[ParsedSection]:
        reader = PdfReader(BytesIO(content))
        if len(reader.pages) > self._max_pdf_pages:
            raise AppError("PDF_PAGE_LIMIT", f"PDF must have at most {self._max_pdf_pages} pages.")
        sections = [
            ParsedSection(
                (page.extract_text() or "").strip(),
                [],
                number + 1,
                infer_block_type(page.extract_text() or ""),
            )
            for number, page in enumerate(reader.pages)
        ]
        sections = [section for section in sections if section.text]
        if not sections:
            raise AppError(
                "SCANNED_PDF_UNSUPPORTED", "Scanned PDFs require OCR and are not supported."
            )
        return sections

    @staticmethod
    def _parse_docx(content: bytes) -> list[ParsedSection]:
        document = DocxDocument(BytesIO(content))
        path: list[str] = []
        buffer: list[str] = []
        sections: list[ParsedSection] = []
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue
            style = ((paragraph.style.name if paragraph.style is not None else "") or "").lower()
            if style.startswith("heading"):
                if buffer:
                    sections.append(
                        ParsedSection(
                            "\n".join(buffer),
                            path.copy(),
                            block_type=infer_block_type("\n".join(buffer)),
                        )
                    )
                    buffer = []
                level_text = "".join(character for character in style if character.isdigit())
                level = int(level_text or "1")
                path = path[: level - 1] + [text]
            else:
                buffer.append(text)
        if buffer:
            sections.append(
                ParsedSection(
                    "\n".join(buffer),
                    path.copy(),
                    block_type=infer_block_type("\n".join(buffer)),
                )
            )
        if not sections:
            raise AppError("EMPTY_DOCUMENT", "The document does not contain extractable text.")
        return sections


def infer_block_type(text: str) -> str:
    stripped = text.strip()
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if not stripped:
        return "unknown"
    if stripped.startswith("```") or stripped.endswith("```"):
        return "code"
    if lines and all(line.startswith(("- ", "* ", "+ ")) for line in lines[: min(3, len(lines))]):
        return "list"
    if _looks_like_table(lines):
        return "table"
    if len(lines) == 1 and (lines[0].startswith("#") or len(lines[0]) <= 80):
        return "heading" if lines[0].startswith("#") else "paragraph"
    return "paragraph"


def _looks_like_table(lines: list[str]) -> bool:
    if len(lines) < 2:
        return False
    pipe_rows = [line for line in lines if line.count("|") >= 2]
    if len(pipe_rows) >= 2:
        return True
    tab_rows = [line for line in lines if line.count("\t") >= 1]
    return len(tab_rows) >= 2
