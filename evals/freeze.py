"""Holdout freezing so tuning cannot quietly peek at the acceptance set.

A personal project cannot run a true double-blind holdout, so the practical
guarantee is weaker but still meaningful: the holdout file content is hashed
and that hash is recorded **before** tuning starts.  Any later modification to
the holdout file changes the hash, and every report carries the freeze record
it was produced under, so a post-hoc edit is visible in the report itself.

Usage:
    python -m uv run python -m evals.freeze --check      # verify no drift
    python -m uv run python -m evals.freeze --write      # record the freeze
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.schema import VALID_SPLITS, load_dataset

HOLDOUT_DATASET = Path("evals/datasets/retrieval_holdout_v1.jsonl")
FREEZE_RECORD = Path("evals/datasets/HOLDOUT_FREEZE.json")


@dataclass(frozen=True, slots=True)
class FreezeRecord:
    dataset: str
    sha256: str
    case_count: int
    case_ids: tuple[str, ...]
    frozen_at: str
    note: str

    def to_json(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "sha256": self.sha256,
            "case_count": self.case_count,
            "case_ids": list(self.case_ids),
            "frozen_at": self.frozen_at,
            "note": self.note,
        }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_record(path: Path, *, note: str) -> FreezeRecord:
    result = load_dataset(path, require_graded=False)
    holdout = [case for case in result.cases if case.split == "holdout"]
    if not holdout:
        raise ValueError(
            f"{path} contains no rows with split='holdout'; a freeze record over an "
            "empty holdout would give false assurance"
        )
    non_holdout = sorted({case.split for case in result.cases} - {"holdout"})
    if non_holdout:
        raise ValueError(
            f"{path} must contain holdout rows only, found other splits: {non_holdout}. "
            "Mixing splits in one file makes the freeze meaningless; keep "
            f"holdout in its own file and use {list(VALID_SPLITS)} for the rest."
        )
    return FreezeRecord(
        dataset=str(path),
        sha256=file_sha256(path),
        case_count=len(holdout),
        case_ids=tuple(case.case_id for case in holdout),
        frozen_at=datetime.now(UTC).isoformat(),
        note=note,
    )


def write_freeze(path: Path = HOLDOUT_DATASET, record_path: Path = FREEZE_RECORD) -> FreezeRecord:
    record = build_record(
        path,
        note=(
            "Holdout is not used for parameter tuning, threshold selection or "
            "failure analysis. Run once per candidate implementation; if the "
            "hash below changes, the previous acceptance run is void."
        ),
    )
    record_path.write_text(
        json.dumps(record.to_json(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record


def check_freeze(
    path: Path = HOLDOUT_DATASET,
    record_path: Path = FREEZE_RECORD,
) -> tuple[bool, str]:
    """Return (ok, message) comparing the live holdout against the record."""
    if not record_path.exists():
        return False, f"no freeze record at {record_path}; run --write before tuning"
    recorded = json.loads(record_path.read_text(encoding="utf-8"))
    if not path.exists():
        return False, f"holdout dataset missing: {path}"
    current_hash = file_sha256(path)
    if current_hash != recorded["sha256"]:
        return False, (
            "HOLDOUT DRIFT: holdout file changed after the freeze was recorded.\n"
            f"  recorded: {recorded['sha256']}\n"
            f"  current:  {current_hash}\n"
            "Any acceptance number produced before this change is void; re-freeze "
            "and re-run tuning from scratch if the holdout was edited."
        )
    return True, (
        f"holdout intact: {recorded['case_count']} cases, sha256={current_hash[:16]}..., "
        f"frozen_at={recorded['frozen_at']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the retrieval holdout freeze.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="Record the current holdout hash.")
    group.add_argument("--check", action="store_true", help="Verify the holdout has not drifted.")
    parser.add_argument("--dataset", type=Path, default=HOLDOUT_DATASET)
    parser.add_argument("--record", type=Path, default=FREEZE_RECORD)
    args = parser.parse_args()

    if args.write:
        record = write_freeze(args.dataset, args.record)
        print(f"frozen: {record.case_count} cases, sha256={record.sha256}")
        return
    ok, message = check_freeze(args.dataset, args.record)
    print(("OK   " if ok else "FAIL ") + message)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
