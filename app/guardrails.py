from __future__ import annotations

import re


PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"forget (all )?(previous|prior|above) instructions",
    r"system prompt",
    r"developer message",
    r"jailbreak",
    r"act as",
    r"reveal .*instructions",
]

LEGAL_PATTERNS = [
    r"\blegal\b",
    r"\blaw\b",
    r"\blawsuit\b",
    r"\bcompliance\b",
    r"\bdiscrimination\b",
    r"\beeoc\b",
    r"\bgdpr\b",
    r"\bvisa\b",
]

GENERAL_HIRING_PATTERNS = [
    r"salary",
    r"compensation",
    r"interview questions",
    r"write .*job description",
    r"make .*job description",
    r"how (do|should) i hire",
    r"recruiting strategy",
    r"where (can|should) i find candidates",
]

OFF_TOPIC_PATTERNS = [
    r"\bweather\b",
    r"\bstock price\b",
    r"\bmovie\b",
    r"\brecipe\b",
    r"\bjoke\b",
    r"\bcapital of\b",
    r"\btranslate\b",
    r"\bwrite (me )?(a )?poem\b",
]


def refusal_reason(text: str) -> str | None:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()

    if any(re.search(pattern, normalized) for pattern in PROMPT_INJECTION_PATTERNS):
        return "I can only use the conversation to recommend or compare SHL catalog assessments, so I cannot follow instruction-changing requests."

    if any(re.search(pattern, normalized) for pattern in LEGAL_PATTERNS):
        return "I can help select SHL assessments, but I cannot provide legal or compliance advice."

    if any(re.search(pattern, normalized) for pattern in GENERAL_HIRING_PATTERNS):
        return "I can help with SHL assessment selection, but not general hiring strategy or interview advice."

    outside_catalog = re.search(r"\b(hacker ?rank|codility|leetcode|testgorilla|mercer|criterion)\b", normalized)
    if outside_catalog:
        return "I can only discuss SHL assessments from the catalog for this task."

    if any(re.search(pattern, normalized) for pattern in OFF_TOPIC_PATTERNS):
        return "I can only help with SHL assessment recommendations or catalog-grounded comparisons."

    return None
