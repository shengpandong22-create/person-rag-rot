"""Apply the two remaining human-review corrections to the regression set.

1. ``ret-015`` referenced ``3.3 RRF 融合：为什么不能直接加分数``, which is a
   parent heading with no body text of its own, so the ingestion parser never
   emits a section for it and the label could not resolve.  The answer points
   actually live in its child section ``RRF 公式``, which contains the fusion
   score formula.  The label is repointed there.

2. ``ret-027``–``ret-030`` were missing an explicit ``label_origin``.  They
   defaulted to ``human`` via the schema, but leaving the field implicit is
   inconsistent with the other 26 rows and makes the file harder to audit.

Usage:
    python -m uv run python scripts/finalize_regression_labels.py [--apply]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _candidate in (_REPO_ROOT / "src", _REPO_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

DATASET = _REPO_ROOT / "evals" / "datasets" / "retrieval_regression_v1.jsonl"

# Section that actually carries the fusion-score content for ret-015.
# The abbreviated form did not resolve in the earlier pass, so it is still the
# bare suffix here; the full form is what it must become.
RET_015_FIXED_PATH = [
    "第 3 课：混合检索与可信 RAG 回答",
    "一、教案正文",
    "3.3 RRF 融合：为什么不能直接加分数",
    "RRF 公式",
]
RET_015_STALE_PATHS = (
    ["3.3 RRF 融合：为什么不能直接加分数"],
    [
        "第 3 课：混合检索与可信 RAG 回答",
        "一、教案正文",
        "3.3 RRF 融合：为什么不能直接加分数",
    ],
)
RET_015_ANSWER_POINTS = [
    "资料给出了融合分数公式 score = Σ 1/(k + rank) 及其量纲无关的排序作用",
    "融合分数同时使用两路排名，使双路共同命中的候选获得更高排序",
]
MISSING_ORIGIN_IDS = {"ret-027", "ret-028", "ret-029", "ret-030"}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    args = parser.parse_args()

    lines = args.dataset.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    changes: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            output.append(line)
            continue
        row = json.loads(stripped)
        case_id = str(row["id"])

        if case_id in MISSING_ORIGIN_IDS and "label_origin" not in row:
            row["label_origin"] = "human"
            changes.append(f"{case_id}: added label_origin=human")

        if case_id == "ret-015":
            for source in row.get("relevant_sources", []):
                if source.get("heading_path") in RET_015_STALE_PATHS:
                    source["heading_path"] = RET_015_FIXED_PATH
                    source["required_answer_points"] = RET_015_ANSWER_POINTS
                    changes.append(
                        f"{case_id}: repointed 3.3 -> 3.3 > RRF 公式 "
                        "(parent heading has no body, so it yields no section)"
                    )
        output.append(json.dumps(row, ensure_ascii=False))

    for item in changes:
        print(f"  {item}")
    print(f"total changes: {len(changes)}")

    if args.apply:
        args.dataset.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")
        print(f"written: {args.dataset}")
    else:
        print("(dry run; pass --apply to write)")


if __name__ == "__main__":
    main()
