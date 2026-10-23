from scripts.prepare_coarse_scoring_review import render_form


def test_coarse_review_form_has_no_author_score_or_expected_label() -> None:
    rendered = render_form(
        [
            {
                "blind_id": "blind-01",
                "question": "Question?",
                "answer": "Answer.",
            }
        ]
    )

    assert "差／一般／好" in rendered
    assert "human_scores" not in rendered
    assert "expected_band" not in rendered
    assert "blind-01" in rendered
