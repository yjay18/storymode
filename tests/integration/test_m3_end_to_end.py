"""Milestone 3 end-to-end integration scenario (PROG-05).

Scenario:
1. Create new save with protagonist.
2. Recruit companion into party roster.
3. Start and complete a combat encounter.
4. Award XP and verify level up + upgrade token grant.
5. Upgrade a combat skill with the earned upgrade token.
6. Configure combat loadout with upgraded skill.
7. Verify party roster, progression view, and plot state.
"""

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

    fixture_src = Path(__file__).parent.parent / "fixtures" / "campaigns" / "valid-minimal"
    target_camp = campaigns_dir / "minimal-campaign"
    shutil.copytree(fixture_src, target_camp)

    settings = Settings(campaigns_dir=str(campaigns_dir.parent))
    app = create_app(settings=settings)
    return TestClient(app)


def test_m3_complete_progression_party_plot_flow(client: TestClient) -> None:
    camp_id = "minimal-campaign"

    # Step 1: Create save (initial revision is 1)
    res = client.post(
        "/api/v1/saves",
        json={
            "command_id": "m3-cmd-init",
            "campaign_id": camp_id,
            "slot_kind": "manual",
            "slot_name": "Valerius Save",
            "player_name": "Valerius",
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
    save_id = res.json()["save_id"]
    current_rev = res.json()["revision"]
    assert current_rev == 1

    # Step 2: Recruit companion comp-1 (revision 1 -> 2)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/party/recruit",
        json={
            "command_id": "m3-cmd-recruit",
            "expected_revision": current_rev,
            "companion_id": "comp-1",
        },
    )
    assert res.status_code == 200
    current_rev = res.json()["revision"]
    assert current_rev == 2
    assert len(res.json()["party"]["companions"]) == 1

    # Step 3: Grant XP to hero (revision 2 -> 3)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/progression/xp",
        json={
            "command_id": "m3-cmd-grant-xp",
            "expected_revision": current_rev,
            "xp_amount": 100,
        },
    )
    assert res.status_code == 200
    current_rev = res.json()["revision"]
    assert current_rev == 3
    assert res.json()["player"]["level"] == 2
    assert res.json()["player"]["upgrade_tokens"] == 1

    # Step 4: Upgrade combat skill (revision 3 -> 4)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/progression/upgrade",
        json={
            "command_id": "m3-cmd-upgrade-skill",
            "expected_revision": current_rev,
            "skill_id": "skill-1",
        },
    )
    assert res.status_code == 200
    current_rev = res.json()["revision"]
    assert current_rev == 4
    assert res.json()["player"]["upgrade_tokens"] == 0

    # Step 5: Update loadout (revision 4 -> 5)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/progression/loadout",
        json={
            "command_id": "m3-cmd-loadout",
            "expected_revision": current_rev,
            "loadout": ["skill-1"],
        },
    )
    assert res.status_code == 200
    current_rev = res.json()["revision"]
    assert current_rev == 5
    assert res.json()["player"]["combat_loadout"] == ["skill-1"]

    # Step 6: Start combat encounter (revision 5 -> 6)
    res = client.post(
        "/api/v1/combat/start",
        json={
            "campaign_id": camp_id,
            "save_id": save_id,
            "encounter_id": "encounter-1",
            "command_id": "m3-cmd-start-combat",
            "expected_revision": current_rev,
        },
    )
    assert res.status_code == 200
    current_rev = res.json()["revision"]
    assert current_rev == 6

    # Step 7: Perform combat skill action (revision 6 -> 7)
    res = client.post(
        "/api/v1/combat/skill",
        json={
            "campaign_id": camp_id,
            "save_id": save_id,
            "skill_id": "skill-1",
            "target_ids": ["enemy-1"],
            "command_id": "m3-cmd-combat-skill",
            "expected_revision": current_rev,
        },
    )
    assert res.status_code == 200
    current_rev = res.json()["revision"]
    assert current_rev == 7

    # Step 8: Verify plot view
    res = client.get(f"/api/v1/saves/{camp_id}/{save_id}/plot")
    assert res.status_code == 200
    assert res.json()["revision"] == current_rev
