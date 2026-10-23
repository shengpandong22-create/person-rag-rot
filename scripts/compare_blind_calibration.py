"""Compare two independently generated blind coarse-calibration outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_rows(path: Path) -> dict[str, dict[str, object]]:
    rows = {
        str(row["blind_id"]): row
        for row in (
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    if len(rows) != 12:
        raise ValueError(f"{path}: expected 12 unique blind rows, got {len(rows)}")
    return rows


def compare(
    left: dict[str, dict[str, object]], right: dict[str, dict[str, object]]
) -> dict[str, object]:
    if set(left) != set(right):
        raise ValueError("blind-id sets differ")
    details = []
    for blind_id in sorted(left):
        left_row = left[blind_id]
        right_row = right[blind_id]
        details.append(
            {
                "blind_id": blind_id,
                "quality_agrees": left_row.get("quality") == right_row.get("quality"),
                "review_agrees": left_row.get("needs_review") == right_row.get("needs_review"),
                "left_quality": left_row.get("quality"),
                "right_quality": right_row.get("quality"),
                "left_needs_review": left_row.get("needs_review"),
                "right_needs_review": right_row.get("needs_review"),
            }
        )
    return {
        "sample_count": len(details),
        "quality_agreement_count": sum(item["quality_agrees"] for item in details),
        "review_agreement_count": sum(item["review_agrees"] for item in details),
        "exact_pair_agreement_count": sum(
            item["quality_agrees"] and item["review_agrees"] for item in details
        ),
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = compare(load_rows(args.left), load_rows(args.right))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
