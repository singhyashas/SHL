from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.catalog import load_catalog
from app.schemas import Recommendation


TOKEN_RE = re.compile(r"[a-z0-9+#.]+")

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "around",
    "assessment",
    "assessments",
    "for",
    "hire",
    "hiring",
    "i",
    "in",
    "is",
    "job",
    "need",
    "of",
    "role",
    "test",
    "tests",
    "the",
    "to",
    "want",
    "who",
    "with",
}

TYPE_SYNONYMS = {
    "K": {
        "technical",
        "knowledge",
        "skills",
        "skill",
        "programming",
        "developer",
        "coding",
        "software",
        "engineering",
    },
    "S": {"simulation", "simulations", "coding", "automata", "hands-on", "practical"},
    "P": {"personality", "behavior", "behaviour", "behavioral", "behavioural", "opq"},
    "A": {"aptitude", "ability", "cognitive", "reasoning", "numerical", "verbal", "inductive"},
    "B": {"situational", "judgment", "judgement", "sjt", "biodata"},
    "C": {"competency", "competencies", "communication", "stakeholder", "leadership"},
    "D": {"development", "360", "feedback"},
    "E": {"exercise", "exercises", "assessment-center", "assessment-centre"},
}

SENIORITY_SYNONYMS = {
    "Entry-Level": {"entry", "entry-level", "junior", "graduate", "freshers", "fresher", "campus"},
    "Graduate": {"graduate", "campus", "freshers", "fresher"},
    "Mid-Professional": {"mid", "mid-level", "intermediate", "experienced"},
    "Manager": {"manager", "management"},
    "Front Line Manager": {"frontline", "front-line", "line-manager"},
    "Supervisor": {"supervisor"},
    "Director": {"director"},
    "Executive": {"executive", "senior", "leadership", "leader"},
}

ROLE_EXPANSIONS = {
    "developer": {"software", "programming", "coding", "technical"},
    "engineer": {"software", "technical", "programming"},
    "java": {"core", "j2ee", "jee", "spring", "developer"},
    "javascript": {"front", "front-end", "frontend", "web"},
    "python": {"programming", "developer"},
    "sql": {"database", "query"},
    "sales": {"salesperson", "selling", "customer"},
    "manager": {"leadership", "management", "supervisor"},
    "representative": {"entry", "service", "sales", "solution"},
    "graduate": {"entry", "verify", "reasoning", "g+"},
    "aptitude": {"ability", "verify", "reasoning", "g+"},
    "cognitive": {"ability", "verify", "reasoning", "g+"},
    "contact": {"center", "service", "phone"},
    "center": {"contact", "service", "phone"},
}

SKILL_TOKENS = {
    ".net",
    "c#",
    "c++",
    "excel",
    "java",
    "javascript",
    "python",
    "react",
    "salesforce",
    "sql",
}

GENERIC_ROLE_TOKENS = {"developer", "engineer", "programmer"}


@dataclass(frozen=True)
class QuerySignals:
    raw_text: str
    tokens: tuple[str, ...]
    expanded_tokens: tuple[str, ...]
    type_codes: tuple[str, ...]
    seniority_levels: tuple[str, ...]
    max_duration_minutes: int | None


@dataclass(frozen=True)
class IndexedItem:
    item: dict[str, Any]
    tokens: tuple[str, ...]
    token_counts: dict[str, int]
    length: int


def tokenize(text: str) -> list[str]:
    tokens = [token.strip(".") for token in TOKEN_RE.findall(text.lower())]
    return [token for token in tokens if token and token not in STOP_WORDS]


def _detect_type_codes(tokens: set[str], text: str) -> tuple[str, ...]:
    codes: list[str] = []
    for code, synonyms in TYPE_SYNONYMS.items():
        if tokens & synonyms:
            codes.append(code)
    if "personality tests" in text or "personality assessment" in text:
        codes.append("P")
    if "coding test" in text or "coding assessment" in text:
        codes.extend(["K", "S"])
    return tuple(dict.fromkeys(codes))


def _detect_seniority(tokens: set[str]) -> tuple[str, ...]:
    levels: list[str] = []
    for level, synonyms in SENIORITY_SYNONYMS.items():
        if tokens & synonyms:
            levels.append(level)
    return tuple(dict.fromkeys(levels))


