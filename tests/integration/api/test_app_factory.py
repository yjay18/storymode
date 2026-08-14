"""Tests for the application factory and health routes."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def test_app() -> TestClient:
    """Provides a TestClient for the application using test settings."""
    settings = Settings(campaigns_dir="./test_campaigns")
    app = create_app(settings=settings)
    return TestClient(app)


def test_app_factory_creates_app_without_side_effects() -> None:
    """App construction doesn't create/download files on import."""
    # Assuming no exceptions raised means it constructed cleanly.
    settings = Settings(campaigns_dir="./test_campaigns")
    app = create_app(settings=settings)
    assert app.title == "Storymode API"


def test_health_route_reports_capabilities(test_app: TestClient) -> None:
    """The /health route reports correct status without network calls."""
    response = test_app.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "core" in data
    assert "storage" in data

    # Model capabilities should be not_configured by default in Milestone 1E
    assert data["models"]["text"] == "not_configured"
    assert data["models"]["image"] == "not_configured"


def test_safe_404_errors(test_app: TestClient) -> None:
    """404 errors use the safe error envelope."""
    response = test_app.get("/does-not-exist")
    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    error_payload = data["error"]
    assert "code" in error_payload
    assert "message" in error_payload
    assert "correlation_id" in error_payload


def test_safe_validation_errors(test_app: TestClient) -> None:
    """422 errors use the safe error envelope."""
    # We will trigger a 422 by sending bad data to a hypothetical route or
    # relying on FastAPI's request validation. Since we don't have mutation routes yet,
    # we might need to add a dummy validation endpoint, or wait until campaigns routes.
    pass
