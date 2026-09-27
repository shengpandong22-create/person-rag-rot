from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NormalizedClaim:
    source_text: str
    hypothesis: str | None
    strategy: str
    reason: str | None = None


OPEN_QUESTION_MARKERS = (
    "多少",
    "什么",
    "哪些",
    "哪一天",
    "何时",
    "什么时候",
    "为什么",
    "如何",
    "怎么",
)


def normalize_claim(text: str) -> NormalizedClaim:
    """Convert only closed questions to propositions without inventing an answer."""
    cleaned = text.strip().rstrip("？?").strip()
    if not cleaned:
        return NormalizedClaim(text, None, "unresolved", "empty_claim")
    if any(marker in cleaned for marker in OPEN_QUESTION_MARKERS):
        return NormalizedClaim(
            text,
            None,
            "requires_candidate_answer",
            "open_question_has_no_proposition_without_an_answer",
        )

    normalized = cleaned
    replacements = (
        (r"是否已经", "已经"),
        (r"是否仍然", "仍然"),
        (r"是否", ""),
        (r"能否", "能够"),
        (r"有没有", "有"),
        (r"是不是", "是"),
        (r"会不会", "会"),
    )
    changed = False
    for pattern, replacement in replacements:
        updated = re.sub(pattern, replacement, normalized, count=1)
        if updated != normalized:
            normalized = updated
            changed = True
            break
    normalized = re.sub(r"\s+", " ", normalized).strip(" ，,")
    if changed and normalized:
        return NormalizedClaim(text, f"{normalized}。", "closed_question_to_proposition")
    return NormalizedClaim(
        text,
        None,
        "requires_candidate_answer",
        "claim_is_not_a_closed_question",
    )
