from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import select

from agent_mentor.config import get_settings
from agent_mentor.infrastructure.database.models import KnowledgeChunkModel
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)
from evals.claim_normalization import NormalizedClaim, normalize_claim

DEFAULT_NLI_MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
LABELS = ("entailment", "neutral", "contradiction")


@dataclass(frozen=True, slots=True)
class NLIPairScore:
    chunk_id: str
    entailment: float
    neutral: float
    contradiction: float
    predicted_label: str


@dataclass(frozen=True, slots=True)
class NLClaimResult:
    claim_id: str
    text: str
    hypothesis: str | None
    normalization_strategy: str
    normalization_reason: str | None
    deterministic_status: str
    semantic_status: str
    combined_status: str
    selected_chunk_id: str | None
    scores: tuple[NLIPairScore, ...]


def aggregate_claim_statuses(statuses: list[str]) -> str:
    if statuses and all(status == "supported" for status in statuses):
        return "full"
    if any(status == "supported" for status in statuses):
        return "partial"
    return "none"


def semantic_status(scores: list[NLIPairScore]) -> tuple[str, str | None]:
    entailed = [score for score in scores if score.predicted_label == "entailment"]
    if entailed:
        best = max(entailed, key=lambda score: score.entailment)
        return "supported", best.chunk_id
    contradicted = [score for score in scores if score.predicted_label == "contradiction"]
    if contradicted:
        best = max(contradicted, key=lambda score: score.contradiction)
        return "contradicted", best.chunk_id
    return "unknown", None


def combined_status(deterministic: str, semantic: str, *, semantic_available: bool = True) -> str:
    if not semantic_available:
        return deterministic
    if deterministic == "unsupported":
        return "unsupported"
    if semantic == "contradicted":
        return "contradicted"
    if semantic == "supported":
        return "supported"
    return "unknown"


