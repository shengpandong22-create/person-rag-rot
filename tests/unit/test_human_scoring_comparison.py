import json
from pathlib import Path

from scripts.prepare_human_scoring_comparison import prepare_rows


def test_blind_worksheet_excludes_author_labels(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "case-1",
                "topic": "Topic",
                "question": "Question?",
                "answer": "Answer",
                "human_scores": {"correctness": 5},
                "expected_review": False,
                "expected_band": "high",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    worksheet, key = prepare_rows(dataset)

    rendered = json.dumps(worksheet, ensure_ascii=False)
    assert "human_scores" not in rendered
    assert "expected_review" not in rendered
    assert "expected_band" not in rendered
    assert worksheet[0]["blind_id"] == "blind-01"
    assert key == [{"blind_id": "blind-01", "case_id": "case-1"}]
