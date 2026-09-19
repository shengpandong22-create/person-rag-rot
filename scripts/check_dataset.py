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

from evals.schema import load_dataset


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
    graded = [case for case in cases if case.relevant_sources]
    print(f"graded_rows: {len(graded)}")
    print(f"ungraded_rows: {len(cases) - len(graded)}")


if __name__ == "__main__":
    main()
