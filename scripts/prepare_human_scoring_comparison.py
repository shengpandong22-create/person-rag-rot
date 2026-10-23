"""Create a blinded human-scoring worksheet from the fixed discrimination set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

DATASET = Path("evals/datasets/evaluation_discrimination_v1.jsonl")
OUTPUT_DIR = Path("evals/reviews/scoring-human-comparison-v1")
DIMENSIONS = ("correctness", "completeness", "reasoning", "communication")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_rows(dataset: Path) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    worksheet: list[dict[str, object]] = []
    key: list[dict[str, str]] = []
    for index, line in enumerate(dataset.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        blind_id = f"blind-{index:02d}"
        worksheet.append(
            {
                "blind_id": blind_id,
                "topic": row["topic"],
                "question": row["question"],
                "answer": row["answer"],
                "rubric": {
                    "correctness": "0–5：事实和结论是否正确。",
                    "completeness": "0–5：是否覆盖题目要求。",
                    "reasoning": "0–5：是否解释原因、流程或取舍。",
                    "communication": "0–5：表达是否清晰、结构是否可读。",
                },
                "reviewer_response": {
                    "correctness": None,
                    "completeness": None,
                    "reasoning": None,
                    "communication": None,
                    "needs_review": None,
                    "rationale": "",
                },
            }
        )
        key.append({"blind_id": blind_id, "case_id": str(row["id"])})
    return worksheet, key


def main() -> None:
    worksheet, key = prepare_rows(DATASET)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "worksheet.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in worksheet), encoding="utf-8"
    )
    (OUTPUT_DIR / "author_key.json").write_text(
        json.dumps(
            {"dataset": str(DATASET), "dataset_sha256": sha256_file(DATASET), "mapping": key},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"worksheet_rows": len(worksheet), "dataset_sha256": sha256_file(DATASET)}))


if __name__ == "__main__":
    main()
