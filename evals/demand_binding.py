"""Eval-only deterministic binding of numeric demands to local evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from agent_mentor.ports.knowledge_retriever import RetrievedChunk


class DemandBindingPolicy(StrEnum):
    NONE = "none"
    NUMERIC_LOCAL_V1 = "numeric-local-v1"


@dataclass(frozen=True, slots=True)
class DemandBindingAssessment:
    passed: bool
    explicit_numbers: tuple[str, ...]
    requested_units: tuple[str, ...]
    core_predicates: tuple[str, ...]
    matched_sentences: tuple[str, ...]
    reasons: tuple[str, ...]


_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?")
_DEMAND = re.compile(r"多少\s*(次|天|名|个|轮|毫秒|秒|分钟|小时|人月|条|%)?")
_SENTENCE = re.compile(r"[^。！？!?；;\n]+")
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
)


def assess_demand_binding(
    question: str,
    chunks: list[RetrievedChunk],
    policy: DemandBindingPolicy,
) -> DemandBindingAssessment:
    """Reject evidence where requested values are not locally bound to the demand."""
    explicit = tuple(dict.fromkeys(_NUMBER.findall(question)))
    implicit = tuple(match.group(1) or "" for match in _DEMAND.finditer(question))
    units = tuple(dict.fromkeys(unit for unit in implicit if unit))
    predicates = _core_predicates(question, explicit, units)
    if policy is DemandBindingPolicy.NONE or not (explicit or implicit):
        return DemandBindingAssessment(True, explicit, units, predicates, (), ())

    sentences = [
        sentence.strip()
        for chunk in chunks
        for sentence in _SENTENCE.findall(chunk.content)
        if sentence.strip()
    ]
    matched: list[str] = []
    reasons: list[str] = []
    for value in explicit:
        local = [sentence for sentence in sentences if value in sentence]
        bound = [sentence for sentence in local if _predicate_matches(sentence, predicates)]
        if not bound:
            reasons.append(f"explicit_number_unbound:{value}")
        matched.extend(bound)

    for unit in implicit:
        local = [
            sentence
            for sentence in sentences
            if _NUMBER.search(sentence)
            and (not unit or unit in sentence)
            and _predicate_matches(sentence, predicates)
        ]
        if not local:
            reasons.append(f"implicit_numeric_demand_unbound:{unit or 'unspecified'}")
        matched.extend(local)

    return DemandBindingAssessment(
        not reasons,
        explicit,
        units,
        predicates,
        tuple(dict.fromkeys(matched)),
        tuple(reasons),
    )


def _core_predicates(
    question: str, explicit: tuple[str, ...], units: tuple[str, ...]
) -> tuple[str, ...]:
    del explicit, units
    return tuple(predicate for predicate in _CORE_PREDICATES if predicate in question)


def _predicate_matches(sentence: str, predicates: tuple[str, ...]) -> bool:
    return not predicates or all(predicate in sentence for predicate in predicates)
