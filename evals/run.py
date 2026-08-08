from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from uuid import UUID

from evals.runners.retrieval_runner import run_retrieval_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AgentMentor evaluation datasets.")
    parser.add_argument(
        "suite",
        choices=("retrieval",),
        help="Evaluation suite to run.",
    )
    parser.add_argument("--knowledge-base-id", required=True, type=UUID)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/datasets/retrieval_v1.jsonl"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("evals/reports"))
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--candidate-k", type=int, default=20)
    args = parser.parse_args()

    if args.suite == "retrieval":
        report = asyncio.run(
            run_retrieval_eval(
                dataset_path=args.dataset,
                knowledge_base_id=args.knowledge_base_id,
                output_dir=args.output_dir,
                top_k=args.top_k,
                candidate_k=args.candidate_k,
            )
        )
        print(report.metrics)


if __name__ == "__main__":
    main()
