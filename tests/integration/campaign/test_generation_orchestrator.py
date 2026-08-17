"""Integration tests for campaign generation orchestrator and stage repair (BUILD-06)."""

import datetime
from pathlib import Path

import httpx
import pytest

from campaign.builder import BuilderBrief, create_initial_draft_state
from campaign.generation import GenerationOrchestrator, StageRunner
from campaign.storage.drafts import DraftRepository
from domain.models.campaign_meta import (
    CampaignLength,
    CampaignMeta,
    CampaignStatus,
    DefaultDifficulty,
    SourceType,
    Theme,
)
from domain.models.common import EntityId, SemanticVersion
from domain.models.style_bible import SensoryPalette, StyleBible, StyleBibleFile
from llm.contracts.campaign_generation import MetaStyleStageResponse
from llm.ollama_client import OllamaClient


def _make_valid_stage1_json() -> str:
    meta = CampaignMeta(
        schema_version=1,
        campaign_id=EntityId("camp-gen-test"),
        campaign_version=SemanticVersion("1.0.0"),
        title="Generated Realm",
        theme=Theme.FANTASY,
        source_type=SourceType.PROMPT,
        source_summary="A generated world.",
        default_difficulty=DefaultDifficulty.NORMAL,
        campaign_length=CampaignLength.MEDIUM,
        art_style_ref=EntityId("style-gen-test"),
        created_at=datetime.datetime.now(datetime.UTC),
        status=CampaignStatus.DRAFT,
    )
    style = StyleBibleFile(
        schema_version=1,
        campaign_id=EntityId("camp-gen-test"),
        campaign_version=SemanticVersion("1.0.0"),
        style_bible=StyleBible(
            style_id=EntityId("style-gen-test"),
            tone="Dark and atmospheric",
            narrative_voice="Third-person limited",
            sensory_palette=SensoryPalette(
                sounds=["crackling hearth fire"],
                smells=["cured leather"],
                materials=["rough stone"],
                lighting=["amber lantern glow"],
                textures=["coarse woven wool"],
            ),
            faction_language_notes="Direct phrasing",
            naming_conventions="Grounded Anglo-Saxon",
            banned_phrases=["suddenly"],
            description_requirements="Sensory first",
            examples=["The cold wind bit through his cloak."],
            anti_examples=["Suddenly he was terrified."],
            art_direction="Painterly dark fantasy",
        ),
    )
    resp = MetaStyleStageResponse(
        contract_version=1,
        prompt_version="campaign-meta_style/1.0.0",
        request_id="req-gen-1",
        stage="meta_style",
        meta=meta,
        style=style,
    )
    return resp.model_dump_json()


@pytest.mark.anyio
async def test_stage_runner_successful_generation(tmp_path: Path) -> None:
    draft_repo = DraftRepository(tmp_path)
    brief = BuilderBrief(title="Winterhold", premise="A fortress in the snow.")
    draft = create_initial_draft_state(EntityId("draft-stage-test"), brief)
    draft_repo.save_draft(draft)

    def mock_ollama_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": _make_valid_stage1_json()}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_ollama_handler))
    ollama_client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)

    runner = StageRunner(ollama_client, draft_repo)
    orchestrator = GenerationOrchestrator(runner, draft_repo)

    result_draft = await orchestrator.generate_stage("draft-stage-test", "meta_style")

    assert result_draft.stages["meta_style"].status == "valid"
    assert result_draft.stages["meta_style"].artifact_data is not None
    assert result_draft.stages["meta_style"].artifact_data["meta"]["campaign_id"] == "camp-gen-test"


@pytest.mark.anyio
async def test_stage_runner_repair_on_first_error(tmp_path: Path) -> None:
    draft_repo = DraftRepository(tmp_path)
    brief = BuilderBrief(title="Winterhold", premise="A fortress in the snow.")
    draft = create_initial_draft_state(EntityId("draft-repair-test"), brief)
    draft_repo.save_draft(draft)

    attempt_counter = 0

    def mock_ollama_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt_counter
        attempt_counter += 1
        if attempt_counter == 1:
            # First attempt returns invalid JSON
            return httpx.Response(
                status_code=200,
                json={"message": {"role": "assistant", "content": '{"invalid": "schema"}'}},
            )
        # Second attempt returns repaired valid JSON
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": _make_valid_stage1_json()}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_ollama_handler))
    ollama_client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)

    runner = StageRunner(ollama_client, draft_repo)
    orchestrator = GenerationOrchestrator(runner, draft_repo)

    result_draft = await orchestrator.generate_stage("draft-repair-test", "meta_style")

    assert result_draft.stages["meta_style"].status == "valid"
    assert result_draft.stages["meta_style"].attempts == 2
    assert result_draft.stages["meta_style"].artifact_data is not None


@pytest.mark.anyio
async def test_stage_runner_exhausts_repairs(tmp_path: Path) -> None:
    draft_repo = DraftRepository(tmp_path)
    brief = BuilderBrief(title="Winterhold", premise="A fortress in the snow.")
    draft = create_initial_draft_state(EntityId("draft-exhaust-test"), brief)
    draft_repo.save_draft(draft)

    def mock_ollama_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": '{"bad": "json"}'}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_ollama_handler))
    ollama_client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)

    runner = StageRunner(ollama_client, draft_repo)
    orchestrator = GenerationOrchestrator(runner, draft_repo)

    result_draft = await orchestrator.generate_stage("draft-exhaust-test", "meta_style")

    assert result_draft.stages["meta_style"].status == "invalid"
    assert result_draft.stages["meta_style"].artifact_data is None
    assert len(result_draft.stages["meta_style"].diagnostics) > 0
