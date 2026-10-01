"""Validate and freeze the independent demand-binding Development fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.schema import Answerability, LabelOrigin, load_dataset

FEATURES = {"exact_value", "unit_alias", "range_value", "table_value", "cross_sentence"}


def load_and_validate(path: Path, *, overlap_paths: tuple[Path, ...] = ()) -> dict[str, Any]:
    parsed = load_dataset(path, require_graded=True)
    rows = _load_jsonl(path)
    if len(rows) != len(parsed.cases):
        raise ValueError("demand-binding fixture raw/schema row counts disagree")
    counts: Counter[str] = Counter()
    polarity: Counter[str] = Counter()
    questions: set[str] = set()
    for case, row in zip(parsed.cases, rows, strict=True):
        feature = str(row.get("binding_feature") or "")
        expected = row.get("expected_binding")
        if feature not in FEATURES:
            raise ValueError(f"{case.case_id}: unknown binding_feature {feature!r}")
        if not isinstance(expected, bool):
            raise ValueError(f"{case.case_id}: expected_binding must be boolean")
        if expected is not (case.answerability is not Answerability.NONE):
            raise ValueError(f"{case.case_id}: expected_binding contradicts answerability")
        if case.label_origin is not LabelOrigin.HUMAN:
            raise ValueError(f"{case.case_id}: label must be human")
        if "demand_binding_fixture" not in case.tags or feature not in case.tags:
            raise ValueError(f"{case.case_id}: fixture and feature tags are required")
        normalized = case.question.strip().casefold()
        if normalized in questions:
            raise ValueError(f"duplicate question: {case.question}")
        questions.add(normalized)
        counts[feature] += 1
        polarity["positive" if expected else "negative"] += 1
    if set(counts) != FEATURES or len(set(counts.values())) != 1:
        raise ValueError(f"features must be balanced, got {dict(counts)}")
    overlaps = []
    for other in overlap_paths:
        if other.resolve() == path.resolve():
            continue
        for row in _load_jsonl(other):
            if str(row.get("question") or "").strip().casefold() in questions:
                overlaps.append(f"{other}:{row.get('id')}")
    if overlaps:
        raise ValueError(f"question overlap: {sorted(overlaps)}")
    return {
        "case_count": len(rows),
        "case_ids": [case.case_id for case in parsed.cases],
        "feature_counts": dict(sorted(counts.items())),
        "polarity_counts": dict(sorted(polarity.items())),
    }


def write_freeze(dataset: Path, manifest: Path, summary: dict[str, Any]) -> None:
    payload = {
        "dataset": str(dataset),
        "sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        **summary,
        "frozen_at": datetime.now(UTC).isoformat(),
        "note": "Frozen independent Development fixture for eval-only demand-binding design.",
    }
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_freeze(dataset: Path, manifest: Path) -> tuple[bool, str]:
    record = json.loads(manifest.read_text(encoding="utf-8"))
    actual = hashlib.sha256(dataset.read_bytes()).hexdigest()
    ok = actual == record.get("sha256")
    return ok, f"{'intact' if ok else 'drift'}: sha256={actual}"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/datasets/retrieval_demand_binding_development_v1.jsonl"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("evals/datasets/DEMAND_BINDING_DEVELOPMENT_FREEZE.json"),
    )
    parser.add_argument("--write-freeze", action="store_true")
    args = parser.parse_args()
    others = tuple(Path("evals/datasets").glob("retrieval_*.jsonl"))
    summary = load_and_validate(args.dataset, overlap_paths=others)
    if args.write_freeze:
        write_freeze(args.dataset, args.manifest, summary)
    ok, message = check_freeze(args.dataset, args.manifest)
    print(json.dumps({**summary, "freeze": message}, ensure_ascii=False, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
