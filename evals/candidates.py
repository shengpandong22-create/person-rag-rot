"""Build candidate evidence packages for human labelling.

What this does
--------------
For each legacy (unlabelled) positive case, search the parsed course documents
for sections that plausibly answer the question, and emit a **candidate**
package for a human to confirm or reject.

What this deliberately does NOT do
---------------------------------
* It never writes ``label_origin=human``.  Every emitted row is marked
  ``model_suggested`` so a machine suggestion can never masquerade as a human
  label.
* It never uses a chunk UUID as the label.  Candidates carry
  ``document_logical_name`` + ``heading_path`` (stable across rebuilds) plus a
  content fingerprint of the section text, so a label can be re-resolved even
  if chunk ids change.
* It never auto-accepts a candidate.  Suggestions are ranked and capped, and
  the reviewer must pick.

The fingerprint is a SHA-256 over the normalised section text.  It is a
*verification aid*, not a substitute for the location: it lets a reviewer see
that the section they are labelling has not silently changed since review.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evals.schema import RetrievalEvalCase

CANDIDATES_PER_CASE = 5
MIN_SCORE = 1.0
MODEL_SUGGESTED = "model_suggested"
NEEDS_REVIEW = "needs_review"

ENGLISH_STOPWORDS = {
    "about",
    "and",
    "are",
    "does",
    "for",
    "from",
    "how",
    "into",
    "the",
    "this",
    "what",
    "when",
    "where",
    "which",
    "why",
    "with",
}


@dataclass(frozen=True, slots=True)
class SectionRecord:
    """One parsed document section, addressable without a chunk UUID."""

    document_logical_name: str
    heading_path: tuple[str, ...]
    block_type: str
    text: str
    fingerprint: str

    @property
    def location(self) -> str:
        return f"{self.document_logical_name} > {' > '.join(self.heading_path)}"


@dataclass(frozen=True, slots=True)
class Candidate:
    document_logical_name: str
    heading_path: tuple[str, ...]
    evidence_excerpt: str
    suggested_answer_points: tuple[str, ...]
    content_fingerprint: str
    score: float

    def to_json(self) -> dict[str, Any]:
        return {
            "document_logical_name": self.document_logical_name,
            "heading_path": list(self.heading_path),
            "evidence_excerpt": self.evidence_excerpt,
            "suggested_answer_points": list(self.suggested_answer_points),
            "content_fingerprint": self.content_fingerprint,
            "match_score": round(self.score, 4),
            "review_status": NEEDS_REVIEW,
        }


@dataclass(frozen=True, slots=True)
class CaseCandidatePackage:
    case_id: str
    question: str
    answerability: str
    diagnostic_keywords: tuple[str, ...]
    candidates: tuple[Candidate, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.case_id,
            "question": self.question,
            "answerability": self.answerability,
            "diagnostic_keywords": list(self.diagnostic_keywords),
            "suggested_by": MODEL_SUGGESTED,
            "human_verified": False,
            "candidates": [item.to_json() for item in self.candidates],
            "notes": list(self.notes),
        }


def content_fingerprint(text: str) -> str:
    """Stable fingerprint of section text, insensitive to markdown reflow.

    Normalisation is deliberately aggressive about layout but conservative
    about words:

    * markdown table padding is collapsed so re-aligning a table does not
      change the fingerprint
    * ``**bold**`` and backticks are stripped so emphasis edits are ignored
    * remaining whitespace is collapsed

    What must NOT be normalised is the actual wording: if a fact is edited the
    fingerprint must change, otherwise it would fail its purpose of letting a
    reviewer detect that a labelled section drifted.
    """
    without_tables = re.sub(r"[ \t]*\|[ \t]*", " | ", text)
    without_tables = re.sub(r"^\s*\|[\s|:-]+\|\s*$", "", without_tables, flags=re.MULTILINE)
    cleaned = without_tables.replace("**", "").replace("`", "")
    normalised = re.sub(r"\s+", " ", cleaned).strip()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def section_terms(text: str) -> set[str]:
    """Terms used for candidate ranking; mirrors the evidence-term idea."""
    lowered = text.lower()
    terms = {
        match.group(0)
        for match in re.finditer(r"[a-z0-9_.+#-]{2,}", lowered)
        if match.group(0) not in ENGLISH_STOPWORDS
    }
    for segment in re.findall(r"[\u4e00-\u9fff]{2,}", lowered):
        terms.update(segment[index : index + 2] for index in range(len(segment) - 1))
    return terms


def score_section(case: RetrievalEvalCase, section: SectionRecord) -> float:
    """Rank a section against a question. Higher means more plausible."""
    question = case.question
    score = 0.0
    for keyword in case.diagnostic_keywords:
        if keyword and keyword.casefold() in section.text.casefold():
            score += 3.0
    heading_text = " ".join(section.heading_path).casefold()
    question_terms = section_terms(question)
    heading_overlap = sum(1 for term in question_terms if term in heading_text)
    score += heading_overlap * 2.0
    body_overlap = sum(1 for term in question_terms if term in section.text.casefold())
    if question_terms:
        score += (body_overlap / len(question_terms)) * 4.0
    if section.block_type in {"table", "list"}:
        # Structured teaching content is more likely to state a crisp answer.
        score += 0.3
    return score


def suggest_answer_points(section: SectionRecord, limit: int = 3) -> tuple[str, ...]:
    """Extract candidate answer points from the section as a review aid.

    These are quoted fragments, not paraphrases: a reviewer must be able to see
    the original wording, because an invented paraphrase would be exactly the
    kind of unsupported claim the project is trying to eliminate.

    Markdown scaffolding is filtered out aggressively.  Table separator rows
    (``| --- | --- |``), fence markers and pure heading lines carry no answer
    content, and emitting them as "answer points" would waste reviewer time
    and could be mistaken for a rubric.
    """
    points: list[str] = []
    for raw in section.text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("```"):
            continue
        if _is_table_separator(stripped):
            continue
        cleaned = re.sub(r"^[#>\-*\d.)\]]+\s*", "", stripped).strip()
        cleaned = cleaned.replace("**", "").replace("`", "").strip()
        if cleaned.startswith("|"):
            cleaned = _table_row_to_text(cleaned)
        if len(cleaned) < 8 or _is_scaffolding(cleaned):
            continue
        points.append(cleaned[:160])
        if len(points) >= limit:
            break
    if not points:
        collapsed = " ".join(section.text.split())
        if collapsed:
            points.append(collapsed[:160])
    return tuple(points)


def _is_table_separator(line: str) -> bool:
    """True for markdown table alignment rows such as ``| --- | :--- |``."""
    stripped = line.strip().strip("|").strip()
    if not stripped:
        return False
    return bool(stripped) and set(stripped) <= {"-", ":", " ", "|"}


def _table_row_to_text(line: str) -> str:
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    return " — ".join(cell for cell in cells if cell)


def _is_scaffolding(text: str) -> bool:
    """Reject lines that are structure rather than content."""
    if set(text) <= {"-", "|", ":", " ", "—"}:
        return True
    if re.fullmatch(r"[\d.\s]+", text):
        return True
    return text in {"---", "***", "___"}


def build_candidates(
    case: RetrievalEvalCase,
    sections: Sequence[SectionRecord],
    *,
    limit: int = CANDIDATES_PER_CASE,
    min_score: float = MIN_SCORE,
) -> tuple[Candidate, ...]:
    scored = [(score_section(case, section), section) for section in sections]
    ranked = sorted(
        (item for item in scored if item[0] >= min_score),
        key=lambda item: (-item[0], item[1].document_logical_name, item[1].heading_path),
    )
    candidates: list[Candidate] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for score, section in ranked:
        location = (section.document_logical_name, section.heading_path)
        if location in seen:
            continue
        seen.add(location)
        candidates.append(
            Candidate(
                document_logical_name=section.document_logical_name,
                heading_path=section.heading_path,
                evidence_excerpt=section.text[:400],
                suggested_answer_points=suggest_answer_points(section),
                content_fingerprint=section.fingerprint,
                score=score,
            )
        )
        if len(candidates) >= limit:
            break
    return tuple(candidates)


def build_packages(
    cases: Iterable[RetrievalEvalCase],
    sections: Sequence[SectionRecord],
    *,
    limit: int = CANDIDATES_PER_CASE,
) -> tuple[CaseCandidatePackage, ...]:
    """Build candidate packages for every answerable, still-unlabelled case."""
    packages: list[CaseCandidatePackage] = []
    for case in cases:
        if case.relevant_sources:
            continue
        if case.answerability.value == "none":
            continue
        candidates = build_candidates(case, sections, limit=limit)
        notes: list[str] = []
        if not candidates:
            notes.append(
                "no section scored above threshold — the knowledge base may not "
                "cover this question; reviewer must decide between re-labelling "
                "as partial/none and authoring a label manually"
            )
        notes.append(
            "candidates are model suggestions; select and verify before setting label_origin=human"
        )
        packages.append(
            CaseCandidatePackage(
                case_id=case.case_id,
                question=case.question,
                answerability=case.answerability.value,
                diagnostic_keywords=case.diagnostic_keywords,
                candidates=candidates,
                notes=tuple(notes),
            )
        )
    return tuple(packages)


def load_sections_from_directory(directory: Path) -> list[SectionRecord]:
    """Parse documents into section records without touching the database."""
    import sys

    repo_root = Path(__file__).resolve().parent.parent
    for candidate in (repo_root / "src", repo_root):
        if str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))

    from agent_mentor.rag.documents import DocumentParser

    parser = DocumentParser(max_pdf_pages=200)
    records: list[SectionRecord] = []
    for path in sorted(directory.glob("*.md")):
        for section in parser.parse(path.name, path.read_bytes()):
            if not section.heading_path:
                continue
            records.append(
                SectionRecord(
                    document_logical_name=path.stem,
                    heading_path=tuple(section.heading_path),
                    block_type=section.block_type,
                    text=section.text,
                    fingerprint=content_fingerprint(section.text),
                )
            )
    return records
