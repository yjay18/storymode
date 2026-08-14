"""Integration tests for exploration action API endpoints."""

import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_action_interpreter, get_random_source
from app.main import create_app
from engine.actions.protocols import ActionInterpreter
from engine.dice.testing import ScriptedRandomSource
from llm.contracts.action import ActionProposal, EntityMention


class FakeActionInterpreter(ActionInterpreter):
    """Deterministic fake interpreter for testing."""

    def __init__(
        self,
        proposal_map: dict[str, ActionProposal] | None = None,
        default_proposal: ActionProposal | None = None,
    ) -> None:
        self.proposal_map = proposal_map or {}
        self.default_proposal = default_proposal

    def interpret(
        self,
        player_text: str,
        candidates: Any = None,
    ) -> ActionProposal:
        if player_text in self.proposal_map:
            return self.proposal_map[player_text]
        if self.default_proposal:
            return self.default_proposal
        raise ValueError(f"No fake proposal for text: {player_text}")


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
    assert resp.status_code == 201
    save_id = resp.json()["save_id"]
    return client, "minimal-campaign", save_id, app


def test_submit_action_without_interpreter_returns_503(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, _app = client_and_save

    resp = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-1",
            "expected_revision": 1,
            "player_text": "look around",
        },
    )
    assert resp.status_code == 503
    data = resp.json()
    assert data["error"]["code"] == "interpreter_not_configured"


def test_submit_action_with_fake_interpreter_direct_inspect(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, app = client_and_save

    fake_proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-1",
        status="valid",
        operation="inspect",
        verb="look",
        intended_effect="look at the wooden crate",
        challenge_label="none",
        stakes=[],
        entity_mentions=[EntityMention(text="Object", role="target", candidate_ordinal=None)],
        capability_mentions=[],
    )
    fake_interpreter = FakeActionInterpreter(default_proposal=fake_proposal)
    app.dependency_overrides[get_action_interpreter] = lambda: fake_interpreter

    resp = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-1",
            "expected_revision": 1,
            "player_text": "inspect the crate",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["revision"] == 2
    assert data["has_pending_check"] is False
    assert data["pending_check"] is None


def test_submit_action_creates_pending_check_and_resolves(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, app = client_and_save

    fake_proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-2",
        status="valid",
        operation="inspect",
        verb="force",
        intended_effect="force open the crate",
        challenge_label="standard",
        stakes=["fail"],
        entity_mentions=[EntityMention(text="Object", role="target", candidate_ordinal=None)],
        capability_mentions=[],
    )
    fake_interpreter = FakeActionInterpreter(default_proposal=fake_proposal)
    app.dependency_overrides[get_action_interpreter] = lambda: fake_interpreter

    # 1. Submit action
    resp = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-2",
            "expected_revision": 1,
            "player_text": "force open the crate",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["revision"] == 2
    assert data["has_pending_check"] is True
    assert data["pending_check"] is not None

    # 2. Resolve check with scripted RNG (roll 15)
    app.dependency_overrides[get_random_source] = lambda: ScriptedRandomSource([15])

    res_resp = client.post(
        "/api/v1/actions/resolve-check",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-resolve",
            "expected_revision": 2,
            "use_luck": False,
        },
    )
    assert res_resp.status_code == 200
    res_data = res_resp.json()
    assert res_data["revision"] == 3
    assert res_data["roll"] == 15
    assert res_data["band"] == "strong"

    # 3. Verify state reloaded
    save_resp = client.get(f"/api/v1/saves/{campaign_id}/{save_id}")
    assert save_resp.status_code == 200
    assert save_resp.json()["revision"] == 3


def test_submit_action_cancel_check(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, app = client_and_save

    fake_proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-2",
        status="valid",
        operation="inspect",
        verb="force",
        intended_effect="force open the crate",
        challenge_label="standard",
        stakes=["fail"],
        entity_mentions=[EntityMention(text="Object", role="target", candidate_ordinal=None)],
        capability_mentions=[],
    )
    fake_interpreter = FakeActionInterpreter(default_proposal=fake_proposal)
    app.dependency_overrides[get_action_interpreter] = lambda: fake_interpreter

    # 1. Submit action
    resp = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-cancel-init",
            "expected_revision": 1,
            "player_text": "force open the crate",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["has_pending_check"] is True

    # 2. Cancel check
    cancel_resp = client.post(
        "/api/v1/actions/cancel-check",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-cancel",
            "expected_revision": 2,
        },
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["revision"] == 3


def test_stale_revision_returns_409(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, app = client_and_save

    fake_proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-1",
        status="valid",
        operation="inspect",
        verb="look",
        intended_effect="look",
        challenge_label="none",
        stakes=[],
        entity_mentions=[EntityMention(text="Object", role="target", candidate_ordinal=None)],
        capability_mentions=[],
    )
    fake_interpreter = FakeActionInterpreter(default_proposal=fake_proposal)
    app.dependency_overrides[get_action_interpreter] = lambda: fake_interpreter

    resp = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-stale",
            "expected_revision": 999,
            "player_text": "look",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


def test_invalid_target_returns_422(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, app = client_and_save

    fake_proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-1",
        status="valid",
        operation="inspect",
        verb="look",
        intended_effect="look",
        challenge_label="none",
        stakes=[],
        entity_mentions=[
            EntityMention(text="NonExistentMonster", role="target", candidate_ordinal=None)
        ],
        capability_mentions=[],
    )
    fake_interpreter = FakeActionInterpreter(default_proposal=fake_proposal)
    app.dependency_overrides[get_action_interpreter] = lambda: fake_interpreter

    resp = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-err",
            "expected_revision": 1,
            "player_text": "look",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_resolve_check_without_pending_returns_422(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, _app = client_and_save

    resp = client.post(
        "/api/v1/actions/resolve-check",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-resolve-nopending",
            "expected_revision": 1,
            "use_luck": False,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_cancel_check_without_pending_returns_422(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, _app = client_and_save

    resp = client.post(
        "/api/v1/actions/cancel-check",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-cancel-nopending",
            "expected_revision": 1,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_submit_action_idempotent_duplicate_command(
    client_and_save: tuple[TestClient, str, str, FastAPI],
) -> None:
    client, campaign_id, save_id, app = client_and_save

    fake_proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-1",
        status="valid",
        operation="inspect",
        verb="look",
        intended_effect="look at object",
        challenge_label="none",
        stakes=[],
        entity_mentions=[EntityMention(text="Object", role="target", candidate_ordinal=None)],
        capability_mentions=[],
    )
    fake_interpreter = FakeActionInterpreter(default_proposal=fake_proposal)
    app.dependency_overrides[get_action_interpreter] = lambda: fake_interpreter

    # First call
    resp1 = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-idem-1",
            "expected_revision": 1,
            "player_text": "look at object",
        },
    )
    assert resp1.status_code == 200
    assert resp1.json()["revision"] == 2

    # Duplicate call with same command_id and revision 2
    resp2 = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": campaign_id,
            "save_id": save_id,
            "command_id": "cmd-idem-1",
            "expected_revision": 2,
            "player_text": "look at object",
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["revision"] == 2
