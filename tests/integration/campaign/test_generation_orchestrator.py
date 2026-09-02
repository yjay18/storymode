"""Integration tests for campaign generation orchestrator and stage repair (BUILD-06)."""

import datetime
import json
from pathlib import Path

import httpx
import pytest

from campaign.builder import BuilderBrief, create_initial_draft_state
from campaign.builder.review import DraftReviewService
from campaign.generation import GenerationOrchestrator, StageRunner
from campaign.storage.drafts import DraftRepository
from campaign.storage.publisher import CampaignPublisher
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
from engine.campaign import load_campaign
from llm.contracts.campaign_generation import MetaStyleStageResponse
from llm.ollama_client import OllamaClient

_SALT_LEDGER = Path(__file__).resolve().parents[3] / "campaigns" / "salt-ledger"


def _salt(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads((_SALT_LEDGER / name).read_text(encoding="utf-8"))
    return data


def _wrap(stage: str, **payload: object) -> str:
    return json.dumps(
        {
            "contract_version": 1,
            "prompt_version": f"campaign-{stage}/1.0.0",
            "request_id": f"req-{stage}",
            "stage": stage,
            **payload,
        }
    )


def _all_stage_responses() -> list[str]:
    """Wrap the hand-authored salt-ledger pack into one response per model stage."""
    meta = _salt("campaign.json")
    meta["status"] = "draft"
    meta.pop("content_fingerprint", None)
    return [
        _wrap("meta_style", meta=meta, style=_salt("style.json")),
        _wrap("rules", world=_salt("world.json")),
        _wrap("areas", areas=_salt("areas.json")),
        _wrap("plot", plot=_salt("plot.json")),
        _wrap("characters", characters=_salt("characters.json")),
        _wrap("skills", skills=_salt("skills.json")),
        _wrap("items_enemies", items=_salt("items.json"), enemies=_salt("enemies.json")),
        _wrap("balance", balance=_salt("balance.json")),
    ]


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


@pytest.mark.anyio
async def test_generate_all_stages_publishes_a_loadable_pack(tmp_path: Path) -> None:
    """The split pipeline (incl. items_enemies + balance) yields a publishable pack."""
    draft_repo = DraftRepository(tmp_path / "drafts")
    brief = BuilderBrief(title="Salt Ledger", premise="A drowned trade city.")
    draft = create_initial_draft_state(EntityId("draft-all"), brief)
    draft_repo.save_draft(draft)

    responses = _all_stage_responses()
    call_index = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_index
        content = responses[call_index]
        call_index += 1
        return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    ollama_client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    runner = StageRunner(ollama_client, draft_repo)
    orchestrator = GenerationOrchestrator(runner, draft_repo)

    result = await orchestrator.generate_all("draft-all")

    assert call_index == 8, "expected exactly one model call per generation stage"
    for name in ("skills", "items_enemies", "balance", "review"):
        assert result.stages[name].status == "valid", name

    review_service = DraftReviewService(draft_repo)
    assert review_service.validate_draft("draft-all").is_publish_ready

    publisher = CampaignPublisher(tmp_path / "campaigns", draft_repo, review_service)
    published = publisher.publish_draft("draft-all", confirmed=True)

    pack, diagnostics = load_campaign(Path(published.campaign_dir))
    assert pack is not None, diagnostics


def test_legacy_four_key_skills_artifact_migrates_on_load(tmp_path: Path) -> None:
    """A pre-PLAY-05 draft with items/enemies/balance in the skills stage splits on load."""
    draft_repo = DraftRepository(tmp_path / "drafts")
    brief = BuilderBrief(title="Legacy", premise="Old draft.")
    draft = create_initial_draft_state(EntityId("draft-legacy"), brief)
    saved = draft_repo.save_draft(draft)

    # Simulate a draft.json written before the split: one skills stage holding four keys.
    legacy = json.loads(json.dumps(saved.model_dump(mode="json")))
    legacy["stages"] = {
        k: v for k, v in legacy["stages"].items() if k not in ("items_enemies", "balance")
    }
    legacy["stages"]["skills"] = {
        "stage": "skills",
        "status": "valid",
        "attempts": 3,
        "diagnostics": [],
        "artifact_data": {
            "contract_version": 1,
            "prompt_version": "campaign-skills/1.0.0",
            "request_id": "req-old",
            "stage": "skills",
            "skills": _salt("skills.json"),
            "items": _salt("items.json"),
            "enemies": _salt("enemies.json"),
            "balance": _salt("balance.json"),
        },
    }
    draft_file = draft_repo._resolve_draft_dir("draft-legacy") / "draft.json"
    draft_file.write_text(json.dumps(legacy), encoding="utf-8")

    migrated = draft_repo.load_draft("draft-legacy")

    assert migrated.stages["skills"].artifact_data is not None
    assert set(migrated.stages["skills"].artifact_data) >= {"stage", "skills"}
    assert "items" not in migrated.stages["skills"].artifact_data
    assert migrated.stages["items_enemies"].status == "valid"
    assert migrated.stages["items_enemies"].artifact_data is not None
    assert "enemies" in migrated.stages["items_enemies"].artifact_data
    assert migrated.stages["balance"].artifact_data is not None
    assert "balance" in migrated.stages["balance"].artifact_data