def _detect_max_duration(text: str) -> int | None:
    patterns = [
        r"(?:under|below|less than|within|max(?:imum)?|up to)\s+(\d{1,3})\s*(?:min|mins|minutes)",
        r"(\d{1,3})\s*(?:min|mins|minutes)\s*(?:or less|max)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def parse_query(text: str) -> QuerySignals:
    normalized = text.lower()
    tokens = tokenize(normalized)
    if set(tokens) & SKILL_TOKENS:
        tokens = [token for token in tokens if token not in GENERIC_ROLE_TOKENS]
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(sorted(ROLE_EXPANSIONS.get(token, set())))
    token_set = set(tokens)
    return QuerySignals(
        raw_text=text,
        tokens=tuple(tokens),
        expanded_tokens=tuple(dict.fromkeys(expanded)),
        type_codes=_detect_type_codes(token_set, normalized),
        seniority_levels=_detect_seniority(token_set),
        max_duration_minutes=_detect_max_duration(normalized),
    )


@lru_cache(maxsize=1)
def _index() -> tuple[list[IndexedItem], dict[str, int], float]:
    indexed: list[IndexedItem] = []
    document_frequency: dict[str, int] = {}

    for item in load_catalog():
        weighted_text = " ".join(
            [
                item.get("name", ""),
                item.get("name", ""),
                " ".join(item.get("aliases", [])),
                " ".join(item.get("categories", [])),
                " ".join(item.get("job_levels", [])),
                item.get("description", ""),
                item.get("search_text", ""),
            ]
        )
        tokens = tokenize(weighted_text)
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        for token in counts:
            document_frequency[token] = document_frequency.get(token, 0) + 1
        indexed.append(IndexedItem(item=item, tokens=tuple(tokens), token_counts=counts, length=len(tokens)))

    average_length = sum(item.length for item in indexed) / max(len(indexed), 1)
    return indexed, document_frequency, average_length


def _bm25_score(indexed_item: IndexedItem, query_tokens: tuple[str, ...], document_frequency: dict[str, int], average_length: float) -> float:
    if not query_tokens:
        return 0.0

    total_documents = len(load_catalog())
    k1 = 1.5
    b = 0.75
    score = 0.0

    for token in query_tokens:
        frequency = indexed_item.token_counts.get(token, 0)
        if not frequency:
            continue
        df = document_frequency.get(token, 0)
        idf = math.log(1 + (total_documents - df + 0.5) / (df + 0.5))
        denominator = frequency + k1 * (1 - b + b * indexed_item.length / average_length)
        score += idf * (frequency * (k1 + 1)) / denominator

    return score


def _field_boost(item: dict[str, Any], signals: QuerySignals) -> float:
    name = item.get("name", "").lower()
    aliases = {alias.lower() for alias in item.get("aliases", [])}
    categories = {category.lower() for category in item.get("categories", [])}
    job_levels = set(item.get("job_levels", []))
    type_codes = set(item.get("test_type_codes", []))
    primary_type = item.get("test_type", "")

    score = 0.0
    for token in signals.tokens:
        if token in name:
            score += 4.0
        if re.search(rf"\b{re.escape(token)}\s+\d+\b", name):
            score += 10.0
        if token in aliases:
            score += 8.0
        if any(token in category for category in categories):
            score += 2.0

    for code in signals.type_codes:
        if code in type_codes:
            score += 8.0
            if primary_type == code:
                score += 4.0
            if len(type_codes) > 3:
                score -= 4.0
        elif signals.type_codes:
            score -= 1.5

    if "report" in name and "report" not in signals.tokens:
        score -= 4.0

    for level in signals.seniority_levels:
        if level in job_levels:
            score += 4.0

    if signals.max_duration_minutes is not None:
        duration = item.get("duration_minutes")
        if duration is not None and duration <= signals.max_duration_minutes:
            score += 3.0
        elif duration is not None:
            score -= 2.0

    return score


def search(text: str, limit: int = 10) -> list[dict[str, Any]]:
    signals = parse_query(text)
    indexed, document_frequency, average_length = _index()
    scored: list[tuple[float, dict[str, Any]]] = []

    for indexed_item in indexed:
        score = _bm25_score(indexed_item, signals.expanded_tokens, document_frequency, average_length)
        score += _field_boost(indexed_item.item, signals)
        if score > 0:
            scored.append((score, indexed_item.item))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["name"].lower()))
    return [item for _, item in scored[: max(1, min(limit, 10))]]


def recommend(text: str, limit: int = 10) -> list[Recommendation]:
    return [
        Recommendation(name=item["name"], url=item["url"], test_type=item["test_type"])
        for item in search(text, limit=limit)
    ]
