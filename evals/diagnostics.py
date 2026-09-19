"""Zero-cost retrieval label diagnostics — no LLM, no human labelling.

Motivation
----------
Before spending human effort re-labelling, it is worth measuring *how much of
the old metric came from matching public terms that appear almost everywhere*.
The v1 runner treated a chunk as relevant when any keyword string appeared
anywhere in ``document_title + heading_path + content``.  Because the demo
knowledge base is itself a course about RAG, terms such as ``RAG``/``证据``/
``引用`` cover 30%-35% of all chunks.

This module computes four variants over an already-produced report:

    A  any keyword, title + heading + content   (the v1 behaviour)
    B  any keyword, heading + content           (drops the title field)
    C  at least two keywords, heading + content (stricter than v1)
    D  all keywords, heading + content          (strictest)

A/B/C are **diagnostic only**.  A large A-vs-B gap shows the title field was
inflating the metric; a large gap between A and C shows single public terms
were doing the work.  Neither substitutes for human labels, which remain the
only valid ground truth.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DiagnosticVariant:
    key: str
    label: str
    uses_title: bool
    min_hits: int

    def matches(self, chunk: dict[str, Any], keywords: Sequence[str]) -> bool:
        haystack_parts = []
        if self.uses_title:
            haystack_parts.append(str(chunk.get("document_title", "")))
        heading = chunk.get("heading_path") or []
        if isinstance(heading, list):
            haystack_parts.append(" ".join(str(item) for item in heading))
        haystack_parts.append(str(chunk.get("content", "")))
        haystack = " ".join(haystack_parts).casefold()
        hits = sum(1 for keyword in keywords if keyword.casefold() in haystack)
        return hits >= self.min_hits


VARIANTS: tuple[DiagnosticVariant, ...] = (
    DiagnosticVariant("A", "any keyword, title+heading+content (v1)", True, 1),
    DiagnosticVariant("B", "any keyword, heading+content", False, 1),
    DiagnosticVariant("C", ">=2 keywords, heading+content", False, 2),
    DiagnosticVariant("D", "all keywords, heading+content", False, 0),
)


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    variant: str
    label: str
    cases_evaluated: int
    hit_at_1: float
    hit_at_3: float
    hit_at_6: float
    misses: tuple[str, ...]
    available: bool = True


def variant_matches_all(
    chunk: dict[str, Any], keywords: Sequence[str], *, uses_title: bool
) -> bool:
    """Variant D: every keyword must appear."""
    haystack_parts = []
    if uses_title:
        haystack_parts.append(str(chunk.get("document_title", "")))
    heading = chunk.get("heading_path") or []
    if isinstance(heading, list):
        haystack_parts.append(" ".join(str(item) for item in heading))
    haystack_parts.append(str(chunk.get("content", "")))
    haystack = " ".join(haystack_parts).casefold()
    return all(keyword.casefold() in haystack for keyword in keywords)


def _first_rank(
    chunks: Iterable[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]
) -> int | None:
    for rank, chunk in enumerate(chunks, start=1):
        if predicate(chunk):
            return rank
    return None


def chunks_carry_content(cases: Iterable[dict[str, Any]]) -> bool:
    """Whether stored rows retain chunk text.

    Older reports persisted only ``rank``/``chunk_id``/``document_title``/
    ``score``/``matched_keywords``.  Without ``content`` the string-matching
    variants cannot be recomputed, and silently scoring against the title
    alone would understate the original metric by an order of magnitude.
    """
    for case in cases:
        for chunk in case.get("top_chunks") or []:
            return "content" in chunk
    return False


def run_diagnostics(
    cases: Iterable[dict[str, Any]],
    *,
    include_title_for_d: bool = False,
) -> tuple[DiagnosticResult, ...]:
    """Compute the A/B/C/D variants over report rows.

    When the report predates ``content`` persistence, this falls back to the
    recorded ``matched_keywords`` lists, which **are** the original variant-A
    verdicts captured at run time.  In that mode only variant A is meaningful
    and the other variants are reported as unavailable rather than as zeros,
    because zeros would read as "the retriever failed" instead of "the report
    cannot answer this question".
    """
    case_list = list(cases)
    answerable = [
        case for case in case_list if bool(case.get("answerable")) and case.get("expected_keywords")
    ]
    if not chunks_carry_content(case_list):
        return (_from_recorded_matches(answerable), *_unavailable())

    results: list[DiagnosticResult] = []
    for variant in VARIANTS:
        if variant.key == "D":
            predicate_factory = lambda keywords, v=variant: (  # noqa: E731
                lambda chunk: variant_matches_all(chunk, keywords, uses_title=include_title_for_d)
            )
        else:
            predicate_factory = lambda keywords, v=variant: (  # noqa: E731
                lambda chunk: v.matches(chunk, keywords)
            )
        ranks: list[int | None] = []
        misses: list[str] = []
        for case in answerable:
            keywords = [str(item) for item in case["expected_keywords"]]
            chunks = case.get("top_chunks") or []
            rank = _first_rank(chunks, predicate_factory(keywords))
            ranks.append(rank)
            if rank is None:
                misses.append(str(case.get("id")))
        results.append(
            DiagnosticResult(
                variant=variant.key,
                label=variant.label,
                cases_evaluated=len(answerable),
                hit_at_1=_rate(ranks, 1),
                hit_at_3=_rate(ranks, 3),
                hit_at_6=_rate(ranks, 6),
                misses=tuple(misses),
                available=True,
            )
        )
    return tuple(results)


def _from_recorded_matches(answerable: list[dict[str, Any]]) -> DiagnosticResult:
    """Reconstruct variant A from the ``matched_keywords`` recorded at run time."""
    ranks: list[int | None] = []
    misses: list[str] = []
    for case in answerable:
        rank = None
        for chunk in case.get("top_chunks") or []:
            if chunk.get("matched_keywords"):
                rank = int(chunk.get("rank", 0)) or None
                break
        ranks.append(rank)
        if rank is None:
            misses.append(str(case.get("id")))
    return DiagnosticResult(
        variant="A",
        label="any keyword, title+heading+content (v1, from recorded matched_keywords)",
        cases_evaluated=len(answerable),
        hit_at_1=_rate(ranks, 1),
        hit_at_3=_rate(ranks, 3),
        hit_at_6=_rate(ranks, 6),
        misses=tuple(misses),
        available=True,
    )


def _unavailable() -> tuple[DiagnosticResult, ...]:
    return tuple(
        DiagnosticResult(
            variant=variant.key,
            label=variant.label,
            cases_evaluated=0,
            hit_at_1=0.0,
            hit_at_3=0.0,
            hit_at_6=0.0,
            misses=(),
            available=False,
        )
        for variant in VARIANTS
        if variant.key != "A"
    )


def _rate(ranks: Sequence[int | None], k: int) -> float:
    if not ranks:
        return 0.0
    hits = sum(rank is not None and rank <= k for rank in ranks)
    return round(hits / len(ranks), 4)


def render_diagnostics(
    results: tuple[DiagnosticResult, ...], *, source: str, content_available: bool = True
) -> str:
    lines = [
        "# Retrieval Label Diagnostics",
        "",
        f"- source_report: `{source}`",
        "- scope: answerable rows carrying diagnostic keywords",
        f"- chunk_content_available: {content_available}",
        "- NOTE: A/B/C are diagnostic only and are NOT valid Recall/MRR.",
        "  They show how much of the old metric came from public-term matching",
        "  or from the document title field. Human labels remain the only",
        "  acceptable ground truth.",
        "",
        "| variant | rule | cases | hit@1 | hit@3 | hit@6 | misses |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        if not result.available:
            lines.append(
                f"| {result.variant} | {result.label} | n/a | n/a | n/a | n/a | "
                "not computable from this report |"
            )
            continue
        misses = ", ".join(result.misses) if result.misses else "-"
        lines.append(
            f"| {result.variant} | {result.label} | {result.cases_evaluated} | "
            f"{result.hit_at_1} | {result.hit_at_3} | {result.hit_at_6} | {misses} |"
        )
    lines.append("")
    if not content_available:
        lines.extend(
            [
                "## Why only variant A is reported",
                "",
                "This report was produced before ``content`` was persisted into",
                "``top_chunks``.  Only ``document_title`` and the run-time",
                "``matched_keywords`` survive, so variants B/C/D cannot be",
                "recomputed.  They are marked *not computable* rather than zero,",
                "because a zero would be read as a retrieval failure instead of a",
                "missing field.",
                "",
                "Variant A above is reconstructed from ``matched_keywords``, which",
                "is the original v1 verdict recorded at run time — so it is exact,",
                "not an approximation.",
                "",
                "To obtain B/C/D, re-run the retrieval evaluation with a dataset",
                "whose positive rows carry human ``relevant_sources`` labels.",
                "",
            ]
        )
        return "\n".join(lines)
    lines.extend(_interpretation(results))
    return "\n".join(lines)


def _interpretation(results: tuple[DiagnosticResult, ...]) -> list[str]:
    by_key = {result.variant: result for result in results}
    a, b, c = by_key.get("A"), by_key.get("B"), by_key.get("C")
    if a is None or b is None or c is None:
        return []
    lines = ["## Reading the result", ""]
    if a.hit_at_1 - b.hit_at_1 > 0.01:
        delta = round(a.hit_at_1 - b.hit_at_1, 4)
        lines.append(
            f"- Dropping the title field lowers hit@1 by {delta}. "
            "The title was contributing matches, so labels must not be "
            "validated against titles alone."
        )
    else:
        lines.append(
            "- Removing the title field does not change hit@1 materially. "
            "Inflation, if any, comes from chunk content rather than titles."
        )
    if a.hit_at_1 - c.hit_at_1 > 0.01:
        delta = round(a.hit_at_1 - c.hit_at_1, 4)
        lines.append(
            f"- Requiring two keywords instead of one lowers hit@1 by {delta}. "
            "A meaningful share of matches came from a single term, which is "
            "consistent with public-term false positives."
        )
    else:
        lines.append(
            "- Requiring two keywords does not change hit@1 materially. "
            "Single-term matches are not the dominant effect on this dataset."
        )
    lines.append("")
    lines.append(
        "These numbers bound the problem; they do not decide it. Human labels "
        "must be authored before any Recall/MRR is reported."
    )
    return lines
