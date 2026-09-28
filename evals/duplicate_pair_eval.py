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
from evals.duplicate_features import FEATURE_NAMES, transform_pair
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
    feature_policies = {
        "nli_baseline": (),
        **{f"{name}_only": (name,) for name in FEATURE_NAMES},
        "combined_typed_features": FEATURE_NAMES,
    }
    transformed: dict[str, list[Any]] = {
        policy: [transform_pair(fixture.left, fixture.right, features) for fixture in fixtures]
        for policy, features in feature_policies.items()
    }
    pairs = [
        pair
        for policy, feature_pairs in transformed.items()
        for fixture, feature_pair in zip(fixtures, feature_pairs, strict=True)
        for pair in (
            (f"{policy}:{fixture.id}", feature_pair.left, feature_pair.right),
            (f"{policy}:{fixture.id}", feature_pair.right, feature_pair.left),
        )
    ]
    started = perf_counter()
    model = NLIModel(model_name)
    scores = model.score(pairs, batch_size)
    rows: list[dict[str, Any]] = []
    predictions: dict[str, list[bool]] = {policy: [] for policy in feature_policies}
    score_offset = 0
    policy_scores: dict[str, list[tuple[Any, Any]]] = defaultdict(list)
    for policy in feature_policies:
        for _fixture in fixtures:
            forward = scores[score_offset]
            reverse = scores[score_offset + 1]
            score_offset += 2
            policy_scores[policy].append((forward, reverse))
            predictions[policy].append(
                forward.predicted_label == "entailment"
                and reverse.predicted_label == "entailment"
            )
    for index, fixture in enumerate(fixtures):
        left_signature = extract_claim_signature(fixture.left)
        right_signature = extract_claim_signature(fixture.right)
        compatible = subjects_compatible(left_signature, right_signature)
        baseline_forward, baseline_reverse = policy_scores["nli_baseline"][index]
        rows.append(
            {
                **fixture.model_dump(),
                "left_signature": asdict(left_signature),
                "right_signature": asdict(right_signature),
                "subject_compatible": compatible,
                "feature_inputs": {
                    policy: {
                        "left": transformed[policy][index].left,
                        "right": transformed[policy][index].right,
                        "applied": transformed[policy][index].applied,
                    }
                    for policy in feature_policies
                },
                "predictions": {
                    policy: predictions[policy][index] for policy in feature_policies
                },
                "baseline_forward_nli": asdict(baseline_forward),
                "baseline_reverse_nli": asdict(baseline_reverse),
            }
        )
    expected = [fixture.expected_duplicate for fixture in fixtures]
    by_category: dict[str, dict[str, object]] = defaultdict(dict)
    for category in sorted({fixture.category for fixture in fixtures}):
        indexes = [index for index, fixture in enumerate(fixtures) if fixture.category == category]
        category_expected = [expected[index] for index in indexes]
        for policy, policy_predictions in predictions.items():
            by_category[category][policy] = binary_metrics(
                category_expected, [policy_predictions[index] for index in indexes]
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
            policy: binary_metrics(expected, policy_predictions)
            for policy, policy_predictions in predictions.items()
        },
        "feature_application_count": {
            policy: sum(pair.applied for pair in feature_pairs)
            for policy, feature_pairs in transformed.items()
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
