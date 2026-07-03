from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_required_payload():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_clarifies_vague_request_with_empty_recommendations():
    response = client.post("/chat", json={"messages": [{"role": "user", "content": "I need an assessment"}]})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"reply", "recommendations", "end_of_conversation"}
    assert body["recommendations"] == []
    assert body["end_of_conversation"] is False


def test_chat_returns_schema_valid_catalog_recommendations_for_specific_request():
    response = client.post("/chat", json={"messages": [{"role": "user", "content": "Hiring a Java developer"}]})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"reply", "recommendations", "end_of_conversation"}
    assert 1 <= len(body["recommendations"]) <= 10
    assert set(body["recommendations"][0]) == {"name", "url", "test_type"}
    assert body["recommendations"][0]["url"].startswith("https://www.shl.com/products/product-catalog/view/")


def test_chat_rejects_extra_request_fields():
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Hiring a Java developer"}], "state": {}},
    )
    assert response.status_code == 422
