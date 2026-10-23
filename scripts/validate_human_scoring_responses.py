"""Validate a completed blinded scoring worksheet without seeing author labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DIMENSIONS = ("correctness", "completeness", "reasoning", "communication")


def validate_rows(rows: list[dict[str, object]], expected_count: int) -> list[str]:
    errors: list[str] = []
    if len(rows) != expected_count:
        errors.append(f"expected {expected_count} rows, found {len(rows)}")
    seen: set[str] = set()
    for row in rows:
        blind_id = row.get("blind_id")
        if not isinstance(blind_id, str) or not blind_id:
            errors.append("row has missing blind_id")
            continue
        if blind_id in seen:
            errors.append(f"duplicate blind_id: {blind_id}")
        seen.add(blind_id)
        response = row.get("reviewer_response")
        if not isinstance(response, dict):
            errors.append(f"{blind_id}: missing reviewer_response")
            continue
        for dimension in DIMENSIONS:
            score = response.get(dimension)
            if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 5:
                errors.append(f"{blind_id}: {dimension} must be an integer from 0 to 5")
        if not isinstance(response.get("needs_review"), bool):
            errors.append(f"{blind_id}: needs_review must be boolean")
        rationale = response.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            errors.append(f"{blind_id}: rationale is required")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("worksheet", type=Path)
    parser.add_argument("--expected-count", type=int, default=12)
    args = parser.parse_args()
    rows = [
        json.loads(line)
        for line in args.worksheet.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    errors = validate_rows(rows, args.expected_count)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
