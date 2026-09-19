"""Verify the holdout freeze hash survives a git round-trip.

Compares the sha256 of the blob stored in HEAD against the sha256 of the
working-tree file.  If they differ, ``evals.freeze --check`` would report a
false drift on a fresh clone, which would make the freeze worthless.

Usage:
    python -m uv run python scripts/verify_holdout_hash.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

DATASET = Path("evals/datasets/retrieval_holdout_v1.jsonl")
RECORD = Path("evals/datasets/HOLDOUT_FREEZE.json")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    if not DATASET.exists():
        raise SystemExit(f"missing {DATASET}")

    local = sha256_bytes(DATASET.read_bytes())
    blob = subprocess.run(
        ["git", "cat-file", "-p", f"HEAD:{DATASET.as_posix()}"],
        capture_output=True,
        check=True,
    ).stdout
    committed = sha256_bytes(blob)

    print(f"committed (HEAD) : {committed}")
    print(f"working tree     : {local}")
    if committed != local:
        print("FAIL: git round-trip changes the bytes; freeze hash is unreliable.")
        sys.exit(1)

    if RECORD.exists():
        recorded = RECORD.read_text(encoding="utf-8")
        marker = '"sha256": "'
        start = recorded.find(marker)
        if start != -1:
            value = recorded[start + len(marker) : recorded.find('"', start + len(marker))]
            print(f"freeze record    : {value}")
            if value != local:
                print("FAIL: freeze record does not match the file it claims to protect.")
                sys.exit(1)

    print("OK: holdout bytes are stable across the git boundary.")


if __name__ == "__main__":
    main()
