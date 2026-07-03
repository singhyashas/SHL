from __future__ import annotations


def normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def recall_at_k(recommended_names: list[str], expected_names: list[str], k: int = 10) -> float:
    """Return the fraction of expected items present in the top-k recommendations."""
    if not expected_names:
        return 1.0

    recommended = {normalize_name(name) for name in recommended_names[:k]}
    expected = {normalize_name(name) for name in expected_names}
    return len(recommended & expected) / len(expected)


def mean_recall_at_k(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return sum(scores) / len(scores)
