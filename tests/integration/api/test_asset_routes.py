"""Integration tests for campaign asset and fallback API routes (IMAGE-03)."""

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.main import create_app
from campaign.assets import AssetCache, build_cover_prompt

MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00"
    b"IEND\xaeB`\x82"
)


def test_get_asset_fallback_descriptor() -> None:
    """Verify fallback card is returned when no local image exists."""
    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/v1/campaigns/citadel_test/assets/cover/citadel_test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "fallback"
    assert data["image_url"] is None
    assert data["fallback_card"] is not None
    assert data["fallback_card"]["icon_symbol"] == "📖"
    assert "Citadel Test" in data["fallback_card"]["title"]


def test_get_asset_cached_and_raw_stream(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Verify cached asset status and raw binary streaming with security headers."""
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    camp_dir = campaigns_dir / "my_camp"
    camp_dir.mkdir()

    # Pre-install a cached cover image
    cache = AssetCache(camp_dir)
    prompt = build_cover_prompt("my_camp", "My Camp", "dark", "sketch")
    cache.install_asset("test_asset_key", prompt, MINIMAL_PNG)

    # Monkeypatch campaigns root lookup in route
    import api.routes.assets as asset_module

    monkeypatch.setattr(
        asset_module,
        "_get_campaign_dir",
        lambda cid: camp_dir,
    )

    app = create_app()
    client = TestClient(app)

    # Status check
    status_resp = client.get("/api/v1/campaigns/my_camp/assets/cover/my_camp")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "cached"
    assert status_data["image_url"] == "/api/v1/campaigns/my_camp/assets/cover/my_camp/raw"

    # Raw stream check
    raw_resp = client.get("/api/v1/campaigns/my_camp/assets/cover/my_camp/raw")
    assert raw_resp.status_code == 200
    assert raw_resp.content == MINIMAL_PNG
    assert raw_resp.headers["content-type"] == "image/png"
    assert raw_resp.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in raw_resp.headers["content-security-policy"]


def test_asset_routes_security_rejections() -> None:
    """Verify path traversal in campaign ID is rejected."""
    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/v1/campaigns/.._escape/assets/cover/my_camp")
    assert resp.status_code == 400
