"""Adversarial security tests for payload sizes, malformed JSON, and strict schemas (SEC-01)."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_malformed_json_returns_422() -> None:
    """Verify malformed JSON requests are safely rejected with 422 rather than crashing."""
    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/api/v1/builder/drafts/guided",
        content="{ bad json payload [[",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data or "detail" in data


def test_extra_fields_rejected_by_strict_api_schemas() -> None:
    """Verify extra unexpected fields on API request bodies return 422."""
    app = create_app()
    client = TestClient(app)

    payload = {
        "title": "Valid Title",
        "premise": "Valid premise text.",
        "unexpected_malicious_field": "injected value",
    }
    resp = client.post("/api/v1/builder/drafts/guided", json=payload)
    assert resp.status_code == 422


def test_oversized_action_input_rejection() -> None:
    """Verify massive input strings exceeding character limits return 422."""
    app = create_app()
    client = TestClient(app)

    huge_input = "A" * 50000  # 50k characters (limit is 2000)
    resp = client.post(
        "/api/v1/builder/drafts/quick",
        json={"raw_prompt": huge_input},
    )
    assert resp.status_code == 422
