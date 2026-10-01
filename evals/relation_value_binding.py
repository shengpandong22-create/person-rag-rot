"""Fixture-backed deterministic relation -> value/unit -> span evaluator."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import asdict, dataclass
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

_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?%?(?:/\d+(?:\.\d+)?)?")
_TERM = re.compile(r"[A-Za-z][A-Za-z0-9_+-]*|[\u4e00-\u9fff]{2,8}")
_STOP = {"对应", "关系", "数值", "默认值", "最长", "分别", "变化", "取值"}


@dataclass(frozen=True, slots=True)
class RelationValueDemand:
    relation: str
    canonical_unit: str | None
    span_type: str


@dataclass(frozen=True, slots=True)
class BoundValue:
    chunk_id: str
    values: tuple[str, ...]
    span: str
    span_type: str
    relation_terms: tuple[str, ...]


def bind_relation_value(
    demand: RelationValueDemand, *, chunk_id: str, content: str
) -> tuple[BoundValue, ...]:
    relation_terms = _terms(demand.relation)
    matches = []
    for span in _spans(content, demand.span_type):
        values = tuple(dict.fromkeys(_NUMBER.findall(span)))
        if not values or not _unit_matches(span, demand.canonical_unit):
            continue
        if not _relation_shape_matches(span, demand.relation, values):
            continue
        searchable_span = _normalized_search_text(span)
        covered = tuple(term for term in relation_terms if term.casefold() in searchable_span)
        minimum = 1 if len(relation_terms) <= 2 else 2
        if len(covered) < minimum:
            continue
        matches.append(BoundValue(chunk_id, values, span, demand.span_type, covered))
    return tuple(matches)


def _spans(content: str, span_type: str) -> tuple[str, ...]:
    lines = tuple(line.strip() for line in content.splitlines() if line.strip())
    if span_type == "table_row":
        table_rows = tuple(line for line in lines if line.startswith("|") and line.endswith("|"))
        if table_rows:
            return table_rows
        return tuple(
            " ".join(lines[index : index + 6])
            for index in range(len(lines))
            if any("=" in line for line in lines[index : index + 6])
        )
    if span_type == "code_statement":
        return tuple(line for line in lines if "=" in line or "return " in line)
    if span_type == "sentence_span":
        return tuple(
            item.strip()
            for item in re.split(r"[。！？!?；;\n]", content)
            if item.strip()
        )
    return tuple(" ".join(lines[index : index + 3]) for index in range(len(lines)))


def _normalized_search_text(span: str) -> str:
    original = span.casefold()
    normalized = f"{original} {original.replace('_', ' ')}"
    aliases = {
        "low confidence": " 低置信 ",
        "confidence weight": " 画像更新权重 ",
    }
    for source, target in aliases.items():
        if source in normalized:
            normalized += target
    if re.search(r"\bmin\s*\(", normalized):
        normalized += " 上限 "
    if re.search(r"\bmax\s*\(", normalized):
        normalized += " 下限 "
    return normalized


def _relation_shape_matches(span: str, relation: str, values: tuple[str, ...]) -> bool:
    if any(marker in relation for marker in ("上限", "上界")):
        return bool(re.search(r"(?:\bmin\s*\(|<=|至多|不超过|上限)", span, re.IGNORECASE))
    if any(marker in relation for marker in ("下限", "下界")):
        return bool(re.search(r"(?:\bmax\s*\(|>=|至少|不低于|下限)", span, re.IGNORECASE))
    if not any(marker in relation for marker in ("边界", "范围")):
        return True
    if len(values) < 2:
        return False
    return bool(
        re.search(r"(?:到|至|~|～|—|<=|>=)", span)
        or re.search(
            r"[\[(（]\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*[\])）]",
            span,
        )
    )


def _terms(text: str) -> tuple[str, ...]:
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
        "分": ("分", "总分"),
        "次": ("次", "streak"),
        "天": ("天", "自然日"),
        "次/秒": ("次", "每秒", "QPS"),
        "百分点": ("百分点", "%"),
        "QPS": ("QPS", "每秒", "次/秒"),
    }.get(unit, (unit,))
    return any(alias.casefold() in span.casefold() for alias in aliases)


async def evaluate(dataset: Path, retrieval_report: Path) -> dict[str, Any]:
    labels = {
        row["id"]: row
        for row in _load_jsonl(dataset)
    }
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
    results = []
    for case in report["cases"]:
        label = labels[case["id"]]
        demand = RelationValueDemand(
            label["requested_relation"], label.get("canonical_unit"), label["evidence_span_type"]
        )
        candidates = [*(case.get("top_chunks") or []), *(case.get("supplemental_chunks") or [])]
        bindings = [
            binding
            for item in candidates
            for binding in bind_relation_value(
                demand,
                chunk_id=str(item["chunk_id"]),
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
            if item.chunk_id in ground_truth_ids and expected_values.issubset(item.values)
        ]
        predicted = bool(bindings)
        expected = bool(label["expected_binding"])
        results.append(
            {
                "id": case["id"],
                "expected_binding": expected,
                "predicted_binding": predicted,
                "correct_labeled_binding": bool(correct),
                "bindings": [asdict(item) for item in bindings],
            }
        )
    positives = [item for item in results if item["expected_binding"]]
    negatives = [item for item in results if not item["expected_binding"]]
    return {
        "dataset": str(dataset),
        "retrieval_report": str(retrieval_report),
        "metrics": {
            "binding_accuracy": round(
                sum(
                    item["correct_labeled_binding"]
                    if item["expected_binding"]
                    else not item["predicted_binding"]
                    for item in results
                )
                / len(results),
                4,
            ),
            "positive_binding_detection": round(
                sum(item["predicted_binding"] for item in positives) / len(positives), 4
            ),
            "labeled_binding_recall": round(
                sum(item["correct_labeled_binding"] for item in positives) / len(positives), 4
            ),
            "negative_rejection": round(
                sum(not item["predicted_binding"] for item in negatives) / len(negatives), 4
            ),
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
    payload = asyncio.run(evaluate(args.dataset, args.retrieval_report))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
