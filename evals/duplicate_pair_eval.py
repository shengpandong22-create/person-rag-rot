from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from evals.claim_extractor import extract_claim_signature, subjects_compatible
from evals.freeze import file_sha256
from evals.nli_gate import DEFAULT_NLI_MODEL, NLIModel
from evals.provenance import collect_git_state


class DuplicatePairFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    category: str = Field(min_length=1, max_length=64)
    left: str = Field(min_length=1, max_length=500)
    right: str = Field(min_length=1, max_length=500)
    expected_duplicate: bool
    note: str = Field(min_length=1)


def load_duplicate_pair_fixtures(path: Path) -> tuple[DuplicatePairFixture, ...]:
    fixtures: list[DuplicatePairFixture] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        fixture = DuplicatePairFixture.model_validate_json(line)
        if fixture.id in seen:
            raise ValueError(f"duplicate fixture id at line {line_number}: {fixture.id}")
        seen.add(fixture.id)
        fixtures.append(fixture)
    if not fixtures:
        raise ValueError("duplicate-pair fixture dataset must not be empty")
    return tuple(fixtures)


def binary_metrics(expected: list[bool], predicted: list[bool]) -> dict[str, int | float]:
    true_positive = sum(left and right for left, right in zip(expected, predicted, strict=True))
    false_positive = sum(
        not left and right for left, right in zip(expected, predicted, strict=True)
    )
    false_negative = sum(
        left and not right for left, right in zip(expected, predicted, strict=True)
    )
    true_negative = sum(
        not left and not right for left, right in zip(expected, predicted, strict=True)
    )
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0
    )
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision + recall
        else 0.0,
        "accuracy": round((true_positive + true_negative) / len(expected), 4),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
    }


def run_duplicate_pair_eval(
    *, dataset: Path, manifest: Path, output_dir: Path, model_name: str, batch_size: int
) -> dict[str, Any]:
    freeze = json.loads(manifest.read_text(encoding="utf-8"))
    if freeze["sha256"] != file_sha256(dataset):
        raise ValueError("duplicate-pair dataset does not match freeze manifest")
    fixtures = load_duplicate_pair_fixtures(dataset)
    pairs = [
        pair
        for fixture in fixtures
        for pair in (
            (fixture.id, fixture.left, fixture.right),
            (fixture.id, fixture.right, fixture.left),
        )
    ]
    started = perf_counter()
    model = NLIModel(model_name)
    scores = model.score(pairs, batch_size)
    rows: list[dict[str, Any]] = []
    for index, fixture in enumerate(fixtures):
        forward = scores[index * 2]
        reverse = scores[index * 2 + 1]
        nli_duplicate = (
            forward.predicted_label == "entailment" and reverse.predicted_label == "entailment"
        )
        left_signature = extract_claim_signature(fixture.left)
        right_signature = extract_claim_signature(fixture.right)
        compatible = subjects_compatible(left_signature, right_signature)
        rows.append(
            {
                **fixture.model_dump(),
                "left_signature": asdict(left_signature),
                "right_signature": asdict(right_signature),
                "subject_compatible": compatible,
                "nli_duplicate": nli_duplicate,
                "combined_duplicate": nli_duplicate and compatible is True,
                "forward_nli": asdict(forward),
                "reverse_nli": asdict(reverse),
            }
        )
    expected = [fixture.expected_duplicate for fixture in fixtures]
    policies = {
        "nli_only": [bool(row["nli_duplicate"]) for row in rows],
        "nli_with_subject_guard": [bool(row["combined_duplicate"]) for row in rows],
    }
    by_category: dict[str, dict[str, object]] = defaultdict(dict)
    for category in sorted({fixture.category for fixture in fixtures}):
        indexes = [index for index, fixture in enumerate(fixtures) if fixture.category == category]
        category_expected = [expected[index] for index in indexes]
        for policy, predictions in policies.items():
            by_category[category][policy] = binary_metrics(
                category_expected, [predictions[index] for index in indexes]
            )
    unresolved = sum(row["subject_compatible"] is None for row in rows)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        **collect_git_state().to_json(),
        "dataset": str(dataset),
        "dataset_sha256": file_sha256(dataset),
        "freeze_manifest": str(manifest),
        "freeze_manifest_sha256": file_sha256(manifest),
        "model": model_name,
        "batch_size": batch_size,
        "duration_ms": round((perf_counter() - started) * 1000, 4),
        "distribution": dict(sorted(Counter(expected).items())),
        "metrics": {
            policy: binary_metrics(expected, predictions)
            for policy, predictions in policies.items()
        },
        "subject_unresolved_rate": round(unresolved / len(rows), 4),
        "metrics_by_category": by_category,
        "cases": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "duplicate_pair_eval.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate semantic duplicate-pair policies.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--freeze-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_NLI_MODEL)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    payload = run_duplicate_pair_eval(
        dataset=args.dataset,
        manifest=args.freeze_manifest,
        output_dir=args.output_dir,
        model_name=args.model,
        batch_size=args.batch_size,
    )
    print(payload["metrics"])
    print({"subject_unresolved_rate": payload["subject_unresolved_rate"]})


if __name__ == "__main__":
    main()
