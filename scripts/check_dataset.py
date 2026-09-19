"""Ad-hoc dataset sanity check used while migrating evaluation labels.

Usage:
    python -m uv run python scripts/check_dataset.py <dataset.jsonl> [--require-graded]

Prints the answerability / origin / split distribution so a migration can be
eyeballed before it is wired into the runner.  Pass ``--require-graded`` to
assert that every answerable row already carries a human label.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

# Allow running directly from the repo root without PYTHONPATH being set.
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _candidate in (_REPO_ROOT / "src", _REPO_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from evals.schema import graded_cases, load_dataset, ungraded_cases  # noqa: E402


def main() -> None:
    args = [item for item in sys.argv[1:] if not item.startswith("--")]
    require_graded = "--require-graded" in sys.argv
    path = Path(args[0] if args else "evals/datasets/retrieval_regression_v1.jsonl")
    result = load_dataset(path, require_graded=require_graded)
    cases = result.cases
    print(f"schema_version: {result.schema_version}")
    print(f"dataset: {path}")
    print(f"require_graded: {require_graded}")
    print(f"total: {len(cases)}")
    print(f"answerability: {dict(Counter(case.answerability.value for case in cases))}")
    print(f"label_origin: {dict(Counter(case.label_origin.value for case in cases))}")
    print(f"split: {dict(Counter(case.split for case in cases))}")
    negatives = [case for case in cases if case.answerability.value == "none"]
    print(f"negative_reason: {dict(Counter(str(case.negative_reason) for case in negatives))}")
    # Reuse the schema helpers so this script and the runner cannot disagree on
    # what counts as a graded row.
    print(f"graded_rows: {len(graded_cases(cases))}")
    print(f"ungraded_rows: {len(ungraded_cases(cases))}")


if __name__ == "__main__":
    main()
