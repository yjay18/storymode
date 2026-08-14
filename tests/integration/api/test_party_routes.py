"""Integration tests for party API routes (PROG-05)."""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir(parents=True)

    fixture_src = Path(__file__).parent.parent.parent / "fixtures" / "campaigns" / "valid-minimal"
    target_camp = campaigns_dir / "minimal-campaign"
    shutil.copytree(fixture_src, target_camp)

    settings = Settings(campaigns_dir=str(campaigns_dir.parent))
    app = create_app(settings=settings)
    return TestClient(app)


def _create_test_save(client: TestClient) -> str:
    res = client.post(
        "/api/v1/saves",
        json={
            "command_id": "cmd-init-1",
            "campaign_id": "minimal-campaign",
            "slot_kind": "manual",
            "slot_name": "Hero Save",
            "player_name": "Hero",
            "background_id": "bg-1",
            "difficulty": "normal",
            "stats": {
                "strength": 10,
                "dexterity": 12,
                "constitution": 13,
                "intelligence": 15,
                "wisdom": 14,
                "charisma": 8,
            },
        },
    )
    assert res.status_code == 201
    return str(res.json()["save_id"])


def test_party_lifecycle_flow(client: TestClient) -> None:
    save_id = _create_test_save(client)
    camp_id = "minimal-campaign"

    # 1. Get initial party view
    res = client.get(f"/api/v1/saves/{camp_id}/{save_id}/party")
    assert res.status_code == 200
    data = res.json()
    assert data["protagonist_id"] == "player-1"
    assert len(data["companions"]) == 0

    # 2. Recruit comp-1 (initial revision is 1)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/party/recruit",
        json={
            "command_id": "cmd-recruit-1",
            "expected_revision": 1,
            "companion_id": "comp-1",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["revision"] == 2
    assert len(data["party"]["companions"]) == 1
    assert data["party"]["companions"][0]["id"] == "comp-1"
    assert "comp-1" not in data["party"]["active_companion_ids"]

    # 3. Activate companion (revision 2 -> 3)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/party/activate",
        json={
            "command_id": "cmd-activate-1",
            "expected_revision": 2,
            "companion_id": "comp-1",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["revision"] == 3
    assert "comp-1" in data["party"]["active_companion_ids"]

    # 4. Deactivate companion (revision 3 -> 4)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/party/deactivate",
        json={
            "command_id": "cmd-deactivate-1",
            "expected_revision": 3,
            "companion_id": "comp-1",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["revision"] == 4
    assert "comp-1" not in data["party"]["active_companion_ids"]

    # 5. Stale revision rejection (reusing revision 3)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/party/leave",
        json={
            "command_id": "cmd-leave-stale",
            "expected_revision": 3,
            "companion_id": "comp-1",
        },
    )
    assert res.status_code == 409

    # 6. Companion leaves party (revision 4 -> 5)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/party/leave",
        json={
            "command_id": "cmd-leave-1",
            "expected_revision": 4,
            "companion_id": "comp-1",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["revision"] == 5
    assert len(data["party"]["companions"]) == 0
