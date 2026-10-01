"""Offline value/relation presence diagnostics for supplemental retrieval candidates."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
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
from evals.retrieval_trigger_features import structural_features

_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?%?")
_NUMERIC_DEMAND = re.compile(
    r"多少|几(?:次|回|成|天|名|个|轮|毫秒|秒|分钟|小时|人月|条)|"
    r"哪个(?:上限|实际值|数值)|区间|范围|阈值|精确值"
)
_UNIT_PATTERNS = {
    "次": ("次", "回", "轮"),
    "天": ("天", "自然日"),
    "名": ("名", "人", "用户"),
    "毫秒": ("毫秒", "ms"),
    "%": ("%", "百分比", "百分点"),
    "成": ("成", "一半", "0.5", "50%"),
}
_RELATIONS = (
    "处理",
    "查询",
    "保留",
    "经过",
    "实验",
    "降低",
    "支持",
    "限制",
    "复核",
    "完成",
    "更新",
    "触发",
    "恢复",
    "保证",
    "允许",
    "影响",
    "计算",
    "融合",
    "验证",
)


def evidence_presence(question: str, content: str) -> dict[str, Any]:
    normalized = content.casefold().replace("learning_rate", "学习率").replace(
        "confidence_weight", "权重"
    )
    explicit_values = tuple(dict.fromkeys(_NUMBER.findall(question)))
    value_required = bool(explicit_values or _NUMERIC_DEMAND.search(question))
    requested_units = tuple(
        unit
        for unit, aliases in _UNIT_PATTERNS.items()
        if any(alias in question for alias in aliases)
    )
    explicit_covered = tuple(value for value in explicit_values if value in normalized)
    number_present = bool(_NUMBER.search(normalized))
    unit_covered = tuple(
        unit
        for unit in requested_units
        if any(alias.casefold() in normalized for alias in _UNIT_PATTERNS[unit])
    )
    relations = tuple(relation for relation in _RELATIONS if relation in question)
    covered_relations = tuple(relation for relation in relations if relation in normalized)
    value_present = (
        len(explicit_covered) == len(explicit_values)
        and (not value_required or number_present)
        and len(unit_covered) == len(requested_units)
    )
    relation_present = bool(covered_relations) if relations else False
    return {
        "value_required": value_required,
        "explicit_values": list(explicit_values),
        "explicit_values_covered": list(explicit_covered),
        "requested_units": list(requested_units),
        "requested_units_covered": list(unit_covered),
        "number_present": number_present,
        "value_present": value_present,
        "relations": list(relations),
        "relations_covered": list(covered_relations),
        "relation_present": relation_present,
        "value_or_relation_present": value_present if value_required else relation_present,
    }


async def build_presence_report(report_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    chunk_ids = {
        UUID(item["chunk_id"])
        for case in report["cases"]
        for item in case.get("supplemental_chunks") or []
    }
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
    finally:
        await engine.dispose()
    contents = {str(chunk_id): content for chunk_id, content in rows}
    cases = []
    for case in report["cases"]:
        candidates = []
        for item in case.get("supplemental_chunks") or []:
            chunk_id = str(item["chunk_id"])
            presence = evidence_presence(case["question"], contents.get(chunk_id, ""))
            candidates.append(
                {
                    "rank": item["rank"],
                    "chunk_id": chunk_id,
                    "matched_ground_truth": bool(item.get("matched_ground_truth")),
                    "presence": presence,
                }
            )
        cases.append(
            {
                "id": case["id"],
                "answerability": case["answerability"],
                "primary_hit": case.get("first_relevant_rank") is not None,
                "structural_features": structural_features(case),
                "supplemental_candidates": candidates,
            }
        )
    return {
        "source_report": str(report_path),
        "dataset": report["dataset"],
        "dataset_sha256": report["metadata"]["dataset_sha256"],
        "case_count": len(cases),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for report_path in args.reports:
        payload = asyncio.run(build_presence_report(report_path))
        output = args.output_dir / f"{report_path.parent.name}.json"
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {output}")


if __name__ == "__main__":
    main()
