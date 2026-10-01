"""Eval-only deterministic binding of numeric demands to local evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from agent_mentor.ports.knowledge_retriever import RetrievedChunk


class DemandBindingPolicy(StrEnum):
    NONE = "none"
    NUMERIC_LOCAL_V1 = "numeric-local-v1"
    TYPED_LOCAL_V2 = "typed-local-v2"


@dataclass(frozen=True, slots=True)
class DemandBindingAssessment:
    passed: bool
    explicit_numbers: tuple[str, ...]
    requested_units: tuple[str, ...]
    core_predicates: tuple[str, ...]
    matched_sentences: tuple[str, ...]
    matched_chunk_ids: tuple[str, ...]
    demand_types: tuple[str, ...]
    reasons: tuple[str, ...]


_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?")
_HAS_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?|[一二两三四五六七八九十百]+")
_DEMAND = re.compile(r"(?:多少|几)\s*(次|回|成|天|自然日|名|个|轮|毫秒|秒|分钟|小时|人月|条|%)?")
_SENTENCE = re.compile(r"[^。！？!?；;\n]+")
_RANGE_DEMAND = re.compile(r"区间|范围|从.+到|上下限")
_VALUE_QUERY = re.compile(r"哪个(?:上限|实际值|数值)|什么(?:值|数值)")
_RANGE_VALUE = re.compile(
    r"(?:\[|\()\s*-?\d+(?:\.\d+)?\s*[,，]\s*-?\d+(?:\.\d+)?\s*(?:\]|\))"
    r"|-?\d+(?:\.\d+)?\s*(?:-|～|~|到|至)\s*-?\d+(?:\.\d+)?"
)
_CORE_PREDICATES = (
    "处理",
    "查询",
    "保留",
    "经过",
    "实验",
    "降低",
    "错误率",
    "支持",
    "限制",
    "超时",
    "重试",
    "保存",
    "并发",
    "复核",
    "完成",
    "权重",
    "掌握度",
    "学习率",
)

_UNIT_CANONICAL = {"回": "次", "轮": "次", "自然日": "天"}


def assess_demand_binding(
    question: str,
    chunks: list[RetrievedChunk],
    policy: DemandBindingPolicy,
) -> DemandBindingAssessment:
    """Reject evidence where requested values are not locally bound to the demand."""
    explicit = tuple(dict.fromkeys(_NUMBER.findall(question)))
    implicit = tuple(match.group(1) or "" for match in _DEMAND.finditer(question))
    units = tuple(dict.fromkeys(_UNIT_CANONICAL.get(unit, unit) for unit in implicit if unit))
    predicates = _core_predicates(question, explicit, units)
    demand_types = tuple(
        kind
        for kind, present in (
            ("exact_value", bool(explicit)),
            ("unit_alias", any(unit in {"回", "成", "轮", "自然日"} for unit in implicit)),
            ("range_value", bool(_RANGE_DEMAND.search(question))),
            ("table_value", "表" in question),
            ("cross_sentence", "先" in question or len(explicit) >= 2),
            ("implicit_numeric", bool(implicit) or bool(_VALUE_QUERY.search(question))),
        )
        if present
    )
    if (policy is DemandBindingPolicy.NONE or not (explicit or implicit)) and (
        policy is not DemandBindingPolicy.TYPED_LOCAL_V2 or not demand_types
    ):
        return DemandBindingAssessment(True, explicit, units, predicates, (), (), demand_types, ())

    windows = _evidence_windows(chunks, typed=policy is DemandBindingPolicy.TYPED_LOCAL_V2)
    matched: list[str] = []
    matched_ids: list[str] = []
    reasons: list[str] = []
    for value in explicit:
        local = [(chunk_id, text) for chunk_id, text in windows if value in text]
        bound = [item for item in local if _predicate_matches(item[1], predicates)]
        if not bound:
            reasons.append(f"explicit_number_unbound:{value}")
        matched.extend(text for _, text in bound)
        matched_ids.extend(chunk_id for chunk_id, _ in bound)

    if policy is DemandBindingPolicy.TYPED_LOCAL_V2 and len(explicit) >= 2:
        local = [
            (chunk_id, text)
            for chunk_id, text in windows
            if all(value in text for value in explicit)
            and _predicate_matches(text, predicates)
        ]
        if not local:
            reasons.append("cross_sentence_values_unbound")
        else:
            matched.extend(text for _, text in local)
            matched_ids.extend(chunk_id for chunk_id, _ in local)

    for raw_unit in implicit:
        unit = _UNIT_CANONICAL.get(raw_unit, raw_unit)
        local = [
            (chunk_id, text)
            for chunk_id, text in windows
            if _HAS_NUMBER.search(text)
            and _unit_matches(text, unit)
            and _predicate_matches(text, predicates)
        ]
        if not local:
            reasons.append(f"implicit_numeric_demand_unbound:{unit or 'unspecified'}")
        matched.extend(text for _, text in local)
        matched_ids.extend(chunk_id for chunk_id, _ in local)

    if policy is DemandBindingPolicy.TYPED_LOCAL_V2 and _VALUE_QUERY.search(question):
        local = [
            (chunk_id, text)
            for chunk_id, text in windows
            if len(_NUMBER.findall(text)) >= 2 and _predicate_matches(text, predicates)
        ]
        if not local:
            reasons.append("implicit_value_pair_unbound")
        matched.extend(text for _, text in local)
        matched_ids.extend(chunk_id for chunk_id, _ in local)

    if policy is DemandBindingPolicy.TYPED_LOCAL_V2 and _RANGE_DEMAND.search(question):
        local = [
            (chunk_id, text)
            for chunk_id, text in windows
            if _RANGE_VALUE.search(text) and _predicate_matches(text, predicates)
        ]
        if not local:
            reasons.append("range_value_unbound")
        matched.extend(text for _, text in local)
        matched_ids.extend(chunk_id for chunk_id, _ in local)

    return DemandBindingAssessment(
        not reasons,
        explicit,
        units,
        predicates,
        tuple(dict.fromkeys(matched)),
        tuple(dict.fromkeys(matched_ids)),
        demand_types,
        tuple(reasons),
    )


def _core_predicates(
    question: str, explicit: tuple[str, ...], units: tuple[str, ...]
) -> tuple[str, ...]:
    del explicit, units
    return tuple(predicate for predicate in _CORE_PREDICATES if predicate in question)


def _predicate_matches(sentence: str, predicates: tuple[str, ...]) -> bool:
    normalized = sentence.replace("learning_rate", "学习率").replace(
        "confidence_weight", "权重"
    )
    return not predicates or all(predicate in normalized for predicate in predicates)


def _unit_matches(text: str, unit: str) -> bool:
    if not unit:
        return True
    aliases = {
        "次": ("次", "回", "轮"),
        "天": ("天", "自然日"),
    }.get(unit, (unit,))
    if any(alias in text for alias in aliases):
        return True
    if unit == "成":
        return any(0 <= float(value.rstrip("%")) <= 1 for value in _NUMBER.findall(text))
    return False


def _evidence_windows(
    chunks: list[RetrievedChunk], *, typed: bool
) -> list[tuple[str, str]]:
    windows: list[tuple[str, str]] = []
    for chunk in chunks:
        sentences = [item.strip() for item in _SENTENCE.findall(chunk.content) if item.strip()]
        for index, sentence in enumerate(sentences):
            windows.append((str(chunk.chunk_id), sentence))
            if typed and index + 1 < len(sentences):
                windows.append((str(chunk.chunk_id), f"{sentence} {sentences[index + 1]}"))
    return windows
