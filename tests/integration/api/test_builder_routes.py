"""Integration tests for FastAPI builder endpoints (BUILD-09)."""

import json
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.main import create_app


@pytest.fixture
def test_app(tmp_path: Path) -> httpx.AsyncClient:
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        campaigns_dir=str(campaigns_dir),
        ollama_url="http://127.0.0.1:11434",
    )
    app = create_app(settings)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.anyio
async def test_guided_draft_lifecycle_endpoints(test_app: httpx.AsyncClient) -> None:
    # 1. Create guided draft
    create_payload = {
        "brief": {
            "title": "API Test Realm",
            "premise": "A kingdom built through API endpoints.",
            "campaign_mode": "faithful_story",
            "genre": "dark fantasy",
        }
    }
    resp = await test_app.post("/api/v1/builder/drafts/guided", json=create_payload)
    assert resp.status_code == 201
    data = resp.json()
    draft_id = data["draft_id"]
    assert data["brief"]["title"] == "API Test Realm"
    assert data["revision"] == 1

    # 2. Get draft
    get_resp = await test_app.get(f"/api/v1/builder/drafts/{draft_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["draft_id"] == draft_id

    # 3. List drafts
    list_resp = await test_app.get("/api/v1/builder/drafts")
    assert list_resp.status_code == 200
    assert any(d["draft_id"] == draft_id for d in list_resp.json())

    # 4. Cancel draft
    cancel_resp = await test_app.post(f"/api/v1/builder/drafts/{draft_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["revision"] == 2

    # 5. Validation report on incomplete draft
    val_resp = await test_app.get(f"/api/v1/builder/drafts/{draft_id}/validate")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["is_valid"] is False
    assert val_data["is_publish_ready"] is False


@pytest.mark.anyio
async def test_quick_draft_creation_endpoint(test_app: httpx.AsyncClient) -> None:
    quick_payload = {
        "quick_input": {
            "premise": "A lone ranger traversing the haunted woods.",
            "campaign_mode": "llm_decide",
        }
    }
    resp = await test_app.post("/api/v1/builder/drafts/quick", json=quick_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "A lone ranger" in data["brief"]["premise"]
    assert data["brief"]["title"] != ""


@pytest.mark.anyio
async def test_publish_unconfirmed_and_success_flow(
    test_app: httpx.AsyncClient, tmp_path: Path
) -> None:
    # 1. Create draft
    create_payload = {
        "brief": {
            "title": "Minimal Pack",
            "premise": "A valid minimal pack.",
        }
    }
    resp = await test_app.post("/api/v1/builder/drafts/guided", json=create_payload)
    draft_id = resp.json()["draft_id"]

    # 2. Populate all stages with fixture files
    fixtures_dir = Path("tests/fixtures/campaigns/valid-minimal")

    meta_json = json.loads((fixtures_dir / "campaign.json").read_text(encoding="utf-8"))
    meta_json["status"] = "draft"
    meta_json.pop("content_fingerprint", None)
    style_json = json.loads((fixtures_dir / "style.json").read_text(encoding="utf-8"))

    # Edit meta_style
    await test_app.put(
        f"/api/v1/builder/drafts/{draft_id}/stages/meta_style",
        json={
            "expected_revision": 1,
            "artifact_data": {
                "contract_version": 1,
                "prompt_version": "campaign-meta_style/1.0.0",
                "request_id": "req-1",
                "stage": "meta_style",
                "meta": meta_json,
                "style": style_json,
            },
        },
    )

    # 3. Publish unconfirmed fails with 422
    pub_unconfirmed = await test_app.post(
        f"/api/v1/builder/drafts/{draft_id}/publish", json={"confirmed": False}
    )
    assert pub_unconfirmed.status_code == 422
