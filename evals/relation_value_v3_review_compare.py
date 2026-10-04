"""Compare author annotations with an independently completed blind review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evals.relation_value_v3_acceptance_audit import load_jsonl


def _normalized_value_sets(value_sets: list[list[str]]) -> list[list[str]]:
    return sorted([sorted(str(value) for value in value_set) for value_set in value_sets])


def compare(
    author_rows: list[dict[str, Any]], reviewer_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    author_by_id = {row["id"]: row for row in author_rows}
    reviewer_by_id = {row["id"]: row for row in reviewer_rows}
    differences: dict[str, list[dict[str, Any]]] = {}
    for row_id, author in author_by_id.items():
        reviewer = reviewer_by_id.get(row_id, {}).get("reviewer_annotation", {})
        row_differences: list[dict[str, Any]] = []
        for field in (
            "answerability",
            "confusion_type",
            "primary_relation_role",
            "primary_span_type",
        ):
            if author.get(field) != reviewer.get(field):
                row_differences.append(
                    {"field": field, "author": author.get(field), "reviewer": reviewer.get(field)}
                )
        author_demands = author.get("demands", [])
        reviewer_demands = reviewer.get("demands", [])
        if len(author_demands) != len(reviewer_demands):
            row_differences.append(
                {
                    "field": "demand_count",
                    "author": len(author_demands),
                    "reviewer": len(reviewer_demands),
                }
            )
        for index, (author_demand, reviewer_demand) in enumerate(
            zip(author_demands, reviewer_demands, strict=False), start=1
        ):
            for field in (
                "relation_role",
                "value_semantic",
                "canonical_unit",
                "expected_binding",
                "modality",
            ):
                if author_demand.get(field) != reviewer_demand.get(field):
                    row_differences.append(
                        {
                            "field": f"demands[{index}].{field}",
                            "author": author_demand.get(field),
                            "reviewer": reviewer_demand.get(field),
                        }
                    )
            author_values = _normalized_value_sets(author_demand.get("accepted_value_sets", []))
            reviewer_values = _normalized_value_sets(reviewer_demand.get("accepted_value_sets", []))
            if author_values != reviewer_values:
                row_differences.append(
                    {
                        "field": f"demands[{index}].accepted_value_sets",
                        "author": author_values,
                        "reviewer": reviewer_values,
                    }
                )
        if row_differences:
            differences[row_id] = row_differences
    missing_author = sorted(set(reviewer_by_id) - set(author_by_id))
    missing_reviewer = sorted(set(author_by_id) - set(reviewer_by_id))
    return {
        "rows_compared": len(author_by_id),
        "agreement_rows": len(author_by_id) - len(differences) - len(missing_reviewer),
        "disagreement_rows": len(differences),
        "missing_author_rows": missing_author,
        "missing_reviewer_rows": missing_reviewer,
        "differences": differences,
        "candidate_executed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--author", required=True, type=Path)
    parser.add_argument("--reviewer", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = compare(load_jsonl(args.author), load_jsonl(args.reviewer))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