def evaluate_predictions(
    rows: list[dict[str, Any]], predictions: dict[str, str]
) -> dict[str, object]:
    labels = ("full", "partial", "none")
    confusion = {
        actual: {
            predicted: sum(
                row["answerability"] == actual and predictions[row["id"]] == predicted
                for row in rows
            )
            for predicted in labels
        }
        for actual in labels
    }
    accuracy = {
        label: _rate(
            predictions[row["id"]] == label
            for row in rows
            if row["answerability"] == label
        )
        for label in labels
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["answerability"] == "none":
            grouped[row.get("negative_reason") or "unspecified"].append(row)
    return {
        "full_acceptance_rate": accuracy["full"],
        "partial_boundary_detection_rate": accuracy["partial"],
        "none_rejection_rate": _rate(
            predictions[row["id"]] != "full"
            for row in rows
            if row["answerability"] == "none"
        ),
        "macro_accuracy": round(sum(accuracy.values()) / len(accuracy), 4),
        "confusion_matrix": confusion,
        "rejection_by_negative_reason": {
            reason: _rate(predictions[row["id"]] != "full" for row in group)
            for reason, group in sorted(grouped.items())
        },
        "false_full_case_ids": [
            row["id"]
            for row in rows
            if row["answerability"] != "full" and predictions[row["id"]] == "full"
        ],
        "false_rejection_case_ids": [
            row["id"]
            for row in rows
            if row["answerability"] == "full" and predictions[row["id"]] != "full"
        ],
    }


class NLIModel:
    def __init__(self, model_name: str) -> None:
        import torch
        import transformers
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.model_name = model_name
        self.transformers_version = transformers.__version__
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self._model.to(self.device)
        self._model.eval()
        id2label = {
            int(index): str(label).lower()
            for index, label in self._model.config.id2label.items()
        }
        if tuple(id2label[index] for index in range(3)) != LABELS:
            raise ValueError(f"Unexpected NLI label mapping: {id2label}")

    def score(self, pairs: list[tuple[str, str, str]], batch_size: int) -> list[NLIPairScore]:
        results: list[NLIPairScore] = []
        for offset in range(0, len(pairs), batch_size):
            batch = pairs[offset : offset + batch_size]
            encoded = self._tokenizer(
                [premise for _, premise, _ in batch],
                [hypothesis for _, _, hypothesis in batch],
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            encoded = {key: value.to(self.device) for key, value in encoded.items()}
            with self._torch.inference_mode():
                logits = self._model(**encoded).logits
                probabilities = self._torch.softmax(logits, dim=-1).cpu().tolist()
            for (chunk_id, _premise, _hypothesis), values in zip(
                batch, probabilities, strict=True
            ):
                predicted = max(range(3), key=lambda index: values[index])
                results.append(
                    NLIPairScore(
                        chunk_id=chunk_id,
                        entailment=round(float(values[0]), 6),
                        neutral=round(float(values[1]), 6),
                        contradiction=round(float(values[2]), 6),
                        predicted_label=LABELS[predicted],
                    )
                )
        return results


async def _load_chunk_content(chunk_ids: set[UUID]) -> dict[str, str]:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            rows = (
                await session.execute(
                    select(KnowledgeChunkModel.id, KnowledgeChunkModel.content).where(
                        KnowledgeChunkModel.id.in_(chunk_ids)
                    )
                )
            ).all()
            return {str(chunk_id): content for chunk_id, content in rows}
    finally:
        await engine.dispose()


async def run_nli_eval(
    *, source_report: Path, output_dir: Path, model_name: str, batch_size: int
) -> dict[str, object]:
    report = json.loads(source_report.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = report["cases"]
    chunk_ids = {
        UUID(chunk["chunk_id"])
        for row in rows
        for chunk in row["top_chunks"][:3]
    }
    content = await _load_chunk_content(chunk_ids)
    missing = sorted(str(chunk_id) for chunk_id in chunk_ids if str(chunk_id) not in content)
    if missing:
        raise ValueError(f"Could not resolve {len(missing)} report chunks: {missing[:3]}")

    pair_keys: list[tuple[str, str, str, str]] = []
    model_pairs: list[tuple[str, str, str]] = []
    normalizations: dict[tuple[str, str], NormalizedClaim] = {}
    for row in rows:
        for claim in row["evidence_assessment"]["claim_assessments"]:
            normalization = normalize_claim(claim["text"])
            normalizations[(row["id"], claim["claim_id"])] = normalization
            if normalization.hypothesis is None:
                continue
            top_chunks = row["top_chunks"][:3]
            for chunk in top_chunks:
                chunk_id = chunk["chunk_id"]
                pair_keys.append((row["id"], claim["claim_id"], chunk_id, claim["text"]))
                model_pairs.append((chunk_id, content[chunk_id], normalization.hypothesis))
            combined_id = "top3-combined"
            combined_premise = "\n\n".join(content[chunk["chunk_id"]] for chunk in top_chunks)
            pair_keys.append((row["id"], claim["claim_id"], combined_id, claim["text"]))
            model_pairs.append((combined_id, combined_premise, normalization.hypothesis))

    started = perf_counter()
    model = NLIModel(model_name)
    scores = model.score(model_pairs, batch_size)
    duration_ms = round((perf_counter() - started) * 1000, 4)
    grouped_scores: dict[tuple[str, str], list[NLIPairScore]] = defaultdict(list)
    for key, score in zip(pair_keys, scores, strict=True):
        grouped_scores[(key[0], key[1])].append(score)

    case_details: list[dict[str, object]] = []
    predictions = {"deterministic_only": {}, "semantic_only": {}, "combined": {}}
    for row in rows:
        claim_results: list[NLClaimResult] = []
        for claim in row["evidence_assessment"]["claim_assessments"]:
            pair_scores = grouped_scores[(row["id"], claim["claim_id"])]
            semantic, selected_chunk_id = semantic_status(pair_scores)
            deterministic = claim["status"]
            normalization = normalizations[(row["id"], claim["claim_id"])]
            claim_results.append(
                NLClaimResult(
                    claim_id=claim["claim_id"],
                    text=claim["text"],
                    hypothesis=normalization.hypothesis,
                    normalization_strategy=normalization.strategy,
                    normalization_reason=normalization.reason,
                    deterministic_status=deterministic,
                    semantic_status=semantic,
                    combined_status=combined_status(
                        deterministic,
                        semantic,
                        semantic_available=normalization.hypothesis is not None,
                    ),
                    selected_chunk_id=selected_chunk_id,
                    scores=tuple(pair_scores),
                )
            )
        for policy, field in (
            ("deterministic_only", "deterministic_status"),
            ("semantic_only", "semantic_status"),
            ("combined", "combined_status"),
        ):
            predictions[policy][row["id"]] = aggregate_claim_statuses(
                [getattr(result, field) for result in claim_results]
            )
        case_details.append(
            {
                "id": row["id"],
                "answerability": row["answerability"],
                "negative_reason": row.get("negative_reason"),
                "predictions": {
                    policy: values[row["id"]] for policy, values in predictions.items()
                },
                "claims": [asdict(result) for result in claim_results],
            }
        )

    payload: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_report": str(source_report),
        "source_report_sha256": sha256(source_report.read_bytes()).hexdigest(),
        "source_metadata": report["metadata"],
        "model": {
            "name": model.model_name,
            "labels": list(LABELS),
            "transformers_version": model.transformers_version,
            "device": model.device,
            "batch_size": batch_size,
        },
        "inference_pair_count": len(model_pairs),
        "normalized_claim_count": sum(
            item.hypothesis is not None for item in normalizations.values()
        ),
        "unresolved_claim_count": sum(
            item.hypothesis is None for item in normalizations.values()
        ),
        "evidence_contexts": ["individual_top3_chunks", "concatenated_top3_context"],
        "inference_duration_ms": duration_ms,
        "metrics": {
            policy: evaluate_predictions(rows, values)
            for policy, values in predictions.items()
        },
        "cases": case_details,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "nli_gate_eval.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def _rate(values: Any) -> float:
    items = list(values)
    return round(sum(bool(item) for item in items) / len(items), 4) if items else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run claim/evidence NLI evaluation.")
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_NLI_MODEL)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    payload = asyncio.run(
        run_nli_eval(
            source_report=args.source_report,
            output_dir=args.output_dir,
            model_name=args.model,
            batch_size=args.batch_size,
        )
    )
    print(payload["metrics"])


if __name__ == "__main__":
    main()
