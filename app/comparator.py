from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from app.catalog import load_catalog


COMPARE_PATTERNS = [
    r"\bcompare\b",
    r"\bdifference\b",
    r"\bdifferences\b",
    r"\bversus\b",
    r"\bvs\b",
    r"\bbetween\b",
]

CANONICAL_LABELS = {
    "gsa": "Global Skills Assessment",
    "opq": "Occupational Personality Questionnaire OPQ32r",
    "opq32": "Occupational Personality Questionnaire OPQ32r",
    "opq32r": "Occupational Personality Questionnaire OPQ32r",
}


def is_compare_request(text: str) -> bool:
    normalized = text.lower()
    return any(re.search(pattern, normalized) for pattern in COMPARE_PATTERNS)


def _candidate_labels(text: str) -> list[str]:
    labels: list[str] = []
    labels.extend(re.findall(r"\b[A-Z][A-Z0-9]{1,8}r?\b", text))
    labels.extend(re.findall(r"\bOPQ[0-9a-zA-Z]*\b", text, flags=re.IGNORECASE))
    labels.extend(re.findall(r"\bGSA\b", text, flags=re.IGNORECASE))

    normalized = text.lower()
    for item in load_catalog():
        name = item["name"]
        if name.lower() in normalized:
            labels.append(name)
            continue
        for alias in item.get("aliases", []):
            alias_text = alias.lower()
            if len(alias_text) >= 3 and re.search(rf"\b{re.escape(alias_text)}\b", normalized):
                labels.append(alias)

    return list(dict.fromkeys(label.strip() for label in labels if label.strip()))


def _match_score(label: str, item: dict[str, Any]) -> float:
    label_lower = label.lower()
    name = item["name"].lower()
    aliases = [alias.lower() for alias in item.get("aliases", [])]

    if label_lower == name:
        return 100.0
    if label_lower in aliases:
        return 95.0
    if re.search(rf"\b{re.escape(label_lower)}\b", name):
        return 85.0
    if any(label_lower in alias for alias in aliases):
        return 80.0
    return SequenceMatcher(None, label_lower, name).ratio() * 60


def find_assessment(label: str) -> dict[str, Any] | None:
    canonical_name = CANONICAL_LABELS.get(label.lower())
    if canonical_name:
        for item in load_catalog():
            if item["name"].lower() == canonical_name.lower():
                return item

    scored = sorted(((_match_score(label, item), item) for item in load_catalog()), key=lambda pair: pair[0], reverse=True)
    best_score, best_item = scored[0]
    return best_item if best_score >= 45 else None


def comparison_targets(text: str) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for label in _candidate_labels(text):
        item = find_assessment(label)
        if item and item["url"] not in seen_urls:
            targets.append(item)
            seen_urls.add(item["url"])
    return targets[:3]


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None or value == "":
        return "not listed"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "not listed"
    return str(value)


def compare(text: str) -> str:
    targets = comparison_targets(text)
    if len(targets) < 2:
        return "Which two SHL assessments should I compare? Please provide their names or abbreviations from the catalog."

    left, right = targets[0], targets[1]
    lines = [
        f"{left['name']} and {right['name']} differ as follows:",
        f"- Type: {left['name']} is {_format_value(left.get('categories'))}; {right['name']} is {_format_value(right.get('categories'))}.",
        f"- Duration: {left['name']} is {_format_value(left.get('duration_text'))}; {right['name']} is {_format_value(right.get('duration_text'))}.",
        f"- Job levels: {left['name']} targets {_format_value(left.get('job_levels'))}; {right['name']} targets {_format_value(right.get('job_levels'))}.",
        f"- Remote/adaptive: {left['name']} remote={_format_value(left.get('remote_testing'))}, adaptive={_format_value(left.get('adaptive'))}; {right['name']} remote={_format_value(right.get('remote_testing'))}, adaptive={_format_value(right.get('adaptive'))}.",
    ]

    left_description = left.get("description") or "No catalog description is listed."
    right_description = right.get("description") or "No catalog description is listed."
    lines.append(f"- Catalog focus: {left['name']}: {left_description} {right['name']}: {right_description}")
    return "\n".join(lines)
