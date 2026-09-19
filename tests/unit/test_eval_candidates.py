from __future__ import annotations

from evals.candidates import (
    MODEL_SUGGESTED,
    NEEDS_REVIEW,
    SectionRecord,
    build_candidates,
    build_packages,
    content_fingerprint,
    suggest_answer_points,
)
from evals.schema import Answerability, RetrievalEvalCase


def _section(
    name: str = "第 3 课：混合检索与可信 RAG 回答",
    heading: tuple[str, ...] = ("一、教案正文", "3.7 第二道防线：证据门禁"),
    text: str = "证据不足时应用层直接拒答，避免把模型常识伪装成资料结论。",
) -> SectionRecord:
    return SectionRecord(
        document_logical_name=name,
        heading_path=heading,
        block_type="paragraph",
        text=text,
        fingerprint=content_fingerprint(text),
    )


def _case(
    case_id: str = "ret-1",
    question: str = "证据门禁什么时候拒答？",
    keywords: tuple[str, ...] = ("证据门禁", "拒答"),
) -> RetrievalEvalCase:
    return RetrievalEvalCase(
        case_id=case_id,
        question=question,
        answerability=Answerability.FULL,
        diagnostic_keywords=keywords,
    )


def test_candidates_never_claim_human_verification() -> None:
    package = build_packages([_case()], [_section()])[0]
    payload = package.to_json()

    assert payload["human_verified"] is False
    assert payload["suggested_by"] == MODEL_SUGGESTED
    assert all(candidate["review_status"] == NEEDS_REVIEW for candidate in payload["candidates"])
    assert payload["notes"]


def test_candidates_use_stable_location_not_chunk_uuid() -> None:
    package = build_packages([_case()], [_section()])[0]
    candidate = package.candidates[0]

    assert candidate.document_logical_name == "第 3 课：混合检索与可信 RAG 回答"
    assert candidate.heading_path == ("一、教案正文", "3.7 第二道防线：证据门禁")
    assert len(candidate.content_fingerprint) == 64
    # No UUID-like field should exist anywhere in the emitted payload.
    serialised = str(package.to_json())
    assert "chunk_id" not in serialised


def test_fingerprint_ignores_markdown_reflow_but_not_wording() -> None:
    padded = "| 防线 | 防什么 |\n| --- | --- |\n| 证据门禁 | 拒答 |"
    reflowed = "|防线|防什么|\n|---|---|\n|证据门禁|拒答|"
    reworded = "| 防线 | 防什么 |\n| --- | --- |\n| 证据门禁 | 改为兜底 |"

    assert content_fingerprint(padded) == content_fingerprint(reflowed)
    assert content_fingerprint(padded) != content_fingerprint(reworded)


def test_fingerprint_ignores_emphasis_edits() -> None:
    plain = "证据门禁直接拒答"
    emphasised = "**证据门禁**直接`拒答`"

    assert content_fingerprint(plain) == content_fingerprint(emphasised)


def test_suggested_answer_points_skip_table_separators_and_fences() -> None:
    section = _section(
        text=(
            "```\n"
            "证据门禁伪代码\n"
            "```\n"
            "| 防线 | 防什么 |\n"
            "| --- | --- |\n"
            "| 证据门禁 | 拒答 |\n"
            "核心价值：应用层先判断资料是否足以支持回答。\n"
        )
    )

    points = suggest_answer_points(section)

    assert not any(set(point) <= {"-", ":", "|", " "} for point in points)
    assert not any(point.startswith("```") for point in points)
    assert any("核心价值" in point for point in points)


def test_table_rows_become_readable_points() -> None:
    section = _section(text="| 防线 | 防什么 |\n| --- | --- |\n| 证据门禁 | 拒答 |\n")

    points = suggest_answer_points(section)

    assert any("证据门禁" in point for point in points)
    assert not any("---" in point for point in points)


def test_no_candidate_above_threshold_is_reported_as_empty_not_fabricated() -> None:
    unrelated = _section(text="完全无关的内容，讨论部署流程。", heading=("其他",))
    candidates = build_candidates(_case(question="量子纠缠的本质？", keywords=()), [unrelated])

    assert candidates == ()


def test_empty_candidate_package_carries_actionable_note() -> None:
    unrelated = _section(text="完全无关的内容。", heading=("其他",))
    package = build_packages([_case(question="量子纠缠的本质？", keywords=())], [unrelated])[0]

    assert package.candidates == ()
    assert any("may not cover this question" in note for note in package.notes)


def test_already_labelled_cases_are_skipped() -> None:
    from evals.schema import RelevantSource

    labelled = RetrievalEvalCase(
        "p1",
        "q",
        Answerability.FULL,
        (RelevantSource("doc.md", ("h",)),),
        (),
    )

    assert build_packages([labelled], [_section()]) == ()


def test_negative_cases_are_skipped() -> None:
    from evals.schema import NegativeReason

    negative = RetrievalEvalCase(
        "n1",
        "q",
        Answerability.NONE,
        (),
        (),
        negative_reason=NegativeReason.FALSE_PREMISE,
    )

    assert build_packages([negative], [_section()]) == ()
