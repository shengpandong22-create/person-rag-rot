"""Validate and freeze relation-value binding Development labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.schema import Answerability, LabelOrigin, load_dataset

SPAN_TYPES = {"sentence_span", "table_row", "code_statement", "bounded_multi_span"}


def load_and_validate(
    path: Path,
    *,
    overlap_paths: tuple[Path, ...] = (),
    reject_source_overlap: bool = False,
) -> dict[str, Any]:
    parsed = load_dataset(path, require_graded=True)
    rows = _load_jsonl(path)
    if len(rows) != len(parsed.cases):
        raise ValueError("relation-value raw/schema row counts disagree")
    span_counts: Counter[str] = Counter()
    polarity: Counter[str] = Counter()
    questions: set[str] = set()
    sources = _source_keys(rows)
    for case, row in zip(parsed.cases, rows, strict=True):
        span_type = str(row.get("evidence_span_type") or "")
        expected = row.get("expected_binding")
        values = row.get("expected_values")
        relation = str(row.get("requested_relation") or "").strip()
        if span_type not in SPAN_TYPES:
            raise ValueError(f"{case.case_id}: invalid evidence_span_type")
        if not isinstance(expected, bool) or expected is not (
            case.answerability is not Answerability.NONE
        ):
            raise ValueError(f"{case.case_id}: expected_binding contradicts answerability")
        if not relation:
            raise ValueError(f"{case.case_id}: requested_relation is required")
        if not isinstance(values, list) or expected != bool(values):
            raise ValueError(f"{case.case_id}: expected_values must match binding polarity")
        if case.label_origin is not LabelOrigin.HUMAN:
            raise ValueError(f"{case.case_id}: label must be human")
        if "relation_value_fixture" not in case.tags or span_type not in case.tags:
            raise ValueError(f"{case.case_id}: fixture/span tags are required")
        question = case.question.strip().casefold()
        if question in questions:
            raise ValueError(f"duplicate question: {case.question}")
        questions.add(question)
        span_counts[span_type] += 1
        polarity["positive" if expected else "negative"] += 1
    if set(span_counts) != SPAN_TYPES or len(set(span_counts.values())) != 1:
        raise ValueError(f"span types must be balanced, got {dict(span_counts)}")
    overlaps = []
    source_overlaps = []
    for other in overlap_paths:
        if other.resolve() == path.resolve():
            continue
        overlaps.extend(
            f"{other}:{row.get('id')}"
            for row in _load_jsonl(other)
            if str(row.get("question") or "").strip().casefold() in questions
        )
        if reject_source_overlap:
            source_overlaps.extend(
                f"{other}:{document} > {' > '.join(heading)}"
                for document, heading in sorted(sources & _source_keys(_load_jsonl(other)))
            )
    if overlaps:
        raise ValueError(f"question overlap: {sorted(overlaps)}")
    if source_overlaps:
        raise ValueError(f"ground-truth source overlap: {sorted(source_overlaps)}")
    return {
        "case_count": len(rows),
        "case_ids": [case.case_id for case in parsed.cases],
        "span_type_counts": dict(sorted(span_counts.items())),
        "polarity_counts": dict(sorted(polarity.items())),
    }


def write_freeze(dataset: Path, manifest: Path, summary: dict[str, Any]) -> None:
    payload = {
        "dataset": str(dataset),
        "sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        **summary,
        "frozen_at": datetime.now(UTC).isoformat(),
        "note": "Frozen independent Development fixture for relation-value binding design.",
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


def _source_keys(rows: list[dict[str, Any]]) -> set[tuple[str, tuple[str, ...]]]:
    return {
        (
            str(source.get("document_logical_name") or ""),
            tuple(str(part) for part in source.get("heading_path") or ()),
        )
        for row in rows
        for source in row.get("relevant_sources") or ()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/datasets/retrieval_relation_value_development_v1.jsonl"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("evals/datasets/RELATION_VALUE_DEVELOPMENT_FREEZE.json"),
    )
    parser.add_argument("--write-freeze", action="store_true")
    parser.add_argument("--reject-source-overlap", action="store_true")
    parser.add_argument("--overlap-dataset", action="append", type=Path)
    args = parser.parse_args()
    overlap_paths = tuple(args.overlap_dataset or Path("evals/datasets").glob("retrieval_*.jsonl"))
    summary = load_and_validate(
        args.dataset,
        overlap_paths=overlap_paths,
        reject_source_overlap=args.reject_source_overlap,
    )
    if args.write_freeze:
        write_freeze(args.dataset, args.manifest, summary)
    ok, message = check_freeze(args.dataset, args.manifest)
    print(json.dumps({**summary, "freeze": message}, ensure_ascii=False, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
