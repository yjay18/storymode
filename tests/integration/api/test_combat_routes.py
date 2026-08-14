"""Integration tests for combat API endpoints."""

import shutil
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_random_source
from app.main import create_app
from engine.dice.testing import ScriptedRandomSource


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Path:
    """Setup a temporary campaigns directory with valid minimal campaign."""
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir(parents=True)

    fixture_src = Path(__file__).parent.parent.parent / "fixtures" / "campaigns" / "valid-minimal"
    target_camp = campaigns_dir / "minimal-campaign"
    shutil.copytree(fixture_src, target_camp)

    return campaigns_dir


@pytest.fixture
def client_and_save(temp_campaigns_dir: Path) -> tuple[TestClient, str, str, FastAPI]:
    settings = Settings(
        campaigns_dir=str(temp_campaigns_dir.parent),
        storymode_env="test",
    )
    app = create_app(settings)
    app.dependency_overrides[get_random_source] = lambda: ScriptedRandomSource([10, 15, 20])
    client = TestClient(app)

    # Create a valid save
    resp = client.post(
        "/api/v1/saves",
        json={
            "campaign_id": "minimal-campaign",
            "command_id": "cmd-init",
            "slot_name": "Test Save",
            "slot_kind": "manual",
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
    assert resp.status_code == 201, resp.text
    save_id = resp.json()["save_id"]
    return client, "minimal-campaign", save_id, app


def test_start_combat_and_view(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, _ = client_and_save

    # 1. Start combat
    start_resp = client.post(
        "/api/v1/combat/start",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "encounter_id": "encounter-1",
            "command_id": "cmd-start-1",
            "expected_revision": 1,
        },
    )
    assert start_resp.status_code == 200, start_resp.text
    data = start_resp.json()
    assert data["save_id"] == save_id
    assert data["revision"] == 2
    assert data["combat"] is not None
    assert data["combat"]["phase"] == "active"
    assert len(data["allowed_actions"]) > 0

    # 2. Get combat view
    view_resp = client.get(
        f"/api/v1/combat/view?campaign_id={campaign_id}&save_id={save_id}",
    )
    assert view_resp.status_code == 200, view_resp.text
    view_data = view_resp.json()
    assert view_data["revision"] == 2
    assert view_data["combat"] is not None
    assert len(view_data["allowed_actions"]) > 0


def test_combat_defend_endpoint(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, _ = client_and_save

    # Start combat
    start_resp = client.post(
        "/api/v1/combat/start",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "encounter_id": "encounter-1",
            "command_id": "cmd-start-1",
            "expected_revision": 1,
        },
    )
    assert start_resp.status_code == 200, start_resp.text

    # Defend
    defend_resp = client.post(
        "/api/v1/combat/defend",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-defend-1",
            "expected_revision": 2,
        },
    )
    assert defend_resp.status_code == 200, defend_resp.text
    data = defend_resp.json()
    assert data["revision"] == 3


def test_combat_revision_conflict(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, _ = client_and_save

    # Start combat with wrong expected revision
    resp = client.post(
        "/api/v1/combat/start",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "encounter_id": "encounter-1",
            "command_id": "cmd-start-1",
            "expected_revision": 999,
        },
    )
    assert resp.status_code == 409
    assert "revision conflict" in resp.json()["error"]["message"]


def test_combat_injected_extra_fields_rejected(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, _ = client_and_save

    # Attempt to inject damage in request body
    resp = client.post(
        "/api/v1/combat/defend",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-defend-1",
            "expected_revision": 1,
            "injected_damage": 999,
        },
    )
    assert resp.status_code == 422


def test_combat_idempotency_endpoint(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, _ = client_and_save

    # Start combat
    resp1 = client.post(
        "/api/v1/combat/start",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "encounter_id": "encounter-1",
            "command_id": "cmd-start-1",
            "expected_revision": 1,
        },
    )
    assert resp1.status_code == 200

    # Repeat exact same request with same command_id
    resp2 = client.post(
        "/api/v1/combat/start",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "encounter_id": "encounter-1",
            "command_id": "cmd-start-1",
            "expected_revision": 1,
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["revision"] == resp1.json()["revision"]


def test_combat_skill_and_yield_endpoints(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, _ = client_and_save

    # Start combat
    start_resp = client.post(
        "/api/v1/combat/start",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "encounter_id": "encounter-1",
            "command_id": "cmd-start-1",
            "expected_revision": 1,
        },
    )
    assert start_resp.status_code == 200
    target_id = start_resp.json()["allowed_actions"][0]["valid_target_ids"][0]

    # Use skill
    skill_resp = client.post(
        "/api/v1/combat/skill",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "skill_id": "skill-1",
            "target_ids": [target_id],
            "command_id": "cmd-skill-1",
            "expected_revision": 2,
        },
    )
    assert skill_resp.status_code == 200, skill_resp.text
    assert skill_resp.json()["revision"] == 3

    # Yield
    yield_resp = client.post(
        "/api/v1/combat/yield",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-yield-1",
            "expected_revision": 3,
        },
    )
    assert yield_resp.status_code == 200, yield_resp.text
    assert yield_resp.json()["is_terminal"] is True
    assert yield_resp.json()["outcome"] == "Yielded"
    assert yield_resp.json()["combat"] is None
