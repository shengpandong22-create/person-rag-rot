"""Detect question and label overlap between dataset splits.

Tuning on validation is only meaningful if the holdout set is genuinely
disjoint.  Two kinds of leakage matter:

* **Question duplication** — the same question in both splits means tuning on
  validation directly tunes the acceptance set.
* **Ground-truth overlap** — a validation row and a holdout row that cite the
  exact same section set are effectively the same evaluation, even if worded
  differently.

Usage:
    python -m uv run python scripts/check_split_overlap.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _candidate in (_REPO_ROOT / "src", _REPO_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from evals.schema import RetrievalEvalCase, load_dataset  # noqa: E402

DATASETS = {
    "regression": _REPO_ROOT / "evals" / "datasets" / "retrieval_regression_v1.jsonl",
    "validation": _REPO_ROOT / "evals" / "datasets" / "retrieval_validation_v1.jsonl",
    "holdout": _REPO_ROOT / "evals" / "datasets" / "retrieval_holdout_v1.jsonl",
}


def _normalise(text: str) -> str:
    return "".join(text.split()).casefold()


def _signature(case: RetrievalEvalCase) -> frozenset[str]:
    return frozenset(
        f"{source.document_logical_name} > {' > '.join(source.heading_path)}"
        for source in case.relevant_sources
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()
    del args

    cases: dict[str, list[RetrievalEvalCase]] = {}
    for name, path in DATASETS.items():
        if not path.exists():
            print(f"{name}: dataset missing ({path})")
            continue
        result = load_dataset(path, require_graded=False)
        cases[name] = list(result.cases)
        counts: dict[str, int] = {}
        for case in result.cases:
            key = str(case.split)
            counts[key] = counts.get(key, 0) + 1
        print(f"{name}: {len(result.cases)} rows, splits={counts}")

    names = [name for name in ("regression", "validation", "holdout") if name in cases]
    problems: list[str] = []
    for i, left_name in enumerate(names):
        for right_name in names[i + 1 :]:
            left = cases[left_name]
            right = cases[right_name]

            left_questions = {_normalise(str(case.question)): case.case_id for case in left}
            for case in right:
                key = _normalise(str(case.question))
                if key in left_questions:
                    problems.append(
                        f"duplicate question: {left_name}/{right_name} "
                        f"{left_questions[key]} == {case.case_id}"
                    )

            signatures: dict[frozenset[str], str] = {}
            for case in left:
                signature = _signature(case)
                if signature:
                    signatures.setdefault(signature, case.case_id)
            for case in right:
                signature = _signature(case)
                if signature and signature in signatures:
                    problems.append(
                        f"identical ground truth: {left_name}/{right_name} "
                        f"{signatures[signature]} == {case.case_id}"
                    )

    if problems:
        print(f"\nOVERLAP DETECTED ({len(problems)}):")
        for item in problems:
            print(f"  - {item}")
        raise SystemExit(1)
    print("\nno question or ground-truth overlap between splits")


if __name__ == "__main__":
    main()
