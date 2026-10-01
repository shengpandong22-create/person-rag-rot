from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.schema import LabelOrigin, load_dataset

SCENARIO_EXPECTATIONS = {
    "heading_similar_negative": False,
    "low_overlap_semantic_positive": True,
    "high_confidence_miss_risk": True,
    "heading_vector_divergence_no_trigger": False,
}


@dataclass(frozen=True, slots=True)
class TriggerFixtureSummary:
    case_count: int
    scenario_counts: dict[str, int]
    expected_trigger_counts: dict[str, int]
    case_ids: tuple[str, ...]


def load_and_validate_trigger_fixture(
    path: Path,
    *,
    overlap_paths: tuple[Path, ...] = (),
) -> TriggerFixtureSummary:
    parsed = load_dataset(path, require_graded=True)
    raw_rows = _load_jsonl(path)
    if len(raw_rows) != len(parsed.cases):
        raise ValueError("trigger fixture raw/schema row counts disagree")
    ids = [case.case_id for case in parsed.cases]
    if len(ids) != len(set(ids)):
        raise ValueError("trigger fixture case ids must be unique")
    questions = [case.question.strip().casefold() for case in parsed.cases]
    if len(questions) != len(set(questions)):
        raise ValueError("trigger fixture questions must be unique")

    scenario_counts: Counter[str] = Counter()
    trigger_counts: Counter[str] = Counter()
    for case, raw in zip(parsed.cases, raw_rows, strict=True):
        scenario = str(raw.get("trigger_scenario") or "")
        if scenario not in SCENARIO_EXPECTATIONS:
            raise ValueError(f"{case.case_id}: unknown trigger_scenario {scenario!r}")
        expected_trigger = raw.get("expected_trigger")
        if not isinstance(expected_trigger, bool):
            raise ValueError(f"{case.case_id}: expected_trigger must be boolean")
        if expected_trigger is not SCENARIO_EXPECTATIONS[scenario]:
            raise ValueError(
                f"{case.case_id}: expected_trigger={expected_trigger} contradicts {scenario}"
            )
        if not str(raw.get("trigger_rationale") or "").strip():
            raise ValueError(f"{case.case_id}: trigger_rationale is required")
        if case.label_origin is not LabelOrigin.HUMAN:
            raise ValueError(f"{case.case_id}: trigger labels must be human")
        if "trigger_fixture" not in case.tags or scenario not in case.tags:
            raise ValueError(f"{case.case_id}: tags must include trigger_fixture and scenario")
        scenario_counts[scenario] += 1
        trigger_counts[str(expected_trigger).lower()] += 1

    if set(scenario_counts) != set(SCENARIO_EXPECTATIONS):
        raise ValueError("trigger fixture must cover all required scenarios")
    if len(set(scenario_counts.values())) != 1:
        raise ValueError(f"trigger scenarios must be balanced, got {dict(scenario_counts)}")

    fixture_questions = set(questions)
    overlaps: list[str] = []
    for other_path in overlap_paths:
        if other_path.resolve() == path.resolve():
            continue
        for other_row in _load_jsonl(other_path):
            other_question = str(other_row.get("question") or "").strip().casefold()
            if other_question in fixture_questions:
                overlaps.append(f"{other_path}:{other_row.get('id', 'unknown')}")
    if overlaps:
        raise ValueError(f"trigger fixture question overlap: {sorted(overlaps)}")

    return TriggerFixtureSummary(
        case_count=len(parsed.cases),
        scenario_counts=dict(sorted(scenario_counts.items())),
        expected_trigger_counts=dict(sorted(trigger_counts.items())),
        case_ids=tuple(ids),
    )


def write_trigger_freeze(
    dataset_path: Path,
    freeze_path: Path,
    summary: TriggerFixtureSummary,
) -> None:
    payload = {
        "dataset": str(dataset_path),
        "sha256": _sha256(dataset_path),
        "case_count": summary.case_count,
        "case_ids": list(summary.case_ids),
        "scenario_counts": summary.scenario_counts,
        "expected_trigger_counts": summary.expected_trigger_counts,
        "frozen_at": datetime.now(UTC).isoformat(),
        "note": (
            "Frozen independent Development fixture for retrieval-trigger feature design. "
            "It may be used for trigger diagnostics but is not a final acceptance set; "
            "any content change invalidates prior trigger experiments."
        ),
    }
    freeze_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def check_trigger_freeze(dataset_path: Path, freeze_path: Path) -> tuple[bool, str]:
    if not freeze_path.exists():
        return False, f"missing freeze manifest: {freeze_path}"
    record = json.loads(freeze_path.read_text(encoding="utf-8"))
    actual = _sha256(dataset_path)
    expected = str(record.get("sha256") or "")
    if actual != expected:
        return False, f"trigger fixture drift: expected {expected}, got {actual}"
    return True, f"intact: {record['case_count']} cases, sha256={actual}"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("//"):
            rows.append(json.loads(stripped))
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and freeze trigger Development data.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/datasets/retrieval_trigger_development_v1.jsonl"),
    )
    parser.add_argument(
        "--freeze",
        type=Path,
        default=Path("evals/datasets/TRIGGER_DEVELOPMENT_FREEZE.json"),
    )
    parser.add_argument("--write-freeze", action="store_true")
    args = parser.parse_args()
    overlap_paths = tuple(
        path for path in Path("evals/datasets").glob("retrieval_*.jsonl") if path != args.dataset
    )
    summary = load_and_validate_trigger_fixture(args.dataset, overlap_paths=overlap_paths)
    if args.write_freeze:
        write_trigger_freeze(args.dataset, args.freeze, summary)
    ok, message = check_trigger_freeze(args.dataset, args.freeze)
    print(
        json.dumps(
            {
                "case_count": summary.case_count,
                "scenario_counts": summary.scenario_counts,
                "expected_trigger_counts": summary.expected_trigger_counts,
                "freeze": message,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
