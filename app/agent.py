from __future__ import annotations

import re

from app.comparator import compare, is_compare_request
from app.guardrails import refusal_reason
from app.retriever import recommend
from app.schemas import ChatRequest, ChatResponse


VAGUE_REQUESTS = {
    "assessment",
    "an assessment",
    "test",
    "a test",
    "i need an assessment",
    "need an assessment",
    "i need a test",
    "help me choose an assessment",
}


def _latest_user_text(request: ChatRequest) -> str:
    for message in reversed(request.messages):
        if message.role == "user":
            return message.content
    return ""


def _user_texts(request: ChatRequest) -> list[str]:
    return [message.content for message in request.messages if message.role == "user"]


def _conversation_query(request: ChatRequest) -> str:
    return " ".join(_user_texts(request))


def _is_vague(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9+#. ]+", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if normalized in VAGUE_REQUESTS:
        return True
    useful_tokens = [
        token
        for token in re.findall(r"[a-z0-9+#.]+", normalized)
        if token not in {"i", "need", "want", "a", "an", "the", "for", "to", "hire", "hiring"}
    ]
    return len(useful_tokens) < 2


def _has_actionable_context(text: str) -> bool:
    normalized = text.lower()
    if _is_vague(normalized):
        return False
    role_or_skill_patterns = [
        r"\bdeveloper\b",
        r"\bengineer\b",
        r"\bmanager\b",
        r"\bsales\b",
        r"\bgraduate\b",
        r"\banalyst\b",
        r"\bjava\b",
        r"\bpython\b",
        r"\bsql\b",
        r"\bjavascript\b",
        r"\bpersonality\b",
        r"\baptitude\b",
        r"\bcognitive\b",
        r"\bstakeholder\b",
        r"\bcommunication\b",
        r"\bleadership\b",
        r"\bjob description\b",
        r"\bjd\b",
    ]
    return any(re.search(pattern, normalized) for pattern in role_or_skill_patterns)


def _reply_for_recommendations(count: int, query: str) -> str:
    if re.search(r"\bactually\b|\badd\b|\binstead\b|\bchange\b|\bupdate\b|\brefine\b", query.lower()):
        return f"Updated the shortlist using the latest constraints. Here are {count} SHL catalog assessments."
    return f"Here are {count} SHL catalog assessments that fit the request."


def respond(request: ChatRequest) -> ChatResponse:
    user_text = _latest_user_text(request)
    full_query = _conversation_query(request)

    if not user_text:
        return ChatResponse(
            reply="Please tell me the role or skills you want to assess.",
            recommendations=[],
            end_of_conversation=False,
        )

    refusal = refusal_reason(user_text)
    if refusal:
        return ChatResponse(reply=refusal, recommendations=[], end_of_conversation=False)

    if is_compare_request(user_text):
        return ChatResponse(reply=compare(user_text), recommendations=[], end_of_conversation=False)

    if _is_vague(full_query) or not _has_actionable_context(full_query):
        return ChatResponse(
            reply="What role, skills, or job description should the SHL assessment shortlist target?",
            recommendations=[],
            end_of_conversation=False,
        )

    recommendations = recommend(full_query, limit=10)
    if recommendations:
        return ChatResponse(
            reply=_reply_for_recommendations(len(recommendations), user_text),
            recommendations=recommendations,
            end_of_conversation=True,
        )

    return ChatResponse(
        reply="I can help with SHL assessment selection. Please share the target role, key skills, or job description.",
        recommendations=[],
        end_of_conversation=False,
    )
