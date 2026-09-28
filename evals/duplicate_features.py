from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from evals.claim_extractor import extract_claim_signature

ALIASES = {
    "Reciprocal Rank Fusion": "RRF",
    "最终验收集": "Holdout ",
}
FEATURE_NAMES = ("alias", "pronoun", "negation", "number", "date")
CHINESE_TENS = {
    "十": 10,
    "二十": 20,
    "三十": 30,
    "四十": 40,
    "五十": 50,
    "六十": 60,
    "七十": 70,
    "八十": 80,
    "九十": 90,
}


@dataclass(frozen=True, slots=True)
class FeaturePair:
    left: str
    right: str
    applied: bool


def normalize_alias(text: str) -> str:
    for alias, canonical in ALIASES.items():
        text = text.replace(alias, canonical)
    return re.sub(r"\s+", " ", text)


def normalize_pronoun_pair(left: str, right: str) -> FeaturePair:
    left_signature = extract_claim_signature(left)
    right_signature = extract_claim_signature(right)
    changed = False
    if re.match(r"^(它|其)", left) and right_signature.resolved and right_signature.subject:
        left = re.sub(r"^(它|其)", right_signature.subject, left, count=1)
        changed = True
    if re.match(r"^(它|其)", right) and left_signature.resolved and left_signature.subject:
        right = re.sub(r"^(它|其)", left_signature.subject, right, count=1)
        changed = True
    return FeaturePair(left, right, changed)


def normalize_negation(text: str) -> str:
    replacements = {
        "不能用于": "禁止用于",
        "不用于": "禁止用于",
        "不能证明": "无法证明",
        "不会": "不",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def normalize_number(text: str) -> str:
    for chinese, value in sorted(CHINESE_TENS.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(chinese, str(value))

    def percentage(match: re.Match[str]) -> str:
        return _decimal_text(Decimal(match.group(1)) / 100)

    text = re.sub(r"(\d+(?:\.\d+)?)\s*%", percentage, text)

    def decimal(match: re.Match[str]) -> str:
        return _decimal_text(Decimal(match.group(0)))

    return re.sub(r"\d+(?:\.\d+)?", decimal, text)


def normalize_date(text: str) -> str:
    def chinese_date(match: re.Match[str]) -> str:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"

    return re.sub(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", chinese_date, text)


def transform_pair(left: str, right: str, features: tuple[str, ...]) -> FeaturePair:
    original = (left, right)
    if "alias" in features:
        left, right = normalize_alias(left), normalize_alias(right)
    if "pronoun" in features:
        resolved = normalize_pronoun_pair(left, right)
        left, right = resolved.left, resolved.right
    if "negation" in features:
        left, right = normalize_negation(left), normalize_negation(right)
    if "date" in features:
        left, right = normalize_date(left), normalize_date(right)
    if "number" in features:
        left, right = normalize_number(left), normalize_number(right)
    return FeaturePair(left, right, (left, right) != original)
