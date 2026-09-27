from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from agent_mentor.config import get_settings
from agent_mentor.infrastructure.llm import OpenAICompatibleLLMGateway
from agent_mentor.ports.llm_gateway import Message, ModelPolicy, TraceContext
from evals.nli_gate import DEFAULT_NLI_MODEL, NLIModel, NLIPairScore
from evals.provenance import collect_git_state

NLI_STATUS = {"entailment": "supported", "neutral": "unknown", "contradiction": "contradicted"}
PROMPT_VERSION = "draft_claim_extractor_boundary_v2"
SYSTEM_PROMPT = (
    "将内部草稿答案拆成原子事实声明。逐句完整提取，不遗漏；只复制草稿中明确出现的事实，"
    "不改写、不补充、不推断。边界规则：一、只有独立谓词或独立结论才拆分；同一谓词后的"
    "并列对象保持为一条。二、复合句按逗号、分号和转折词拆成最小子句，保留子句原文，"
    "不要为子句补写主语或语气词。三、JSON 或键值内容每个字段各生成一条“字段 是 值”；"
    "标题、项目符号、代码围栏不是声明。四、语义重复的声明只保留第一次出现的原文。"
    "直接回答问题的声明 required=true，补充信息 required=false；所有 origin 必须为 model_draft。"
)


class ExtractedDraftClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=500)
    required: bool
    origin: str = Field(pattern="^model_draft$")


class DraftClaimExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ExtractedDraftClaim] = Field(max_length=20)


class ExpectedExtractionClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=500)
    required: bool


class ClaimExtractionFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    draft_answer: str = Field(min_length=1)
    expected_claims: list[ExpectedExtractionClaim] = Field(min_length=1, max_length=20)
    category: str = Field(default="baseline", min_length=1, max_length=64)


class NLIScorer(Protocol):
    def score(self, pairs: list[tuple[str, str, str]], batch_size: int) -> list[NLIPairScore]: ...


def _key(text: str) -> str:
    return re.sub(r"[\s。！？!?，,；;]+", "", text).casefold()


def load_extraction_fixtures(path: Path) -> tuple[ClaimExtractionFixture, ...]:
    fixtures: list[ClaimExtractionFixture] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        fixture = ClaimExtractionFixture.model_validate_json(line)
        if fixture.id in seen:
            raise ValueError(f"duplicate fixture id at line {line_number}: {fixture.id}")
        seen.add(fixture.id)
        fixtures.append(fixture)
    if not fixtures:
        raise ValueError("claim extraction fixture dataset must not be empty")
    return tuple(fixtures)


def compute_extractor_metrics(rows: list[dict[str, Any]]) -> dict[str, int | float]:
    total_required = sum(int(row["required_count"]) for row in rows)
    required_hits = sum(int(row["required_hit_count"]) for row in rows)
    total_extracted = sum(len(row["extracted_claims"]) for row in rows)
    total_extra = sum(int(row["extra_count"]) for row in rows)
    total_duplicates = sum(int(row.get("semantic_duplicate_count", 0)) for row in rows)
    supported = sum(
        claim.get("nli_status") == "supported"
        for row in rows
        for claim in row["extracted_claims"]
    )
    return {
        "schema_valid_rate": round(sum(bool(row["schema_valid"]) for row in rows) / len(rows), 4),
        "required_claim_recall": round(required_hits / total_required, 4),
        "extra_claim_rate": round(total_extra / total_extracted, 4) if total_extracted else 0.0,
        "unsupported_claim_rate": round((total_extracted - supported) / total_extracted, 4)
        if total_extracted
        else 0.0,
        "nli_retained_claim_rate": round(supported / total_extracted, 4)
        if total_extracted
        else 0.0,
        "semantic_duplicate_rate": round(total_duplicates / total_extracted, 4)
        if total_extracted
        else 0.0,
        "total_extracted_claims": total_extracted,
    }


