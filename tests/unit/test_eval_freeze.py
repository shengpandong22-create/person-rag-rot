from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.freeze import build_record, check_freeze, file_sha256, write_freeze
from evals.schema import (
    Answerability,
    LabelOrigin,
    RetrievalEvalCase,
    graded_cases,
    split_cases,
    ungraded_cases,
)

HOLDOUT_ROW = (
    '{"id":"ho-001","question":"保留样本问题？","answerability":"full",'
    '"split":"holdout","diagnostic_keywords":["a"]}'
)
VALIDATION_ROW = (
    '{"id":"va-001","question":"调参样本问题？","answerability":"full",'
    '"split":"validation","diagnostic_keywords":["a"]}'
)


def _write(path: Path, rows: list[str]) -> Path:
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_build_record_requires_holdout_rows(tmp_path: Path) -> None:
    dataset = _write(tmp_path / "no_holdout.jsonl", [VALIDATION_ROW])

    with pytest.raises(ValueError, match="no rows with split='holdout'"):
        build_record(dataset, note="test")


def test_build_record_rejects_mixed_splits(tmp_path: Path) -> None:
    dataset = _write(tmp_path / "mixed.jsonl", [HOLDOUT_ROW, VALIDATION_ROW])

    with pytest.raises(ValueError, match="must contain holdout rows only"):
        build_record(dataset, note="test")


def test_freeze_round_trip_detects_drift(tmp_path: Path) -> None:
    dataset = _write(tmp_path / "holdout.jsonl", [HOLDOUT_ROW])
    record_path = tmp_path / "FREEZE.json"

    record = write_freeze(dataset, record_path)
    assert record.case_count == 1
    assert record.case_ids == ("ho-001",)

    ok, message = check_freeze(dataset, record_path)
    assert ok is True
    assert "intact" in message

    dataset.write_text(HOLDOUT_ROW.replace("保留样本问题", "偷改后的问题") + "\n", encoding="utf-8")
    ok, message = check_freeze(dataset, record_path)
    assert ok is False
    assert "DATASET DRIFT" in message


def test_validation_split_can_be_frozen_with_its_own_record(tmp_path: Path) -> None:
    dataset = _write(tmp_path / "validation.jsonl", [VALIDATION_ROW])
    record_path = tmp_path / "VALIDATION_FREEZE.json"

    record = write_freeze(
        dataset, record_path, expected_split="validation", note="tuning split"
    )

    assert record.case_count == 1
    ok, message = check_freeze(dataset, record_path)
    assert ok is True
    assert "intact" in message


def test_freeze_rejects_a_record_for_the_wrong_split(tmp_path: Path) -> None:
    """Freezing validation rows as if they were holdout would fake an acceptance set."""
    dataset = _write(tmp_path / "validation.jsonl", [VALIDATION_ROW])

    with pytest.raises(ValueError, match="no rows with split='holdout'"):
        build_record(dataset, note="test", expected_split="holdout")


def test_check_freeze_without_record_fails_loudly(tmp_path: Path) -> None:
    dataset = _write(tmp_path / "holdout.jsonl", [HOLDOUT_ROW])

    ok, message = check_freeze(dataset, tmp_path / "missing.json")

    assert ok is False
    assert "no freeze record" in message


def test_file_sha256_is_stable_for_unchanged_content(tmp_path: Path) -> None:
    dataset = _write(tmp_path / "a.jsonl", [HOLDOUT_ROW])

    assert file_sha256(dataset) == file_sha256(dataset)
    assert len(file_sha256(dataset)) == 64


def test_split_cases_groups_all_three_splits() -> None:
    cases = (
        RetrievalEvalCase("r1", "q", Answerability.FULL, (), (), split="regression"),
        RetrievalEvalCase("v1", "q", Answerability.FULL, (), (), split="validation"),
        RetrievalEvalCase("h1", "q", Answerability.FULL, (), (), split="holdout"),
    )

    grouped = split_cases(cases)

    assert [case.case_id for case in grouped["regression"]] == ["r1"]
    assert [case.case_id for case in grouped["validation"]] == ["v1"]
    assert [case.case_id for case in grouped["holdout"]] == ["h1"]


def test_split_cases_rejects_unknown_split_instead_of_defaulting() -> None:
    cases = (RetrievalEvalCase("x", "q", Answerability.FULL, (), (), split="tunning"),)

    with pytest.raises(ValueError, match="unknown split"):
        split_cases(cases)


def test_graded_cases_excludes_unlabeled_rows_but_keeps_labelled_negatives() -> None:
    from evals.schema import RelevantSource

    graded_positive = RetrievalEvalCase(
        "p1",
        "q",
        Answerability.FULL,
        (RelevantSource("doc.md"),),
        (),
    )
    ungraded_positive = RetrievalEvalCase(
        "p2",
        "q",
        Answerability.FULL,
        (),
        (),
        label_origin=LabelOrigin.LEGACY_UNGRADED,
    )
    graded_negative = RetrievalEvalCase("n1", "q", Answerability.NONE, (), ())

    selected = graded_cases((graded_positive, ungraded_positive, graded_negative))

    assert {case.case_id for case in selected} == {"p1", "n1"}
    assert {case.case_id for case in ungraded_cases((graded_positive, ungraded_positive))} == {"p2"}


def test_freeze_record_json_is_readable_by_check(tmp_path: Path) -> None:
    dataset = _write(tmp_path / "holdout.jsonl", [HOLDOUT_ROW])
    record_path = tmp_path / "FREEZE.json"

    write_freeze(dataset, record_path)
    payload = json.loads(record_path.read_text(encoding="utf-8"))

    assert payload["sha256"] == file_sha256(dataset)
    assert payload["note"]
