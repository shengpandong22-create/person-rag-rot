"""Typed eval-only relation/value binding candidate (V3)."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from agent_mentor.config import get_settings
from agent_mentor.infrastructure.database.models import KnowledgeChunkModel
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)


class RelationRole(StrEnum):
    EXACT = "exact"
    RANGE = "range"
    UPPER_BOUND = "upper_bound"
    LOWER_BOUND = "lower_bound"
    SEQUENCE = "sequence"


class ValueSemantic(StrEnum):
    GENERIC = "generic"
    RATIO = "ratio"
    SCORE = "score"
    COUNT = "count"
    DURATION = "duration"
    RATE = "rate"
    ACCURACY = "accuracy"
    COVERAGE = "coverage"
    WEIGHT = "weight"


class ClaimModality(StrEnum):
    FACT = "fact"
    GUARANTEE = "guarantee"


@dataclass(frozen=True, slots=True)
class TypedRelationDemand:
    relation: str
    role: RelationRole
    value_semantic: ValueSemantic
    canonical_unit: str | None
    preferred_span_type: str
    modality: ClaimModality
    relation_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceProvenance:
    chunk_id: str
    document_logical_name: str
    heading_path: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TypedBoundValue:
    provenance: EvidenceProvenance
    values: tuple[str, ...]
    canonical_unit: str | None
    role: RelationRole
    value_semantic: ValueSemantic
    span_type: str
    span: str
    relation_terms: tuple[str, ...]


_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?%?(?:/\d+(?:\.\d+)?)?")
_TERM = re.compile(r"[A-Za-z][A-Za-z0-9_+-]*|[\u4e00-\u9fff]{2,8}")
_STOP = {
    "对应",
    "关系",
    "数值",
    "默认值",
    "分别",
    "变化",
    "取值",
    "多少",
    "是否",
    "所需",
}


def normalize_demand(
    relation: str, canonical_unit: str | None, preferred_span_type: str
) -> TypedRelationDemand:
    return TypedRelationDemand(
        relation=relation,
        role=_relation_role(relation),
        value_semantic=_value_semantic(relation, canonical_unit),
        canonical_unit=canonical_unit,
        preferred_span_type=preferred_span_type,
        modality=(
            ClaimModality.GUARANTEE
            if any(marker in relation for marker in ("保证", "承诺", "确保"))
            else ClaimModality.FACT
        ),
        relation_terms=_terms(relation),
    )


def bind_typed_relation_value(
    demand: TypedRelationDemand,
    *,
    provenance: EvidenceProvenance,
    content: str,
) -> tuple[TypedBoundValue, ...]:
    matches: list[TypedBoundValue] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for span_type, span in _typed_spans(content, demand.preferred_span_type):
        values = tuple(dict.fromkeys(_NUMBER.findall(span)))
        if not values or not _unit_matches(span, demand.canonical_unit):
            continue
        if not _role_matches(demand.role, span, values):
            continue
        if not _semantic_matches(demand, span):
            continue
        searchable = _normalized_search_text(span)
        covered = tuple(term for term in demand.relation_terms if term.casefold() in searchable)
        minimum = 1 if len(demand.relation_terms) <= 2 else 2
        if len(covered) < minimum:
            continue
        key = (span, values)
        if key in seen:
            continue
        seen.add(key)
        matches.append(
            TypedBoundValue(
                provenance=provenance,
                values=values,
                canonical_unit=demand.canonical_unit,
                role=demand.role,
                value_semantic=demand.value_semantic,
                span_type=span_type,
                span=span,
                relation_terms=covered,
            )
        )
    return tuple(matches)


def _relation_role(relation: str) -> RelationRole:
    if any(marker in relation for marker in ("上限", "上界", "最多", "至多")):
        return RelationRole.UPPER_BOUND
    if any(marker in relation for marker in ("下限", "下界", "至少", "最低")):
        return RelationRole.LOWER_BOUND
    if any(marker in relation for marker in ("范围", "边界", "区间")):
        return RelationRole.RANGE
    if any(marker in relation for marker in ("两次", "先后", "变化")):
        return RelationRole.SEQUENCE
    return RelationRole.EXACT


def _value_semantic(relation: str, unit: str | None) -> ValueSemantic:
    if "准确率" in relation:
        return ValueSemantic.ACCURACY
    if "覆盖" in relation and any(marker in relation for marker in ("率", "比例")):
        return ValueSemantic.COVERAGE
    if "权重" in relation:
        return ValueSemantic.WEIGHT
    if "掌握度" in relation:
        return ValueSemantic.RATIO
    if any(marker in relation for marker in ("分数", "总分", "得分")) or unit == "分":
        return ValueSemantic.SCORE
    if unit in {"天", "小时", "分钟", "秒", "毫秒"}:
        return ValueSemantic.DURATION
    if unit in {"QPS", "次/秒"}:
        return ValueSemantic.RATE
    if unit in {"次", "个", "条", "页", "位"} or any(
        marker in relation for marker in ("数量", "次数", "位数")
    ):
        return ValueSemantic.COUNT
    if unit in {"比例", "百分点"}:
        return ValueSemantic.RATIO
    return ValueSemantic.GENERIC


def _typed_spans(content: str, preferred: str) -> tuple[tuple[str, str], ...]:
    lines = tuple(line.strip() for line in content.splitlines() if line.strip())
    spans: list[tuple[str, str]] = []
    for line in lines:
        if "|" in line and line.count("|") >= 2:
            spans.append(("table_row", line))
        if "=" in line or "return " in line:
            spans.append(("code_statement", line))
    for width in (2, 3):
        spans.extend(
            ("bounded_record", " ".join(lines[index : index + width]))
            for index in range(max(0, len(lines) - width + 1))
        )
    spans.extend(
        ("sentence_span", item.strip())
        for item in re.split(r"[。！？!?；;\n]", content)
        if item.strip()
    )
    if preferred == "bounded_multi_span":
        spans.extend(
            ("bounded_multi_span", " ".join(lines[index : index + 3]))
            for index in range(max(0, len(lines) - 2))
        )
    return tuple(spans)


def _role_matches(role: RelationRole, span: str, values: tuple[str, ...]) -> bool:
    if role is RelationRole.UPPER_BOUND:
        return bool(re.search(r"(?:\bmin\s*\(|<=|≤|至多|不超过|上限|最多)", span, re.I))
    if role is RelationRole.LOWER_BOUND:
        return bool(re.search(r"(?:\bmax\s*\(|>=|≥|至少|不低于|下限|最低)", span, re.I))
    if role is RelationRole.RANGE:
        return len(values) >= 2 and bool(
            re.search(r"(?:\d\s*[-~～—至到]\s*\d|[\[(（]\s*-?\d[^\])）]{0,40}[\])）])", span)
        )
    if role is RelationRole.SEQUENCE:
        return len(values) >= 2
    return True


def _semantic_matches(demand: TypedRelationDemand, span: str) -> bool:
    lowered = span.casefold()
    if demand.modality is ClaimModality.GUARANTEE and not any(
        marker in lowered for marker in ("保证", "承诺", "确保", "guarantee")
    ):
        return False
    markers = {
        ValueSemantic.ACCURACY: ("准确率", "accuracy"),
        ValueSemantic.COVERAGE: ("覆盖率", "覆盖比例", "coverage"),
        ValueSemantic.WEIGHT: ("权重", "weight"),
        ValueSemantic.SCORE: ("分数", "总分", "得分", "score", "correctness"),
        ValueSemantic.DURATION: ("天", "小时", "分钟", "秒", "duration"),
        ValueSemantic.RATE: ("qps", "每秒", "次/秒"),
    }.get(demand.value_semantic)
    return markers is None or any(marker in lowered for marker in markers)


def _normalized_search_text(span: str) -> str:
    original = span.casefold()
    normalized = f"{original} {original.replace('_', ' ')}"
    aliases = {
        "low confidence": " 低置信 ",
        "confidence weight": " 画像更新权重 ",
        "mini fingerprint": " mini指纹 ",
    }
    for source, target in aliases.items():
        if source in normalized:
            normalized += target
    if re.search(r"\bmin\s*\(", normalized):
        normalized += " 上限 "
    if re.search(r"\bmax\s*\(", normalized):
        normalized += " 下限 "
    return normalized


def _terms(text: str) -> tuple[str, ...]:
    for marker in (
        "单项",
        "分数",
        "总分",
        "范围",
        "边界",
        "上限",
        "下限",
        "准确率",
        "覆盖比例",
        "保证",
    ):
        text = text.replace(marker, " ")
    terms: list[str] = []
    for token in _TERM.findall(text):
        if token in _STOP:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            terms.extend(token[index : index + 2] for index in range(len(token) - 1))
        else:
            terms.append(token.casefold())
    return tuple(dict.fromkeys(terms))


def _unit_matches(span: str, unit: str | None) -> bool:
    if unit is None or unit == "比例":
        return True
    aliases = {
        "分": ("分", "总分", "score", "correctness"),
        "次": ("次", "streak", "verification"),
        "个": ("个", "数量"),
        "条": ("条", "top"),
        "位": ("位", "prefix"),
        "天": ("天", "自然日"),
        "次/秒": ("次", "每秒", "qps"),
        "百分点": ("百分点", "%"),
        "QPS": ("qps", "每秒", "次/秒"),
    }.get(unit, (unit,))
    lowered = span.casefold()
    return any(alias.casefold() in lowered for alias in aliases)


async def evaluate_v3(dataset: Path, retrieval_report: Path) -> dict[str, Any]:
    labels = {row["id"]: row for row in _load_jsonl(dataset)}
    report = json.loads(retrieval_report.read_text(encoding="utf-8"))
    ids = {
        UUID(item["chunk_id"])
        for case in report["cases"]
        for item in [*(case.get("top_chunks") or []), *(case.get("supplemental_chunks") or [])]
    }
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            rows = (
                await session.execute(
                    select(KnowledgeChunkModel.id, KnowledgeChunkModel.content).where(
                        KnowledgeChunkModel.id.in_(ids)
                    )
                )
            ).all()
    finally:
        await engine.dispose()
    contents = {str(chunk_id): content for chunk_id, content in rows}
    results: list[dict[str, Any]] = []
    for case in report["cases"]:
        label = labels[case["id"]]
        demand = normalize_demand(
            label["requested_relation"],
            label.get("canonical_unit"),
            label["evidence_span_type"],
        )
        candidates = [*(case.get("top_chunks") or []), *(case.get("supplemental_chunks") or [])]
        bindings = [
            binding
            for item in candidates
            for binding in bind_typed_relation_value(
                demand,
                provenance=EvidenceProvenance(
                    str(item["chunk_id"]),
                    str(item.get("document_logical_name") or item.get("document_title") or ""),
                    tuple(str(part) for part in item.get("heading_path") or ()),
                ),
                content=contents.get(str(item["chunk_id"]), ""),
            )
        ]
        ground_truth_ids = {
            str(item["chunk_id"]) for item in candidates if item.get("matched_ground_truth")
        }
        expected_values = set(label["expected_values"])
        correct = [
            item
            for item in bindings
            if item.provenance.chunk_id in ground_truth_ids
            and expected_values.issubset(item.values)
        ]
        results.append(
            {
                "id": case["id"],
                "span_type": label["evidence_span_type"],
                "expected_binding": bool(label["expected_binding"]),
                "predicted_binding": bool(bindings),
                "correct_labeled_binding": bool(correct),
                "demand": asdict(demand),
                "bindings": [asdict(item) for item in bindings],
            }
        )
    positives = [item for item in results if item["expected_binding"]]
    negatives = [item for item in results if not item["expected_binding"]]
    span_types = sorted({str(item["span_type"]) for item in positives})
    return {
        "candidate": "relation-value-binding-v3",
        "dataset": str(dataset),
        "retrieval_report": str(retrieval_report),
        "metrics": {
            "provenance_aware_binding_accuracy": round(
                (
                    sum(item["correct_labeled_binding"] for item in positives)
                    + sum(not item["predicted_binding"] for item in negatives)
                )
                / len(results),
                4,
            ),
            "labeled_binding_recall": round(
                sum(item["correct_labeled_binding"] for item in positives) / len(positives), 4
            ),
            "negative_rejection": round(
                sum(not item["predicted_binding"] for item in negatives) / len(negatives), 4
            ),
            "span_success_counts": {
                span_type: sum(
                    item["correct_labeled_binding"]
                    for item in positives
                    if item["span_type"] == span_type
                )
                for span_type in span_types
            },
        },
        "cases": results,
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--retrieval-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = asyncio.run(evaluate_v3(args.dataset, args.retrieval_report))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
