"""Apply source-grounded blind-review adjudications to the acceptance annotations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evals.relation_value_v3_acceptance_audit import load_jsonl


def adjudicate(
    rows: list[dict[str, Any]],
    comparison: dict[str, Any],
    adjudication: dict[str, Any],
) -> list[dict[str, Any]]:
    disagreement_ids = set(comparison["differences"])
    decisions = adjudication["decisions"]
    if disagreement_ids != set(decisions):
        missing = sorted(disagreement_ids - set(decisions))
        extra = sorted(set(decisions) - disagreement_ids)
        raise ValueError(f"adjudication coverage mismatch: missing={missing}, extra={extra}")
    rows_by_id = {row["id"]: row for row in rows}
    row = rows_by_id["rva3-006"]
    row["primary_span_type"] = "table_row"
    row["evidence"][0]["span_type"] = "table_row"
    row["demands"][0]["accepted_value_sets"] = [["0.40", "0.47"]]
    rows_by_id["rva3-025"]["demands"][0]["canonical_unit"] = None
    rows_by_id["rva3-026"]["demands"][0]["modality"] = "guarantee"
    reviewer = adjudication["reviewer"]
    for item in rows:
        decision = decisions.get(item["id"])
        item["annotation"] = {
            "author": "author-pass-1",
            "reviewer": reviewer,
            "review_state": "agreed",
            "adjudication_note": decision or "Independent hard labels matched the author labels.",
        }
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--comparison", required=True, type=Path)
    parser.add_argument("--adjudication", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = adjudicate(
        load_jsonl(args.dataset),
        json.loads(args.comparison.read_text(encoding="utf-8")),
        json.loads(args.adjudication.read_text(encoding="utf-8")),
    )
    args.output.write_text(
        "// Independently reviewed and source-adjudicated. V3 has not been run.\n"
        + "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in result)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"rows": len(result), "review_state": "agreed"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
