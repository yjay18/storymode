"""Integration tests for progression API routes (PROG-05)."""

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


def test_progression_flow(client: TestClient) -> None:
    save_id = _create_test_save(client)
    camp_id = "minimal-campaign"

    # 1. Get initial progression
    res = client.get(f"/api/v1/saves/{camp_id}/{save_id}/progression")
    assert res.status_code == 200
    data = res.json()
    assert data["player"]["level"] == 1
    assert data["player"]["upgrade_tokens"] == 0

    # 2. Grant 100 XP -> player levels up to 2, gets 1 upgrade token (revision 1 -> 2)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/progression/xp",
        json={
            "command_id": "cmd-xp-1",
            "expected_revision": 1,
            "xp_amount": 100,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["revision"] == 2
    assert data["player"]["level"] == 2
    assert data["player"]["upgrade_tokens"] == 1

    # 3. Upgrade skill-1 from level 1 to level 2 (revision 2 -> 3)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/progression/upgrade",
        json={
            "command_id": "cmd-upgrade-1",
            "expected_revision": 2,
            "skill_id": "skill-1",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["revision"] == 3
    assert data["player"]["upgrade_tokens"] == 0
    skill_view = next(s for s in data["player"]["known_skills"] if s["skill_id"] == "skill-1")
    assert skill_view["current_level"] == 2

    # 4. Attempt second upgrade with 0 tokens -> 422 rejected
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/progression/upgrade",
        json={
            "command_id": "cmd-upgrade-fail",
            "expected_revision": 3,
            "skill_id": "skill-1",
        },
    )
    assert res.status_code == 422

    # 5. Set combat loadout (revision 3 -> 4)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/progression/loadout",
        json={
            "command_id": "cmd-loadout-1",
            "expected_revision": 3,
            "loadout": ["skill-1"],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["revision"] == 4
    assert data["player"]["combat_loadout"] == ["skill-1"]
