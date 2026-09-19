"""Print one candidate package in a readable form for spot-checking.

Usage:
    python -m uv run python scripts/show_candidate_package.py <case_id> [jsonl]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_QUEUE = Path("evals/review/candidates_retrieval_regression_v1.jsonl")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    parser.add_argument("queue", nargs="?", type=Path, default=DEFAULT_QUEUE)
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in args.queue.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matched = [row for row in rows if row["id"] == args.case_id]
    if not matched:
        raise SystemExit(f"case {args.case_id} not found in {args.queue}")
    row = matched[0]

    print(f"id: {row['id']}")
    print(f"question: {row['question']}")
    print(f"answerability: {row['answerability']}")
    print(f"suggested_by: {row['suggested_by']}")
    print(f"human_verified: {row['human_verified']}")
    print(f"candidates: {len(row['candidates'])}")
    for index, candidate in enumerate(row["candidates"], start=1):
        print(f"\n[{index}] score={candidate['match_score']}")
        print(f"    doc: {candidate['document_logical_name']}")
        print(f"    path: {' > '.join(candidate['heading_path'])}")
        print(f"    fingerprint: {candidate['content_fingerprint'][:20]}...")
        print(f"    status: {candidate['review_status']}")
        for point in candidate["suggested_answer_points"]:
            print(f"    - {point}")


if __name__ == "__main__":
    main()
