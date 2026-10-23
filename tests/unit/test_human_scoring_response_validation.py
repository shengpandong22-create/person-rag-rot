from scripts.validate_human_scoring_responses import validate_rows


def test_completed_blind_response_is_accepted() -> None:
    row = {
        "blind_id": "blind-01",
        "reviewer_response": {
            "correctness": 4,
            "completeness": 3,
            "reasoning": 4,
            "communication": 5,
            "needs_review": False,
            "rationale": "覆盖了核心结论，但没有完整展开边界。",
        },
    }

    assert validate_rows([row], expected_count=1) == []


def test_incomplete_blind_response_is_rejected() -> None:
    row = {
        "blind_id": "blind-01",
        "reviewer_response": {
            "correctness": 6,
            "completeness": None,
            "reasoning": 1,
            "communication": 1,
            "needs_review": None,
            "rationale": "",
        },
    }

    errors = validate_rows([row], expected_count=1)

    assert len(errors) == 4
