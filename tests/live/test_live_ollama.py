"""Opt-in tests against a real local Ollama. Skipped unless ``STORYMODE_LIVE_OLLAMA=1``.

These are the only tests that talk to a model. They prove the prompt contracts survive
contact with the configured local model (``STORYMODE_MODEL_TEXT``) rather than the
in-memory mocks used everywhere else. Run with::

    STORYMODE_LIVE_OLLAMA=1 STORYMODE_MODEL_TEXT=qwen3.5:9b uv run pytest tests/live -q
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from campaign.builder.models import QuickPromptInput
from campaign.builder.normalization import create_initial_draft_state, normalize_quick_prompt
from campaign.generation.orchestrator import GenerationOrchestrator
from campaign.generation.stages import StageRunner
from campaign.storage.drafts import DraftRepository
from domain.models.common import EntityId
from llm.health import normalize_model_name
from llm.ollama_client import OllamaClient
from llm.orchestration.action_interpreter import ActionInterpreter
from llm.orchestration.narrator import NarratorOrchestrator

pytestmark = [
    pytest.mark.live_ollama,
    pytest.mark.skipif(
        os.environ.get("STORYMODE_LIVE_OLLAMA") != "1",
        reason="set STORYMODE_LIVE_OLLAMA=1 to run against a local Ollama",
    ),
]

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "campaigns" / "valid-minimal"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    campaigns_dir = tmp_path / "campaigns"
    shutil.copytree(_FIXTURE, campaigns_dir / "minimal-campaign")
    return Settings(campaigns_dir=str(campaigns_dir))


@pytest.fixture
def ollama(settings: Settings) -> OllamaClient:
    return OllamaClient(
        base_url=settings.ollama_url,
        default_timeout=settings.ollama_timeout_seconds,
        max_response_bytes=settings.ollama_max_response_bytes,
    )


@pytest.mark.anyio
async def test_configured_model_is_installed(settings: Settings, ollama: OllamaClient) -> None:
    installed = {normalize_model_name(m) for m in await ollama.list_models()}
    assert normalize_model_name(settings.model_text) in installed, (
        f"{settings.model_text} not in {sorted(installed)}; run `ollama pull {settings.model_text}`"
    )


def test_interpreter_and_narrator_round_trip(settings: Settings, ollama: OllamaClient) -> None:
    app = create_app(settings)
    model, timeout = settings.model_text, settings.ollama_timeout_seconds
    app.state.action_interpreter = ActionInterpreter(ollama, model, timeout)
    app.state.narrator_orchestrator = NarratorOrchestrator(ollama, model, timeout)
    client = TestClient(app)

    created = client.post(
        "/api/v1/saves",
        json={
            "campaign_id": "minimal-campaign",
            "command_id": "cmd-live-init",
            "slot_name": "Live",
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
    assert created.status_code == 201, created.text
    save_id = created.json()["save_id"]

    submitted = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "command_id": "cmd-live-1",
            # Reference the Object that actually exists in the minimal-campaign fixture so
            # the engine's world-reference validation can resolve the mention.
            "expected_revision": 1,
            "player_text": "I carefully inspect the Object for anything unusual.",
        },
    )
    assert submitted.status_code == 200, submitted.text
    body = submitted.json()
    assert body["revision"] == 2
    assert body["narration"].strip()


@pytest.mark.anyio
async def test_meta_style_stage_produces_valid_artifact(
    settings: Settings, ollama: OllamaClient, tmp_path: Path
) -> None:
    repo = DraftRepository(tmp_path)
    brief = normalize_quick_prompt(
        QuickPromptInput(premise="A lighthouse keeper guards a door that should not exist.")
    )
    repo.save_draft(create_initial_draft_state(EntityId("draft-live"), brief))
    orchestrator = GenerationOrchestrator(StageRunner(ollama, repo, settings.model_text), repo)

    draft = await orchestrator.generate_stage("draft-live", "meta_style")

    stage = draft.stages["meta_style"]
    assert stage.status == "valid", [d.message[:200] for d in stage.diagnostics]
    assert stage.artifact_data is not None
    assert stage.artifact_data["meta"]["status"] == "draft"
