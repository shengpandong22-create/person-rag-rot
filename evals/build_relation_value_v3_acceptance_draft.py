"""Materialize the human-authored V3 acceptance draft without running V3."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from agent_mentor.config import get_settings
from agent_mentor.infrastructure.database.models import (
    KnowledgeChunkModel,
    SourceDocumentModel,
)
from agent_mentor.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)
from evals.relation_value_v3_acceptance_audit import normalized_span_hash


def demand(
    relation: str,
    role: str,
    semantic: str,
    unit: str | None,
    values: list[str],
    terms: list[str],
    *,
    alternatives: list[list[str]] | None = None,
) -> dict[str, Any]:
    return {
        "requested_relation": relation,
        "relation_role": role,
        "value_semantic": semantic,
        "canonical_unit": unit,
        "accepted_value_sets": [values, *(alternatives or [])],
        "required_relation_terms": terms,
        "modality": "fact",
    }


POSITIVES: list[dict[str, Any]] = [
    {
        "id": "rva3-001",
        "q": "项目总结明确支持在多大内存的普通开发机上运行？",
        "doc": "第 7 课：工程化专题 + 面试实战",
        "lines": [193, 193],
        "needle": "16GB 本地约束",
        "span": "sentence_span",
        "d": [demand("普通开发机运行内存", "exact", "generic", "GB", ["16"], ["内存", "运行"])],
    },
    {
        "id": "rva3-002",
        "q": "文档中间插入内容后，示例旧块的索引怎样变化？新索引又是多少？",
        "doc": "第 2 课：知识入库链路——文档如何变成可检索证据",
        "lines": [317, 318],
        "needle": "旧的第3块变成了第4块",
        "span": "sentence_span",
        "d": [
            demand(
                "插入内容前后旧块索引变化", "sequence", "count", None, ["3", "4"], ["旧块", "索引"]
            ),
            demand("插入内容后的旧块索引", "exact", "count", None, ["4"], ["插入", "索引"]),
        ],
    },
    {
        "id": "rva3-003",
        "q": "示例四个维度 4、3、2、4 相加后，应用层应得到多少总分？",
        "doc": "第 5 课：可信评分与报告",
        "lines": [59, 59],
        "needle": "4+3+2+4=13",
        "span": "sentence_span",
        "d": [
            demand(
                "四维示例的应用层计算结果",
                "derived_value",
                "score",
                "分",
                ["13"],
                ["四维", "应用层"],
            )
        ],
    },
    {
        "id": "rva3-004",
        "q": "Reviewer 复核后要进入 FINAL，分差必须小于多少？",
        "doc": "第 5 课：可信评分与报告",
        "lines": [84, 84],
        "needle": "分差<5",
        "span": "sentence_span",
        "d": [
            demand(
                "Reviewer确认FINAL的分差上界",
                "upper_bound",
                "score",
                "分",
                ["5"],
                ["Reviewer", "分差", "FINAL"],
            )
        ],
    },
    {
        "id": "rva3-005",
        "q": "四个评分维度的最大差距达到多少时会触发复核？",
        "doc": "第 5 课：可信评分与报告",
        "lines": [79, 79],
        "needle": "四维分差 ≥ 4",
        "span": "sentence_span",
        "d": [
            demand(
                "维度冲突触发复核的分差下界",
                "lower_bound",
                "score",
                "分",
                ["4"],
                ["维度", "分差", "复核"],
            )
        ],
    },
    {
        "id": "rva3-006",
        "q": "画像展示示例中，RAG 掌握度从多少变化到多少？最终展示值是多少？",
        "doc": "第 6 课：两层画像与复习闭环",
        "lines": [75, 75],
        "needle": "RAG 掌握度从 0.40",
        "span": "sentence_span",
        "tags": ["unit_alias_or_conversion"],
        "d": [
            demand(
                "画像展示中的RAG掌握度变化",
                "sequence",
                "ratio",
                "比例",
                ["0.40", "0.47"],
                ["RAG", "掌握度"],
                alternatives=[["40%", "47%"]],
            ),
            demand(
                "画像展示中的RAG最终掌握度",
                "exact",
                "ratio",
                "比例",
                ["0.47"],
                ["RAG", "最终掌握度"],
                alternatives=[["47%"]],
            ),
        ],
    },
    {
        "id": "rva3-007",
        "q": "completeness 维度的最低分和最高分各是多少？它的最高分是多少？",
        "doc": "第 5 课：可信评分与报告",
        "lines": [34, 34],
        "needle": "completeness",
        "span": "table_row",
        "tags": ["unit_alias_or_conversion"],
        "d": [
            demand(
                "completeness单项分数范围",
                "range",
                "score",
                "分",
                ["0", "5"],
                ["completeness", "分数"],
            ),
            demand(
                "completeness单项最高分",
                "upper_bound",
                "score",
                "分",
                ["5"],
                ["completeness", "最高分"],
            ),
        ],
    },
    {
        "id": "rva3-008",
        "q": "reasoning 维度允许的分数范围是多少？",
        "doc": "第 5 课：可信评分与报告",
        "lines": [35, 35],
        "needle": "reasoning",
        "span": "table_row",
        "tags": ["unit_alias_or_conversion"],
        "d": [
            demand(
                "reasoning单项分数范围", "range", "score", "分", ["0", "5"], ["reasoning", "分数"]
            )
        ],
    },
    {
        "id": "rva3-009",
        "q": "communication 维度从最低到最高可取多少分？",
        "doc": "第 5 课：可信评分与报告",
        "lines": [36, 36],
        "needle": "communication",
        "span": "table_row",
        "tags": ["unit_alias_or_conversion"],
        "d": [
            demand(
                "communication单项分数范围",
                "range",
                "score",
                "分",
                ["0", "5"],
                ["communication", "分数"],
            )
        ],
    },
    {
        "id": "rva3-010",
        "q": "disputed 或 review_pending 状态的画像更新权重是多少？",
        "doc": "第 6 课：两层画像与复习闭环",
        "lines": [111, 111],
        "needle": "disputed / review_pending",
        "span": "table_row",
        "d": [
            demand(
                "争议或待复核评分的画像更新权重",
                "exact",
                "weight",
                "比例",
                ["0"],
                ["disputed", "review_pending", "权重"],
            )
        ],
    },
    {
        "id": "rva3-011",
        "q": "高置信 FINAL 在画像更新表中使用什么完整权重？",
        "doc": "第 6 课：两层画像与复习闭环",
        "lines": [113, 113],
        "needle": "confidence ≥ 0.70",
        "span": "table_row",
        "d": [
            demand(
                "高置信FINAL的完整更新权重",
                "exact",
                "weight",
                "比例",
                ["1.0"],
                ["FINAL", "完整权重"],
            )
        ],
    },
    {
        "id": "rva3-012",
        "q": "RRF 示例里 A 在向量路和全文路分别排第几？向量路名次是多少？",
        "doc": "第 3 课：混合检索与可信 RAG 回答",
        "lines": [68, 68],
        "needle": "A（RRF段落）",
        "span": "table_row",
        "d": [
            demand(
                "A在向量与全文两路的排名",
                "sequence",
                "count",
                "名",
                ["1", "3"],
                ["A", "向量", "全文"],
            ),
            demand("A在向量召回中的排名", "exact", "count", "名", ["1"], ["A", "向量排名"]),
        ],
    },
    {
        "id": "rva3-013",
        "q": "启动面试时创建首题所传入的 sequence 值是多少？",
        "doc": "第 4 课：可恢复模拟面试工作流",
        "lines": [57, 57],
        "needle": "sequence=1",
        "span": "code_statement",
        "d": [
            demand(
                "启动面试创建首题的sequence", "exact", "count", None, ["1"], ["首题", "sequence"]
            )
        ],
    },
    {
        "id": "rva3-014",
        "q": "掌握度更新结果会保留到小数点后多少位？",
        "doc": "第 6 课：两层画像与复习闭环",
        "lines": [127, 130],
        "needle": "return round",
        "span": "code_statement",
        "d": [
            demand("掌握度更新的舍入小数位数", "exact", "count", "位", ["4"], ["掌握度", "round"])
        ],
    },
    {
        "id": "rva3-015",
        "q": "六层架构图中的 FastAPI Router 一共有多少个路由？",
        "doc": "第 1 课：项目全景与架构地图",
        "lines": [29, 33],
        "needle": "FastAPI Router (7个路由)",
        "span": "code_statement",
        "d": [
            demand(
                "FastAPI Router路由数量",
                "exact",
                "count",
                "个",
                ["7"],
                ["FastAPI Router", "路由数量"],
            )
        ],
    },
    {
        "id": "rva3-016",
        "q": "RRF 遍历排名时 rank 的起始下界是多少？",
        "doc": "第 3 课：混合检索与可信 RAG 回答",
        "lines": [52, 56],
        "needle": "enumerate(ranked, start=1)",
        "span": "code_statement",
        "d": [
            demand(
                "RRF遍历rank的起始下界",
                "lower_bound",
                "count",
                None,
                ["1"],
                ["RRF", "rank", "start"],
            )
        ],
    },
    {
        "id": "rva3-017",
        "q": "词汇证据函数建立上下文词集合时最多查看前几个候选？",
        "doc": "第 3 课：混合检索与可信 RAG 回答",
        "lines": [161, 168],
        "needle": "candidates[:3]",
        "span": "code_statement",
        "d": [
            demand(
                "词汇证据上下文使用的候选数上限",
                "upper_bound",
                "count",
                "个",
                ["3"],
                ["词汇证据", "候选", "上限"],
            )
        ],
    },
    {
        "id": "rva3-018",
        "q": "示例中引用版本从 v3 演进到 v4 的先后序列是什么？最终版本是多少？",
        "doc": "第 2 课：知识入库链路——文档如何变成可检索证据",
        "lines": [341, 345],
        "needle": "version=v3",
        "span": "code_statement",
        "d": [
            demand(
                "示例引用版本的演进序列", "sequence", "count", None, ["3", "4"], ["引用", "版本"]
            ),
            demand("示例演进后的新版本", "exact", "count", None, ["4"], ["演进", "新版本"]),
        ],
    },
    {
        "id": "rva3-019",
        "q": "RRF 示例中 D 的两个倒数排名贡献相加后结果是多少？",
        "doc": "第 3 课：混合检索与可信 RAG 回答",
        "lines": [78, 78],
        "needle": "D: 1/(60+3)",
        "span": "bounded_multi_span",
        "d": [
            demand(
                "D的RRF两路贡献之和",
                "derived_value",
                "generic",
                None,
                ["0.0320"],
                ["D", "RRF", "贡献"],
            )
        ],
    },
    {
        "id": "rva3-020",
        "q": "只有全文路召回的 C，其 RRF 计算结果是多少？",
        "doc": "第 3 课：混合检索与可信 RAG 回答",
        "lines": [79, 79],
        "needle": "C: 1/(60+1)",
        "span": "bounded_multi_span",
        "d": [
            demand(
                "仅全文召回C的RRF计算结果",
                "derived_value",
                "generic",
                None,
                ["0.0164"],
                ["C", "全文", "RRF"],
            )
        ],
    },
    {
        "id": "rva3-021",
        "q": "只有向量路召回的 B，其 RRF 计算结果是多少？",
        "doc": "第 3 课：混合检索与可信 RAG 回答",
        "lines": [80, 80],
        "needle": "B: 1/(60+2)",
        "span": "bounded_multi_span",
        "d": [
            demand(
                "仅向量召回B的RRF计算结果",
                "derived_value",
                "generic",
                None,
                ["0.0161"],
                ["B", "向量", "RRF"],
            )
        ],
    },
    {
        "id": "rva3-022",
        "q": "难度因子从 easy 到 hard 的取值范围是什么？三个档位依次是多少？",
        "doc": "第 6 课：两层画像与复习闭环",
        "lines": [121, 125],
        "needle": '"easy": 0.85',
        "span": "bounded_multi_span",
        "d": [
            demand(
                "难度因子的取值范围", "range", "generic", None, ["0.85", "1.15"], ["难度", "因子"]
            ),
            demand(
                "easy到hard的难度因子序列",
                "sequence",
                "generic",
                None,
                ["0.85", "1.0", "1.15"],
                ["easy", "medium", "hard"],
            ),
        ],
    },
    {
        "id": "rva3-023",
        "q": "可信高分累加时 verification streak 的封顶值是多少？",
        "doc": "第 6 课：两层画像与复习闭环",
        "lines": [199, 200],
        "needle": "next_streak = min(2",
        "span": "bounded_multi_span",
        "d": [
            demand(
                "verification streak累加上限",
                "upper_bound",
                "count",
                "次",
                ["2"],
                ["verification streak", "上限"],
            )
        ],
    },
    {
        "id": "rva3-024",
        "q": "英文特征正则要求单词长度至少为多少个字符？",
        "doc": "第 2 课：知识入库链路——文档如何变成可检索证据",
        "lines": [144, 146],
        "needle": "[a-z0-9_]{2,}",
        "span": "bounded_multi_span",
        "d": [
            demand(
                "英文特征单词长度下限",
                "lower_bound",
                "count",
                "个字符",
                ["2"],
                ["英文特征", "单词长度"],
            )
        ],
    },
]

NEGATIVES: list[dict[str, Any]] = [
    {
        "id": "rva3-025",
        "base": "rva3-004",
        "q": "Reviewer 分差小于 5 是否保证评分绝对正确？",
        "relation": "Reviewer评分绝对正确保证",
        "role": "exact",
        "semantic": "accuracy",
        "unit": "比例",
        "type": "relation_role",
    },
    {
        "id": "rva3-026",
        "base": "rva3-023",
        "q": "streak 上限 2 是否表示必须恰好两次才能写入任何进度？",
        "relation": "任何进度写入所需精确次数",
        "role": "exact",
        "semantic": "count",
        "unit": "次",
        "type": "relation_role",
    },
    {
        "id": "rva3-027",
        "base": "rva3-001",
        "q": "16GB 是否是系统的并发用户数量？",
        "relation": "系统并发用户数量",
        "role": "exact",
        "semantic": "count",
        "unit": "位",
        "type": "value_semantic",
    },
    {
        "id": "rva3-028",
        "base": "rva3-003",
        "q": "示例里的 13 是否是评分接口的 P95 延迟？",
        "relation": "评分接口P95延迟",
        "role": "exact",
        "semantic": "duration",
        "unit": "毫秒",
        "type": "value_semantic",
    },
    {
        "id": "rva3-029",
        "base": "rva3-007",
        "q": "completeness 行能否证明 correctness 的最高分是 5？",
        "relation": "correctness单项最高分",
        "role": "upper_bound",
        "semantic": "score",
        "unit": "分",
        "type": "subject_predicate",
    },
    {
        "id": "rva3-030",
        "base": "rva3-010",
        "q": "disputed 行是否说明高置信 FINAL 的更新权重为 0？",
        "relation": "高置信FINAL更新权重",
        "role": "exact",
        "semantic": "weight",
        "unit": "比例",
        "type": "subject_predicate",
    },
    {
        "id": "rva3-031",
        "base": "rva3-008",
        "q": "reasoning 的 0 到 5 是否表示保留 0 到 5 天？",
        "relation": "reasoning记录保留期限",
        "role": "range",
        "semantic": "duration",
        "unit": "天",
        "type": "unit_binding",
    },
    {
        "id": "rva3-032",
        "base": "rva3-001",
        "q": "16GB 是否等于一次请求最长 16 毫秒？",
        "relation": "单次请求时长上限",
        "role": "upper_bound",
        "semantic": "duration",
        "unit": "毫秒",
        "type": "unit_binding",
    },
    {
        "id": "rva3-033",
        "base": "rva3-013",
        "q": "sequence=1 能否证明一场面试最多只有一道题？",
        "relation": "单场面试题目数量上限",
        "role": "upper_bound",
        "semantic": "count",
        "unit": "道",
        "type": "provenance_structure",
    },
    {
        "id": "rva3-034",
        "base": "rva3-018",
        "q": "version=v4 能否证明知识库只允许四个文档？",
        "relation": "知识库文档数量上限",
        "role": "upper_bound",
        "semantic": "count",
        "unit": "个",
        "type": "provenance_structure",
    },
    {
        "id": "rva3-035",
        "base": "rva3-017",
        "q": "词汇证据代码是否给出了线上 P95 为 3 毫秒？",
        "relation": "线上词汇证据P95延迟",
        "role": "exact",
        "semantic": "duration",
        "unit": "毫秒",
        "type": "missing_value_false_premise",
    },
    {
        "id": "rva3-036",
        "base": "rva3-022",
        "q": "难度因子 1.15 是否是生产服务实测 QPS？",
        "relation": "生产服务实测QPS",
        "role": "exact",
        "semantic": "rate",
        "unit": "QPS",
        "type": "missing_value_false_premise",
    },
]


def _span(document: str, start: int, end: int) -> tuple[str, str]:
    path = Path("docs/learning") / f"{document}.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[start - 1 : end]), hashlib.sha256(path.read_bytes()).hexdigest()


async def build(knowledge_base_id: UUID) -> list[dict[str, Any]]:
    engine = create_database_engine(get_settings().database_url)
    factory = create_session_factory(engine)
    async with factory() as session:
        result = await session.execute(
            select(KnowledgeChunkModel, SourceDocumentModel)
            .join(SourceDocumentModel, KnowledgeChunkModel.document_id == SourceDocumentModel.id)
            .where(SourceDocumentModel.knowledge_base_id == knowledge_base_id)
            .where(SourceDocumentModel.is_active.is_(True))
            .where(KnowledgeChunkModel.is_active.is_(True))
        )
        catalog = list(result.all())
    await engine.dispose()
    rows: list[dict[str, Any]] = []
    for spec in POSITIVES:
        matches = [
            (chunk, document)
            for chunk, document in catalog
            if document.logical_name == spec["doc"] and spec["needle"] in chunk.content
        ]
        if not matches:
            raise ValueError(f"{spec['id']}: no chunk found for {spec['needle']!r}")
        chunk, document = min(matches, key=lambda item: item[0].chunk_index)
        span_text, source_file_sha256 = _span(spec["doc"], *spec["lines"])
        evidence_id = "e1"
        demands = []
        for index, raw in enumerate(spec["d"], start=1):
            demands.append(
                {
                    "demand_id": f"d{index}",
                    **raw,
                    "expected_binding": True,
                    "evidence_ids": [evidence_id],
                    "rationale": "首轮人工标注：值、单位和关系均由所引证据直接支持。",
                }
            )
        pair_id = (
            f"pair-{int(spec['id'].split('-')[-1]):02d}"
            if int(spec["id"].split("-")[-1]) <= 12
            else None
        )
        row = {
            "id": spec["id"],
            "split": "acceptance",
            "label_origin": "human",
            "question": spec["q"],
            "answerability": "full",
            "confusion_type": None,
            "primary_relation_role": demands[0]["relation_role"],
            "primary_span_type": spec["span"],
            "pair_id": pair_id,
            "demands": demands,
            "evidence": [
                {
                    "evidence_id": evidence_id,
                    "chunk_id": str(chunk.id),
                    "document_logical_name": document.logical_name,
                    "heading_path": chunk.heading_path,
                    "span_type": spec["span"],
                    "span_text": span_text,
                    "span_sha256": normalized_span_hash(span_text),
                    "source_content_hash": document.content_hash,
                    "source_file_sha256": source_file_sha256,
                    "supports_demand_ids": [item["demand_id"] for item in demands],
                }
            ],
            "relevant_sources": [
                {
                    "document_logical_name": document.logical_name,
                    "heading_path": chunk.heading_path,
                    "required_answer_points": [demands[0]["rationale"]],
                }
            ],
            "negative_reason": None,
            "annotation": {
                "author": "author-pass-1",
                "reviewer": None,
                "review_state": "draft",
                "adjudication_note": None,
            },
            "tags": [
                "relation_value_v3_acceptance",
                "positive",
                spec["span"],
                *(spec.get("tags", [])),
            ],
        }
        rows.append(row)
    by_id = {row["id"]: row for row in rows}
    for offset, spec in enumerate(NEGATIVES, start=1):
        base = by_id[spec["base"]]
        evidence = json.loads(json.dumps(base["evidence"], ensure_ascii=False))
        evidence[0]["supports_demand_ids"] = []
        rows.append(
            {
                "id": spec["id"],
                "split": "acceptance",
                "label_origin": "human",
                "question": spec["q"],
                "answerability": "none",
                "confusion_type": spec["type"],
                "primary_relation_role": spec["role"],
                "primary_span_type": evidence[0]["span_type"],
                "pair_id": f"pair-{offset:02d}" if offset <= 8 else None,
                "demands": [
                    {
                        "demand_id": "d1",
                        "requested_relation": spec["relation"],
                        "relation_role": spec["role"],
                        "value_semantic": spec["semantic"],
                        "canonical_unit": spec["unit"],
                        "expected_binding": False,
                        "accepted_value_sets": [],
                        "evidence_ids": [],
                        "required_relation_terms": spec["relation"].split(),
                        "modality": "guarantee" if "保证" in spec["q"] else "fact",
                        "rationale": (
                            "首轮人工标注：证据中的数字属于不同关系、语义、单位或结构边界，"
                            "不能支持请求。"
                        ),
                    }
                ],
                "evidence": evidence,
                "relevant_sources": [],
                "negative_reason": "evidence_relation_value_mismatch",
                "annotation": {
                    "author": "author-pass-1",
                    "reviewer": None,
                    "review_state": "draft",
                    "adjudication_note": None,
                },
                "tags": ["relation_value_v3_acceptance", "hard_negative", spec["type"]],
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge-base-id", required=True, type=UUID)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rows = asyncio.run(build(args.knowledge_base_id))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "// First-pass human annotation draft. V3 has not been run.\n"
        + "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"rows": len(rows), "candidate_executed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
