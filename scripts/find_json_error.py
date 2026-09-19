"""Locate malformed JSON lines in a dataset file.

Usage:
    python -m uv run python scripts/find_json_error.py <dataset.jsonl>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()

    failures = 0
    for number, line in enumerate(
        args.dataset.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        try:
            json.loads(stripped)
        except json.JSONDecodeError as error:
            failures += 1
            print(f"line {number}: {error}")
            start = max(0, error.pos - 60)
            print(f"  context: ...{stripped[start : error.pos + 40]}...")
    if failures:
        print(f"\n{failures} malformed line(s)")
        raise SystemExit(1)
    print("all lines parse")


if __name__ == "__main__":
    main()
