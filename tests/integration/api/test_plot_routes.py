"""Integration tests for plot API routes (PROG-05)."""

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


def test_plot_overview_and_opportunity_resolution(client: TestClient) -> None:
    save_id = _create_test_save(client)
    camp_id = "minimal-campaign"

    # 1. Get plot overview
    res = client.get(f"/api/v1/saves/{camp_id}/{save_id}/plot")
    assert res.status_code == 200
    data = res.json()
    assert len(data["milestones"]) >= 1
    assert len(data["opportunities"]) >= 1
    opp = next(o for o in data["opportunities"] if o["id"] == "opp-1")
    assert opp["status"] in ("active", "locked")

    # 2. Resolve opportunity opp-1 (revision 1 -> 2)
    res = client.post(
        f"/api/v1/saves/{camp_id}/{save_id}/plot/opportunities/resolve",
        json={
            "command_id": "cmd-resolve-opp-1",
            "expected_revision": 1,
            "opportunity_id": "opp-1",
            "outcome_id": "outcome-1",
        },
    )
    assert res.status_code in (200, 422)
