from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from agent_mentor.domain.evidence import EvidenceGatePolicy
from agent_mentor.infrastructure.retriever import RetrievalExperimentMode
from evals.runners.retrieval_runner import run_retrieval_eval
from evals.runners.scoring_runner import run_scoring_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AgentMentor evaluation datasets.")
    parser.add_argument(
        "suite",
        choices=("retrieval", "retrieval-ablation", "scoring", "all"),
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
    parser.add_argument(
        "--experiment-mode",
        type=RetrievalExperimentMode,
        choices=tuple(RetrievalExperimentMode),
        default=RetrievalExperimentMode.RRF_HEURISTIC,
    )
    parser.add_argument(
        "--evidence-gate-policy",
        type=EvidenceGatePolicy,
        choices=tuple(EvidenceGatePolicy),
        default=None,
    )
    args = parser.parse_args()

    if args.suite in {"retrieval", "retrieval-ablation", "all"}:
        if args.knowledge_base_id is None:
            parser.error("--knowledge-base-id is required for retrieval eval.")
        if args.suite == "retrieval-ablation":
            if "holdout" in args.retrieval_dataset.name.lower():
                parser.error("Ablation is forbidden on holdout; use validation only.")
            reports: dict[str, dict[str, object]] = {}
            for mode in RetrievalExperimentMode:
                report = asyncio.run(
                    run_retrieval_eval(
                        dataset_path=args.retrieval_dataset,
                        knowledge_base_id=args.knowledge_base_id,
                        output_dir=args.output_dir / mode.value,
                        top_k=args.top_k,
                        candidate_k=args.candidate_k,
                        experiment_mode=mode,
                        evidence_gate_policy=args.evidence_gate_policy,
                    )
                )
                reports[mode.value] = report.metrics
            args.output_dir.mkdir(parents=True, exist_ok=True)
            (args.output_dir / "ablation_comparison.json").write_text(
                json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            metric_names = (
                "recall_at_1",
                "recall_at_3",
                "recall_at_6",
                "mrr",
                "full_answerability_accuracy",
                "partial_answerability_accuracy",
                "negative_rejection_accuracy",
                "latency_p50_ms",
                "latency_p95_ms",
                "average_candidate_count",
            )
            lines = [
                "# Validation Retrieval Ablation",
                "",
                "| mode | " + " | ".join(metric_names) + " |",
                "|---|" + "---:|" * len(metric_names),
            ]
            for mode, metrics in reports.items():
                lines.append(
                    f"| {mode} | " + " | ".join(str(metrics[name]) for name in metric_names) + " |"
                )
            (args.output_dir / "ablation_comparison.md").write_text(
                "\n".join(lines) + "\n", encoding="utf-8"
            )
            print({"retrieval_ablation": reports})
        else:
            report = asyncio.run(
                run_retrieval_eval(
                    dataset_path=args.retrieval_dataset,
                    knowledge_base_id=args.knowledge_base_id,
                    output_dir=args.output_dir,
                    top_k=args.top_k,
                    candidate_k=args.candidate_k,
                    experiment_mode=args.experiment_mode,
                    evidence_gate_policy=args.evidence_gate_policy,
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
