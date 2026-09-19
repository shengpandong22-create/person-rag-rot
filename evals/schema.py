"""Retrieval evaluation data model — v2 schema.

Why this exists
---------------
The v1 dataset only stored ``question + expected_keywords + answerable``.
The runner treated a chunk as relevant as soon as **any one** keyword appeared
anywhere in ``document_title + heading_path + content``.  Because the demo
knowledge base is itself about RAG, keywords such as ``RAG``/``证据``/``引用``
cover 30%-35% of all chunks, so the v1 Recall number was inflated by public
terms and could not be reproduced after a rebuild.

The v2 schema separates three concerns that v1 conflated:

1. **Answerability** is now three-valued (``full``/``partial``/``none``) so the
   evidence gate can be scored as a 3-class decision instead of a boolean.
2. **Ground truth is location based**, not UUID based.  Chunk UUIDs change on
   re-chunk / re-embed / soft-deactivation, so labels anchor to
   ``document_logical_name + heading_path`` and the runner resolves them
   against the live knowledge base at run time.
3. **``expected_keywords`` is demoted to a diagnostic field.**  It is still
   recorded and reported, but it never decides formal Recall/MRR.

Backwards compatibility
-----------------------
The legacy v1 row is still accepted through :func:`load_legacy_case`, which
maps it onto a degenerate v2 case that resolves ground truth by keyword.  That
path exists only so the frozen v1 report stays reproducible; it is marked
``legacy`` in the report so nobody mistakes it for a graded label.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

ANSWERABILITY_VALUES = ("full", "partial", "none")
DIAGNOSTIC_ONLY_NOTE = "diagnostic_only"
NEEDS_GRADING_NOTE = "needs_grading"


class Answerability(StrEnum):
    """How much of the question the knowledge base can actually answer."""

    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class NegativeReason(StrEnum):
    """Why an unanswerable case is unanswerable.

    Kept explicit because "rejection accuracy" is meaningless without knowing
    whether the negative sample was an out-of-scope question (easy) or an
    in-domain question whose value is simply not recorded (hard).
    """

    OUT_OF_SCOPE = "out_of_scope"
    IN_DOMAIN_VALUE_MISSING = "in_domain_value_missing"
    IN_DOMAIN_NO_CONCLUSION = "in_domain_no_conclusion"
    VERSION_NOT_RELEASED = "version_not_released"
    OUT_OF_RANGE_IMPLEMENTATION = "out_of_range_implementation"
    FALSE_PREMISE = "false_premise"
    CONFLICTING_SOURCES = "conflicting_sources"
    PARTIAL_EVIDENCE_ONLY = "partial_evidence_only"


class LabelOrigin(StrEnum):
    """Provenance of a label, so synthetic rows can never pose as human labels."""

    HUMAN = "human"
    LEGACY_UNGRADED = "legacy_ungraded"


@dataclass(frozen=True, slots=True)
class RelevantSource:
    """A stable, rebuild-safe pointer to the evidence that answers a question.

    ``heading_path`` is matched as a suffix-normalised prefix so a document
    reorganisation that only adds an outer chapter does not silently break the
    label.  ``required_answer_points`` are the human-readable facts a correct
    answer must contain; they are what a grader checks, not a string matcher.
    """

    document_logical_name: str
    heading_path: tuple[str, ...] = ()
    required_answer_points: tuple[str, ...] = ()
    note: str | None = None

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"document_logical_name": self.document_logical_name}
        if self.heading_path:
            payload["heading_path"] = list(self.heading_path)
        if self.required_answer_points:
            payload["required_answer_points"] = list(self.required_answer_points)
        if self.note:
            payload["note"] = self.note
        return payload


@dataclass(frozen=True, slots=True)
class RetrievalEvalCase:
    """One graded retrieval evaluation row (v2 schema)."""

    case_id: str
    question: str
    answerability: Answerability
    relevant_sources: tuple[RelevantSource, ...] = ()
    diagnostic_keywords: tuple[str, ...] = ()
    negative_reason: NegativeReason | None = None
    negative_note: str | None = None
    label_origin: LabelOrigin = LabelOrigin.HUMAN
    split: str = "regression"
    tags: tuple[str, ...] = ()

    @property
    def answerable(self) -> bool:
        """Backwards-compatible boolean view: partial still counts as answerable."""
        return self.answerability is not Answerability.NONE

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.case_id,
            "question": self.question,
            "answerability": self.answerability.value,
            "split": self.split,
            "label_origin": self.label_origin.value,
        }
        if self.relevant_sources:
            payload["relevant_sources"] = [item.to_json() for item in self.relevant_sources]
        if self.diagnostic_keywords:
            payload["diagnostic_keywords"] = list(self.diagnostic_keywords)
        if self.negative_reason is not None:
            payload["negative_reason"] = self.negative_reason.value
        if self.negative_note:
            payload["negative_note"] = self.negative_note
        if self.tags:
            payload["tags"] = list(self.tags)
        return payload


@dataclass(frozen=True, slots=True)
class DatasetLoadResult:
    """Loaded cases plus the reasons any row had to be rejected."""

    cases: tuple[RetrievalEvalCase, ...]
    schema_version: str
    skipped: tuple[str, ...] = field(default_factory=tuple)


def parse_case(
    raw: dict[str, Any], *, line_number: int, require_graded: bool = True
) -> RetrievalEvalCase:
    """Parse one JSON object into a v2 case.

    ``require_graded`` controls whether answerable rows must already carry a
    ``relevant_sources`` label:

    * ``True`` (default) — the dataset claims to be graded.  A missing label is
      a hard error so an ungraded row can never be silently scored as Recall.
    * ``False`` — migration mode.  Answerable rows without labels are accepted
      but tagged ``needs_grading`` and downgraded to
      :class:`LabelOrigin.LEGACY_UNGRADED`, so grading code still refuses to
      treat them as ground truth.
    """
    context = f"dataset row {line_number}"
    try:
        case_id = str(raw["id"])
        question = str(raw["question"])
    except KeyError as error:
        raise ValueError(f"{context}: missing required field {error}") from error

    if "answerability" in raw:
        answerability_raw = str(raw["answerability"]).strip().lower()
        if answerability_raw not in ANSWERABILITY_VALUES:
            raise ValueError(
                f"{context}: answerability must be one of {ANSWERABILITY_VALUES}, "
                f"got {answerability_raw!r}"
            )
        answerability = Answerability(answerability_raw)
    elif "answerable" in raw:
        answerability = Answerability.FULL if bool(raw["answerable"]) else Answerability.NONE
    else:
        raise ValueError(f"{context}: missing answerability (or legacy answerable)")

    sources = tuple(
        RelevantSource(
            document_logical_name=str(item["document_logical_name"]),
            heading_path=tuple(str(part) for part in item.get("heading_path", ())),
            required_answer_points=tuple(
                str(point) for point in item.get("required_answer_points", ())
            ),
            note=str(item["note"]) if item.get("note") else None,
        )
        for item in raw.get("relevant_sources", ())
    )

    tags = tuple(str(item) for item in raw.get("tags", ()))
    origin = LabelOrigin(str(raw.get("label_origin", LabelOrigin.HUMAN.value)))

    if answerability is not Answerability.NONE and not sources:
        if require_graded:
            raise ValueError(
                f"{context}: answerability={answerability.value} requires at least one "
                "relevant_sources entry with a stable document_logical_name"
            )
        tags = (*tags, NEEDS_GRADING_NOTE)
        origin = LabelOrigin.LEGACY_UNGRADED
    if answerability is Answerability.NONE and sources:
        raise ValueError(f"{context}: answerability=none must not declare relevant_sources")

    negative_reason_raw = raw.get("negative_reason")
    negative_reason = None
    if negative_reason_raw is not None:
        try:
            negative_reason = NegativeReason(str(negative_reason_raw))
        except ValueError as error:
            valid = [item.value for item in NegativeReason]
            raise ValueError(
                f"{context}: unknown negative_reason {negative_reason_raw!r}; "
                f"expected one of {valid}"
            ) from error
    if answerability is Answerability.NONE and negative_reason is None:
        raise ValueError(
            f"{context}: answerability=none requires negative_reason so negatives can be "
            "stratified into easy/hard instead of reported as one aggregate number"
        )

    return RetrievalEvalCase(
        case_id=case_id,
        question=question,
        answerability=answerability,
        relevant_sources=sources,
        diagnostic_keywords=tuple(str(item) for item in raw.get("diagnostic_keywords", ())),
        negative_reason=negative_reason,
        negative_note=str(raw["negative_note"]) if raw.get("negative_note") else None,
        label_origin=origin,
        split=str(raw.get("split", "regression")),
        tags=tags,
    )


def load_dataset(path: Path, *, require_graded: bool = True) -> DatasetLoadResult:
    """Load a v2 JSONL dataset, failing on the first malformed row."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    cases: list[RetrievalEvalCase] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            cases.append(
                parse_case(
                    json.loads(stripped),
                    line_number=line_number,
                    require_graded=require_graded,
                )
            )
    if not cases:
        raise ValueError(f"Dataset is empty: {path}")
    duplicates = _duplicate_ids(cases)
    if duplicates:
        raise ValueError(f"Dataset contains duplicate ids: {sorted(duplicates)}")
    return DatasetLoadResult(cases=tuple(cases), schema_version="v2")


