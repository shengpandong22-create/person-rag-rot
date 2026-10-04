"""Evaluate V3 on paired, non-blind semantic-role Development cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evals.relation_value_binding_v3 import (
    EvidenceProvenance,
    bind_typed_relation_value,
    normalize_demand,
)


def evaluate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for row in rows:
        evidence = row["evidence"]
        bindings = bind_typed_relation_value(
            normalize_demand(row["relation"], row.get("canonical_unit"), row["span_type"]),
            provenance=EvidenceProvenance(
                evidence["chunk_id"],
                evidence["document_logical_name"],
                tuple(evidence["heading_path"]),
            ),
            content=evidence["text"],
        )
        expected_values = set(row["expected_values"])
        value_match = any(expected_values.issubset(binding.values) for binding in bindings)
        correct = value_match if row["expected_binding"] else not bindings
        results.append(
            {
                "id": row["id"],
                "pair_id": row["pair_id"],
                "confusion_type": row["confusion_type"],
                "expected_binding": row["expected_binding"],
                "predicted_binding": bool(bindings),
                "value_match": value_match,
                "correct": correct,
                "binding_count": len(bindings),
            }
        )
    positives = [item for item in results if item["expected_binding"]]
    negatives = [item for item in results if not item["expected_binding"]]
    return {
        "metrics": {
            "accuracy": round(sum(item["correct"] for item in results) / len(results), 4),
            "positive_value_recall": round(
                sum(item["value_match"] for item in positives) / len(positives), 4
            ),
            "negative_rejection": round(
                sum(not item["predicted_binding"] for item in negatives) / len(negatives), 4
            ),
            "average_binding_count": round(
                sum(item["binding_count"] for item in results) / len(results), 4
            ),
            "max_binding_count": max(item["binding_count"] for item in results),
        },
        "cases": results,
    }


def _load(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate_rows(_load(args.dataset))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
