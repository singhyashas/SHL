from evaluation.metrics import mean_recall_at_k, recall_at_k
from evaluation.replay import DEFAULT_TRACE_PATH, evaluate_file, evaluate_trace


def test_recall_at_k_counts_expected_hits():
    assert recall_at_k(["A", "B", "C"], ["B", "D"], k=2) == 0.5
    assert recall_at_k(["A"], [], k=10) == 1.0
    assert mean_recall_at_k([1.0, 0.5]) == 0.75


def test_sample_trace_replay_runs_hard_checks():
    result = evaluate_file(DEFAULT_TRACE_PATH, k=10)
    assert result["trace_count"] >= 4
    assert result["hard_checks_ok"] is True
    assert 0 <= result["mean_recall_at_k"] <= 1


def test_vague_trace_has_no_recommendations_and_schema_ok():
    result = evaluate_trace(
        {
            "id": "vague",
            "messages": [{"role": "user", "content": "I need an assessment"}],
            "expected_recommendations": [],
        }
    )
    assert result["schema_ok"] is True
    assert result["catalog_only"] is True
    assert result["recommendation_count"] == 0
