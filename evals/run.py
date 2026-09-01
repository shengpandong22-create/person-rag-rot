from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from uuid import UUID

from evals.runners.retrieval_runner import run_retrieval_eval
from evals.runners.scoring_runner import run_scoring_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AgentMentor evaluation datasets.")
    parser.add_argument(
        "suite",
        choices=("retrieval", "scoring", "all"),
        help="Evaluation suite to run.",
    )
    parser.add_argument("--knowledge-base-id", type=UUID)
    parser.add_argument(
        "--retrieval-dataset",
        type=Path,
        default=Path("evals/datasets/retrieval_v1.jsonl"),
    )
    parser.add_argument(
        "--scoring-dataset",
        type=Path,
        default=Path("evals/datasets/evaluation_v1.jsonl"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("evals/reports"))
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--use-llm-scoring", action="store_true")
    args = parser.parse_args()

    if args.suite in {"retrieval", "all"}:
        if args.knowledge_base_id is None:
            parser.error("--knowledge-base-id is required for retrieval eval.")
        report = asyncio.run(
            run_retrieval_eval(
                dataset_path=args.retrieval_dataset,
                knowledge_base_id=args.knowledge_base_id,
                output_dir=args.output_dir,
                top_k=args.top_k,
                candidate_k=args.candidate_k,
            )
        )
        print({"retrieval": report.metrics})
    if args.suite in {"scoring", "all"}:
        report = asyncio.run(
            run_scoring_eval(
                dataset_path=args.scoring_dataset,
                output_dir=args.output_dir,
                use_llm=args.use_llm_scoring,
            )
        )
        print({"scoring": report.metrics})


if __name__ == "__main__":
    main()
