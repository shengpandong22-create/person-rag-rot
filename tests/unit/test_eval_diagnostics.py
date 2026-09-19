from __future__ import annotations

from evals.diagnostics import (
    chunks_carry_content,
    render_diagnostics,
    run_diagnostics,
)


def _case(
    case_id: str,
    keywords: list[str],
    chunks: list[dict[str, object]],
    *,
    answerable: bool = True,
) -> dict[str, object]:
    return {
        "id": case_id,
        "question": f"{case_id} question",
        "answerable": answerable,
        "expected_keywords": keywords,
        "top_chunks": chunks,
    }


def test_chunks_carry_content_detects_legacy_reports() -> None:
    legacy = [_case("c1", ["a"], [{"rank": 1, "document_title": "t", "matched_keywords": ["a"]}])]
    modern = [_case("c1", ["a"], [{"rank": 1, "document_title": "t", "content": "a"}])]

    assert chunks_carry_content(legacy) is False
    assert chunks_carry_content(modern) is True


def test_legacy_report_reconstructs_variant_a_from_recorded_matches() -> None:
    cases = [
        _case(
            "ret-1",
            ["RAG"],
            [
                {"rank": 1, "document_title": "t", "matched_keywords": ["RAG"]},
                {"rank": 2, "document_title": "t", "matched_keywords": []},
            ],
        ),
        _case(
            "ret-2",
            ["MRR"],
            [
                {"rank": 1, "document_title": "t", "matched_keywords": []},
                {"rank": 2, "document_title": "t", "matched_keywords": ["MRR"]},
            ],
        ),
        _case(
            "ret-3",
            ["never"],
            [{"rank": 1, "document_title": "t", "matched_keywords": []}],
        ),
    ]

    results = run_diagnostics(cases)
    by_key = {result.variant: result for result in results}

    assert by_key["A"].available is True
    assert by_key["A"].hit_at_1 == 0.3333
    assert by_key["A"].hit_at_3 == 0.6667
    assert by_key["A"].misses == ("ret-3",)
    assert by_key["B"].available is False
    assert by_key["C"].available is False
    assert by_key["D"].available is False


def test_modern_report_computes_all_four_variants() -> None:
    cases = [
        _case(
            "c1",
            ["alpha", "beta"],
            [
                {
                    "rank": 1,
                    "document_title": "title-only-match alpha",
                    "heading_path": [],
                    "content": "unrelated body",
                },
                {
                    "rank": 2,
                    "document_title": "t",
                    "heading_path": ["h"],
                    "content": "alpha and beta both here",
                },
            ],
        )
    ]

    results = run_diagnostics(cases)
    by_key = {result.variant: result for result in results}

    assert all(result.available for result in results)
    # A matches at rank 1 because the title contains "alpha".
    assert by_key["A"].hit_at_1 == 1.0
    # B ignores titles, so it needs rank 2.
    assert by_key["B"].hit_at_1 == 0.0
    assert by_key["B"].hit_at_3 == 1.0
    # C requires two keywords, satisfied at rank 2.
    assert by_key["C"].hit_at_3 == 1.0
    # D requires all keywords, also rank 2 here.
    assert by_key["D"].hit_at_3 == 1.0


def test_negatives_and_keywordless_rows_are_excluded() -> None:
    cases = [
        _case("neg", [], [{"rank": 1, "content": "x"}], answerable=False),
        _case("nokw", [], [{"rank": 1, "content": "x"}]),
        _case("ok", ["x"], [{"rank": 1, "content": "x"}]),
    ]

    results = run_diagnostics(cases)
    by_key = {result.variant: result for result in results}

    assert by_key["A"].cases_evaluated == 1


def test_render_marks_unavailable_variants_instead_of_reporting_zero() -> None:
    cases = [_case("c1", ["a"], [{"rank": 1, "document_title": "t", "matched_keywords": ["a"]}])]

    markdown = render_diagnostics(
        run_diagnostics(cases), source="legacy.json", content_available=False
    )

    assert "not computable from this report" in markdown
    assert "Why only variant A is reported" in markdown
    assert "is the original v1 verdict recorded at run time" in markdown


def test_render_interprets_title_and_multi_keyword_gaps() -> None:
    cases = [
        _case(
            "c1",
            ["alpha", "beta"],
            [
                {
                    "rank": 1,
                    "document_title": "title mentions alpha",
                    "heading_path": [],
                    "content": "nothing else",
                },
                {
                    "rank": 2,
                    "document_title": "t",
                    "heading_path": [],
                    "content": "alpha beta",
                },
            ],
        )
    ]

    markdown = render_diagnostics(
        run_diagnostics(cases), source="modern.json", content_available=True
    )

    assert "Reading the result" in markdown
    assert "Dropping the title field lowers hit@1" in markdown