def mark_semantic_duplicates(
    rows: list[dict[str, Any]], nli: NLIScorer, batch_size: int
) -> None:
    pairs: list[tuple[str, str, str]] = []
    locations: list[tuple[int, int, int]] = []
    for row_index, row in enumerate(rows):
        claims = row["extracted_claims"]
        for right in range(1, len(claims)):
            for left in range(right):
                pair_id = f"{row['id']}:{left}:{right}"
                pairs.extend(
                    [
                        (pair_id, claims[left]["text"], claims[right]["text"]),
                        (pair_id, claims[right]["text"], claims[left]["text"]),
                    ]
                )
                locations.append((row_index, left, right))
    scores = nli.score(pairs, batch_size)
    for row in rows:
        row["semantic_duplicate_count"] = 0
    for pair_index, (row_index, left, right) in enumerate(locations):
        forward = scores[pair_index * 2]
        reverse = scores[pair_index * 2 + 1]
        if forward.predicted_label != "entailment" or reverse.predicted_label != "entailment":
            continue
        claim = rows[row_index]["extracted_claims"][right]
        if "semantic_duplicate_of" not in claim:
            claim["semantic_duplicate_of"] = rows[row_index]["extracted_claims"][left]["claim_id"]
            rows[row_index]["semantic_duplicate_count"] += 1


async def run_extractor_eval(dataset: Path, output_dir: Path, batch_size: int) -> dict[str, object]:
    settings = get_settings()
    if not settings.llm_base_url or not settings.llm_api_key or not settings.llm_default_model:
        raise ValueError("LLM configuration is required for claim extractor evaluation")
    cases = load_extraction_fixtures(dataset)
    gateway = OpenAICompatibleLLMGateway(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        default_model=settings.llm_default_model,
    )
    rows: list[dict[str, Any]] = []
    started = perf_counter()
    try:
        for case in cases:
            try:
                output = await gateway.generate_structured(
                    operation="eval_draft_claim_extraction",
                    messages=[
                        Message(
                            "system",
                            SYSTEM_PROMPT,
                        ),
                        Message(
                            "user",
                            f"问题：{case.question}\n内部草稿：\n{case.draft_answer}",
                        ),
                    ],
                    response_model=DraftClaimExtractionOutput,
                    model_policy=ModelPolicy(timeout_seconds=60, max_retries=1),
                    trace_context=TraceContext(str(uuid4()), "eval_draft_claim_extraction"),
                )
                extracted = [claim.model_dump() for claim in output.claims]
                error = None
            except Exception as exc:  # evaluation must count invalid output, not hide it
                extracted = []
                error = f"{type(exc).__name__}: {exc}"
            expected = [claim.model_dump() for claim in case.expected_claims]
            expected_keys = {_key(item["text"]): item for item in expected}
            extracted_keys = {_key(item["text"]): item for item in extracted}
            required = {key for key, item in expected_keys.items() if item["required"]}
            rows.append(
                {
                    "id": case.id,
                    "schema_valid": error is None,
                    "error": error,
                    "evidence": case.evidence,
                    "expected_claims": expected,
                    "extracted_claims": extracted,
                    "required_hit_count": len(required & extracted_keys.keys()),
                    "required_count": len(required),
                    "extra_count": len(extracted_keys.keys() - expected_keys.keys()),
                }
            )
    finally:
        await gateway.aclose()

    nli = NLIModel(DEFAULT_NLI_MODEL)
    pairs: list[tuple[str, str, str]] = []
    locations: list[tuple[int, int]] = []
    for row_index, row in enumerate(rows):
        for claim_index, claim in enumerate(row["extracted_claims"]):
            pairs.append((str(row["id"]), str(row["evidence"]), claim["text"]))
            locations.append((row_index, claim_index))
    scores = nli.score(pairs, batch_size)
    for (row_index, claim_index), score in zip(locations, scores, strict=True):
        claim = rows[row_index]["extracted_claims"][claim_index]
        claim["nli_status"] = NLI_STATUS[score.predicted_label]
        claim["nli_scores"] = {
            "entailment": score.entailment,
            "neutral": score.neutral,
            "contradiction": score.contradiction,
        }
    mark_semantic_duplicates(rows, nli, batch_size)
    payload: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        **collect_git_state().to_json(),
        "dataset": str(dataset),
        "dataset_sha256": sha256(dataset.read_bytes()).hexdigest(),
        "llm_model": settings.llm_default_model,
        "llm_temperature": 0.2,
        "prompt_version": PROMPT_VERSION,
        "nli_model": DEFAULT_NLI_MODEL,
        "run_duration_ms": round((perf_counter() - started) * 1000, 4),
        "metrics": compute_extractor_metrics(rows),
        "cases": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "claim_extractor_eval.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an LLM DraftClaim extractor.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    result = asyncio.run(run_extractor_eval(args.dataset, args.output_dir, args.batch_size))
    print(result["metrics"])


if __name__ == "__main__":
    main()
