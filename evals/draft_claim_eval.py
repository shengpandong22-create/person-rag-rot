from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from evals.draft_claims import load_draft_claim_fixtures
from evals.nli_gate import DEFAULT_NLI_MODEL, NLIModel

NLI_TO_STATUS = {
    "entailment": "supported",
    "neutral": "unknown",
    "contradiction": "contradicted",
}


def evaluate_fixture_predictions(
    expected: list[str], predicted: list[str]
) -> dict[str, object]:
    labels = ("supported", "contradicted", "unknown")
    confusion = {
        actual: {
            prediction: sum(
                left == actual and right == prediction
                for left, right in zip(expected, predicted, strict=True)
            )
            for prediction in labels
        }
        for actual in labels
    }
    per_class = {
        label: round(
            sum(
                left == label and right == label
                for left, right in zip(expected, predicted, strict=True)
            )
            / sum(left == label for left in expected),
            4,
        )
        for label in labels
    }
    return {
        "total": len(expected),
        "accuracy": round(
            sum(left == right for left, right in zip(expected, predicted, strict=True))
            / len(expected),
            4,
        ),
        "macro_accuracy": round(sum(per_class.values()) / len(per_class), 4),
        "per_class_accuracy": per_class,
        "confusion_matrix": confusion,
    }


def run_fixture_eval(
    *, dataset: Path, output_dir: Path, model_name: str, batch_size: int
) -> dict[str, object]:
    fixtures = load_draft_claim_fixtures(dataset)
    started = perf_counter()
    model = NLIModel(model_name)
    scores = model.score(
        [(fixture.case_id, fixture.evidence, fixture.claim.text) for fixture in fixtures],
        batch_size,
    )
    duration_ms = round((perf_counter() - started) * 1000, 4)
    expected = [fixture.expected_status.value for fixture in fixtures]
    predicted = [NLI_TO_STATUS[score.predicted_label] for score in scores]
    rows = [
        {
            "id": fixture.case_id,
            "evidence": fixture.evidence,
            "draft_claim": asdict(fixture.claim),
            "expected_status": fixture.expected_status.value,
            "predicted_status": prediction,
            "correct": fixture.expected_status.value == prediction,
            "note": fixture.note,
            "nli": asdict(score),
        }
        for fixture, score, prediction in zip(fixtures, scores, predicted, strict=True)
    ]
    payload: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset),
        "dataset_sha256": sha256(dataset.read_bytes()).hexdigest(),
        "label_distribution": dict(sorted(Counter(expected).items())),
        "model": {
            "name": model.model_name,
            "labels": list(NLI_TO_STATUS),
            "transformers_version": model.transformers_version,
            "device": model.device,
            "batch_size": batch_size,
        },
        "inference_duration_ms": duration_ms,
        "metrics": evaluate_fixture_predictions(expected, predicted),
        "cases": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "draft_claim_nli_eval.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate DraftClaim NLI fixtures.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_NLI_MODEL)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    payload = run_fixture_eval(
        dataset=args.dataset,
        output_dir=args.output_dir,
        model_name=args.model,
        batch_size=args.batch_size,
    )
    print(payload["metrics"])


if __name__ == "__main__":
    main()
