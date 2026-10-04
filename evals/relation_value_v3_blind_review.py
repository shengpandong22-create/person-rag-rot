"""Create a label-blind reviewer worksheet for the V3 acceptance draft."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evals.relation_value_v3_acceptance_audit import load_jsonl


def create_worksheet(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    worksheet: list[dict[str, Any]] = []
    for row in rows:
        worksheet.append(
            {
                "id": row["id"],
                "question": row["question"],
                "evidence": [
                    {
                        "evidence_id": item["evidence_id"],
                        "chunk_id": item["chunk_id"],
                        "document_logical_name": item["document_logical_name"],
                        "heading_path": item["heading_path"],
                        "span_text": item["span_text"],
                        "span_sha256": item["span_sha256"],
                        "source_content_hash": item["source_content_hash"],
                    }
                    for item in row["evidence"]
                ],
                "reviewer_annotation": {
                    "answerability": None,
                    "confusion_type": None,
                    "primary_relation_role": None,
                    "primary_span_type": None,
                    "demands": [],
                    "rationale": None,
                },
            }
        )
    return worksheet


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    worksheet = create_worksheet(load_jsonl(args.dataset))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "// Label-blind worksheet: author labels and candidate output are excluded.\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in worksheet
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "rows": len(worksheet),
                "author_labels_included": False,
                "candidate_output_included": False,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