def _duplicate_ids(cases: list[RetrievalEvalCase]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            duplicates.add(case.case_id)
        seen.add(case.case_id)
    return duplicates


def load_legacy_case(raw: dict[str, Any], *, line_number: int) -> RetrievalEvalCase:
    """Map a v1 row onto the v2 shape without pretending it is a graded label.

    This deliberately does not call :func:`parse_case`: a v1 row has no
    ``relevant_sources``, and the v2 parser rejects answerable rows without
    them.  Ground truth for legacy rows is resolved by keyword at run time and
    the row is tagged ``legacy_ungraded``; reporting code must keep those rows
    out of formal Recall/MRR and out of graded negative stratification.
    """
    context = f"dataset row {line_number}"
    try:
        case_id = str(raw["id"])
        question = str(raw["question"])
    except KeyError as error:
        raise ValueError(f"{context}: missing required field {error}") from error

    answerability_raw = raw.get("answerability")
    if answerability_raw is not None:
        answerability = Answerability(str(answerability_raw).strip().lower())
    elif "answerable" in raw:
        answerability = Answerability.FULL if bool(raw["answerable"]) else Answerability.NONE
    else:
        raise ValueError(f"{context}: missing answerable (legacy) or answerability (v2)")

    negative_reason = None
    if raw.get("negative_reason") is not None:
        negative_reason = NegativeReason(str(raw["negative_reason"]))

    keywords = tuple(str(item) for item in raw.get("diagnostic_keywords", ()))
    if not keywords:
        keywords = tuple(str(item) for item in raw.get("expected_keywords", ()))

    tags = tuple(str(item) for item in raw.get("tags", ()))
    if answerability is not Answerability.NONE:
        tags = (*tags, DIAGNOSTIC_ONLY_NOTE)

    return RetrievalEvalCase(
        case_id=case_id,
        question=question,
        answerability=answerability,
        relevant_sources=(),
        diagnostic_keywords=keywords,
        negative_reason=negative_reason,
        negative_note=str(raw["negative_note"]) if raw.get("negative_note") else None,
        label_origin=LabelOrigin.LEGACY_UNGRADED,
        split=str(raw.get("split", "regression")),
        tags=tags,
    )
