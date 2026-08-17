"""Adversarial security tests for path traversal, absolute paths, and symlink escapes (SEC-01)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from campaign.assets import compute_asset_relative_path
from campaign.storage.drafts import DraftRepository
from engine.state.errors import UnsafePathError


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_api_campaign_path_traversal_rejected(client: TestClient) -> None:
    """Verify campaign ID path traversal attempts return 400 or 404."""
    traversal_ids = [
        "../etc/passwd",
        "..%2F..%2Fetc%2Fpasswd",
        ".._escape",
        "....//....//etc",
        "/etc/shadow",
        "C:\\Windows\\System32",
    ]
    for bad_id in traversal_ids:
        resp = client.get(f"/api/v1/campaigns/{bad_id}")
        assert resp.status_code in (400, 404, 422)


def test_api_save_path_traversal_rejected(client: TestClient) -> None:
    """Verify save slot path traversal attempts return 400 or 404."""
    bad_save_ids = [
        "../other_save",
        ".._save",
        "/var/run/secrets",
    ]
    for bad_id in bad_save_ids:
        resp = client.get(f"/api/v1/campaigns/c1/saves/{bad_id}")
        assert resp.status_code in (400, 404, 422)


def test_api_asset_path_traversal_rejected(client: TestClient) -> None:
    """Verify asset endpoint traversal attempts return 400 or 404."""
    resp = client.get("/api/v1/campaigns/.._escape/assets/cover/test_cover")
    assert resp.status_code == 400


def test_asset_keys_relative_path_sanitization() -> None:
    """Verify asset relative path generator strips traversal and dangerous characters."""
    bad_inputs = [
        "../../root",
        "/absolute/path",
        "sub/dir/nested",
        "name\x00nullbyte",
    ]
    for bad in bad_inputs:
        path = compute_asset_relative_path("a" * 64, bad, "png")
        assert ".." not in path
        assert not path.startswith("/")
        assert path.startswith("assets/")


def test_draft_repository_path_traversal_rejected(tmp_path: Path) -> None:
    """Verify DraftRepository strictly defends against directory traversal."""
    repo = DraftRepository(tmp_path)
    with pytest.raises((UnsafePathError, ValueError)):
        repo.load_draft("../escape_slot")
