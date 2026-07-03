from app.retriever import parse_query, recommend


def names_for(query: str) -> list[str]:
    return [item.name for item in recommend(query, limit=10)]


def test_java_developer_query_prioritizes_java_assessments():
    names = names_for("Hiring a mid-level Java developer")
    assert any("Java 8" in name for name in names[:5])
    assert any("Core Java" in name for name in names[:5])


def test_personality_query_returns_personality_assessments():
    recs = recommend("Add personality tests for a stakeholder-facing manager", limit=10)
    assert recs
    assert any(item.test_type == "P" for item in recs[:5])
    assert any("OPQ" in item.name or "Personality" in item.name for item in recs[:10])


def test_duration_constraint_is_detected():
    signals = parse_query("Need a Java test under 20 minutes")
    assert signals.max_duration_minutes == 20


def test_retriever_never_returns_more_than_ten():
    recs = recommend("software developer coding technical skills java python sql", limit=50)
    assert 1 <= len(recs) <= 10


def test_retriever_outputs_catalog_contract_fields():
    rec = recommend("Global Skills Assessment", limit=1)[0]
    assert rec.name
    assert rec.url.startswith("https://www.shl.com/products/product-catalog/view/")
    assert rec.test_type
