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

# Validation is frozen too, for a different reason: holdout freezing protects
# the acceptance set from being edited after tuning, while validation freezing
# makes a tuning run reproducible — the same parameters must be scored against
# the same questions to be comparable across experiments.
VALIDATION_DATASET = Path("evals/datasets/retrieval_validation_v1.jsonl")
VALIDATION_FREEZE_RECORD = Path("evals/datasets/VALIDATION_FREEZE.json")
QUOTA4_ACCEPTANCE_DATASET = Path(
    "evals/datasets/retrieval_quota4_acceptance_v1.jsonl"
)
QUOTA4_ACCEPTANCE_FREEZE_RECORD = Path(
    "evals/datasets/QUOTA4_ACCEPTANCE_FREEZE.json"
)
SAME_HEADING_ACCEPTANCE_DATASET = Path(
    "evals/datasets/retrieval_same_heading_acceptance_v1.jsonl"
)
SAME_HEADING_ACCEPTANCE_FREEZE_RECORD = Path(
    "evals/datasets/SAME_HEADING_ACCEPTANCE_FREEZE.json"
)


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


def build_record(path: Path, *, note: str, expected_split: str = "holdout") -> FreezeRecord:
    """Record a hash over a single-split dataset file.

    A freeze over a file that mixes splits is meaningless: editing one split
    would invalidate the other's record.  ``expected_split`` makes the intent
    explicit so validation and holdout cannot be frozen by accident.
    """
    result = load_dataset(path, require_graded=False)
    rows = [case for case in result.cases if case.split == expected_split]
    if not rows:
        raise ValueError(
            f"{path} contains no rows with split={expected_split!r}; a freeze record "
            "over an empty set would give false assurance"
        )
    other_splits = sorted({case.split for case in result.cases} - {expected_split})
    if other_splits:
        raise ValueError(
            f"{path} must contain {expected_split} rows only, found other splits: "
            f"{other_splits}. Mixing splits in one file makes the freeze meaningless; "
            f"keep each split in its own file and use {list(VALID_SPLITS)} for the rest."
        )
    return FreezeRecord(
        dataset=str(path),
        sha256=file_sha256(path),
        case_count=len(rows),
        case_ids=tuple(case.case_id for case in rows),
        frozen_at=datetime.now(UTC).isoformat(),
        note=note,
    )


def write_freeze(
    path: Path = HOLDOUT_DATASET,
    record_path: Path = FREEZE_RECORD,
    *,
    expected_split: str = "holdout",
    note: str | None = None,
) -> FreezeRecord:
    record = build_record(
        path,
        expected_split=expected_split,
        note=note
        or (
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
            f"DATASET DRIFT: {path} changed after the freeze was recorded.\n"
            f"  recorded: {recorded['sha256']}\n"
            f"  current:  {current_hash}\n"
            "Any metric produced before this change is void. Re-freeze and re-run; "
            "if this was the holdout, tuning must start over because the acceptance "
            "set has been seen."
        )
    return True, (
        f"intact: {recorded['case_count']} cases, sha256={current_hash[:16]}..., "
        f"frozen_at={recorded['frozen_at']}"
    )


VALIDATION_NOTE = (
    "Validation is the tuning split. Freezing it keeps ablation runs comparable: "
    "the same parameters must be scored against the same questions. It is "
    "expected to be read during tuning; the holdout record is the one that must "
    "not be read."
)


def freeze_targets() -> dict[str, tuple[Path, Path, str, str]]:
    """Map a split name to (dataset, record, expected_split, note)."""
    return {
        "holdout": (
            HOLDOUT_DATASET,
            FREEZE_RECORD,
            "holdout",
            "Holdout is not used for parameter tuning, threshold selection or "
            "failure analysis. Run once per candidate implementation; if the "
            "hash below changes, the previous acceptance run is void.",
        ),
        "validation": (
            VALIDATION_DATASET,
            VALIDATION_FREEZE_RECORD,
            "validation",
            VALIDATION_NOTE,
        ),
        "acceptance": (
            QUOTA4_ACCEPTANCE_DATASET,
            QUOTA4_ACCEPTANCE_FREEZE_RECORD,
            "acceptance",
            "Independent one-shot acceptance set for the fixed quota-4 retrieval "
            "candidate at b791ef6. It is not used for tuning or failure-driven "
            "changes; any dataset hash change voids the acceptance result.",
        ),
        "same-heading-acceptance": (
            SAME_HEADING_ACCEPTANCE_DATASET,
            SAME_HEADING_ACCEPTANCE_FREEZE_RECORD,
            "acceptance",
            "Independent one-shot acceptance set for the fixed same-heading "
            "adjacent-filter candidate at 1fe37f0. It is not used for tuning or "
            "failure-driven changes; any dataset hash change voids the result.",
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage dataset freeze records.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="Record the current hash.")
    group.add_argument("--check", action="store_true", help="Verify no drift occurred.")
    parser.add_argument(
        "--split",
        choices=sorted(freeze_targets()),
        default="holdout",
        help="Which split to freeze or verify.",
    )
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--record", type=Path, default=None)
    args = parser.parse_args()

    default_dataset, default_record, expected_split, note = freeze_targets()[args.split]
    dataset = args.dataset or default_dataset
    record_path = args.record or default_record

    if args.write:
        record = write_freeze(
            dataset, record_path, expected_split=expected_split, note=note
        )
        print(f"frozen {args.split}: {record.case_count} cases, sha256={record.sha256}")
        return
    ok, message = check_freeze(dataset, record_path)
    print(("OK   " if ok else "FAIL ") + message)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
