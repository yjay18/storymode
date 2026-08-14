"""Integration tests for campaign and save routes."""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Path:
    """Setup a temporary campaigns directory with valid minimal campaign."""
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir(parents=True)

    # Copy valid-minimal campaign fixture
    fixture_src = Path(__file__).parent.parent.parent / "fixtures" / "campaigns" / "valid-minimal"
    target_camp = campaigns_dir / "minimal-campaign"
    shutil.copytree(fixture_src, target_camp)

    return campaigns_dir


@pytest.fixture
def client(temp_campaigns_dir: Path) -> TestClient:
    """Create a TestClient with temporary campaigns directory."""
    settings = Settings(campaigns_dir=str(temp_campaigns_dir.parent))
    app = create_app(settings=settings)
    return TestClient(app)


def test_list_campaigns(client: TestClient) -> None:
    """GET /api/v1/campaigns returns list of available campaigns."""
    response = client.get("/api/v1/campaigns")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    item = next(c for c in data if c["campaign_id"] == "minimal-campaign")
    assert item["title"] == "Minimal"
    assert item["status"] == "draft"


def test_get_campaign_detail(client: TestClient) -> None:
    """GET /api/v1/campaigns/{campaign_id} returns campaign detail."""
    response = client.get("/api/v1/campaigns/minimal-campaign")
    assert response.status_code == 200
    data = response.json()
    assert data["campaign_id"] == "minimal-campaign"
    assert "backgrounds" in data
    assert len(data["backgrounds"]) >= 1


def test_get_campaign_not_found(client: TestClient) -> None:
    """GET /api/v1/campaigns/{campaign_id} with unknown ID returns 404."""
    response = client.get("/api/v1/campaigns/unknown-campaign")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "not_found"


def test_get_campaign_validation(client: TestClient) -> None:
    """GET /api/v1/campaigns/{campaign_id}/validation returns validation report."""
    response = client.get("/api/v1/campaigns/minimal-campaign/validation")
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["diagnostics"] == []


def test_create_save_valid(client: TestClient) -> None:
    """POST /api/v1/saves creates a new character and save."""
    # Stats with exactly 27 points (e.g. 15, 14, 13, 12, 10, 8 = 9+7+5+4+2+0 = 27)
    payload = {
        "campaign_id": "minimal-campaign",
        "slot_kind": "manual",
        "slot_name": "Hero Save",
        "player_name": "Valiant Hero",
        "background_id": "bg-1",
        "stats": {
            "strength": 10,
            "dexterity": 12,
            "constitution": 13,
            "intelligence": 15,
            "wisdom": 14,
            "charisma": 8,
        },
        "difficulty": "normal",
        "command_id": "cmd-create-1",
    }
    response = client.post("/api/v1/saves", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["campaign_id"] == "minimal-campaign"
    assert data["revision"] == 1
    assert data["player_name"] == "Valiant Hero"
    assert "save_id" in data


def test_create_save_invalid_point_buy(client: TestClient) -> None:
    """POST /api/v1/saves returns 422 if point buy is invalid."""
    payload = {
        "campaign_id": "minimal-campaign",
        "slot_kind": "manual",
        "slot_name": "Hero Save",
        "player_name": "Invalid Hero",
        "background_id": "bg-1",
        "stats": {
            "strength": 18,  # Exceeds max pre-bonus
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10,
        },
        "difficulty": "normal",
        "command_id": "cmd-create-2",
    }
    response = client.post("/api/v1/saves", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "validation_error"


def test_create_save_unknown_background(client: TestClient) -> None:
    """POST /api/v1/saves returns 422 if background does not exist."""
    payload = {
        "campaign_id": "minimal-campaign",
        "slot_kind": "manual",
        "slot_name": "Hero Save",
        "player_name": "Hero",
        "background_id": "bg-unknown",
        "stats": {
            "strength": 10,
            "dexterity": 12,
            "constitution": 13,
            "intelligence": 15,
            "wisdom": 14,
            "charisma": 8,
        },
        "difficulty": "normal",
        "command_id": "cmd-create-3",
    }
    response = client.post("/api/v1/saves", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "validation_error"


def test_create_save_unknown_campaign(client: TestClient) -> None:
    """POST /api/v1/saves returns 404 if campaign is not found."""
    payload = {
        "campaign_id": "nonexistent-campaign",
        "slot_kind": "manual",
        "slot_name": "Hero Save",
        "player_name": "Hero",
        "background_id": "bg-1",
        "stats": {
            "strength": 10,
            "dexterity": 12,
            "constitution": 13,
            "intelligence": 15,
            "wisdom": 14,
            "charisma": 8,
        },
        "difficulty": "normal",
        "command_id": "cmd-create-4",
    }
    response = client.post("/api/v1/saves", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "not_found"


def test_create_save_unsafe_id(client: TestClient) -> None:
    """POST /api/v1/saves rejects path traversal campaign IDs."""
    payload = {
        "campaign_id": "../escaped-campaign",
        "slot_kind": "manual",
        "slot_name": "Hero Save",
        "player_name": "Hero",
        "background_id": "bg-1",
        "stats": {
            "strength": 10,
            "dexterity": 12,
            "constitution": 13,
            "intelligence": 15,
            "wisdom": 14,
            "charisma": 8,
        },
        "difficulty": "normal",
        "command_id": "cmd-create-5",
    }
    response = client.post("/api/v1/saves", json=payload)
    assert response.status_code in (400, 404, 422)


def test_create_save_idempotency(client: TestClient) -> None:
    """POST /api/v1/saves with duplicate command_id returns original result."""
    payload = {
        "campaign_id": "minimal-campaign",
        "slot_kind": "manual",
        "slot_name": "Hero Save",
        "player_name": "Valiant Hero",
        "background_id": "bg-1",
        "stats": {
            "strength": 10,
            "dexterity": 12,
            "constitution": 13,
            "intelligence": 15,
            "wisdom": 14,
            "charisma": 8,
        },
        "difficulty": "normal",
        "command_id": "cmd-create-idempotent",
    }
    res1 = client.post("/api/v1/saves", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()

    res2 = client.post("/api/v1/saves", json=payload)
    assert res2.status_code in (200, 201)
    data2 = res2.json()

    assert data1["save_id"] == data2["save_id"]
    assert data1["revision"] == data2["revision"]
