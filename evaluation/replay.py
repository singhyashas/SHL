from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.agent import respond
from app.catalog import load_catalog
from app.schemas import ChatRequest
from evaluation.metrics import mean_recall_at_k, recall_at_k


DEFAULT_TRACE_PATH = Path(__file__).resolve().parent / "sample_traces.json"


def _load_traces(path: Path) -> list[dict[str, Any]]:
    traces = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(traces, list):
        raise ValueError("Trace file must contain a JSON array.")
    return traces


def _catalog_urls() -> set[str]:
    return {item["url"] for item in load_catalog()}


def evaluate_trace(trace: dict[str, Any], k: int = 10) -> dict[str, Any]:
    request = ChatRequest(messages=trace["messages"])
    response = respond(request)
    recommended_names = [item.name for item in response.recommendations]
    expected_names = trace.get("expected_recommendations", [])
    urls = _catalog_urls()

    return {
        "id": trace.get("id", "unnamed"),
        "recommendation_count": len(response.recommendations),
        "schema_ok": isinstance(response.reply, str) and isinstance(response.end_of_conversation, bool),
        "catalog_only": all(item.url in urls for item in response.recommendations),
        "recall_at_k": recall_at_k(recommended_names, expected_names, k=k),
        "expected": expected_names,
        "recommended": recommended_names[:k],
        "reply": response.reply,
    }


def evaluate_file(path: Path = DEFAULT_TRACE_PATH, k: int = 10) -> dict[str, Any]:
    trace_results = [evaluate_trace(trace, k=k) for trace in _load_traces(path)]
    return {
        "trace_count": len(trace_results),
        "mean_recall_at_k": mean_recall_at_k([result["recall_at_k"] for result in trace_results]),
        "hard_checks_ok": all(
            result["schema_ok"]
            and result["catalog_only"]
            and 0 <= result["recommendation_count"] <= 10
            for result in trace_results
        ),
        "traces": trace_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay local SHL recommender traces.")
    parser.add_argument("--traces", type=Path, default=DEFAULT_TRACE_PATH)
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    result = evaluate_file(args.traces, k=args.k)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
