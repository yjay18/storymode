"""Contract tests for campaign generation LLM responses (BUILD-04)."""

import datetime

import pytest
from pydantic import ValidationError

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


def _make_valid_meta() -> CampaignMeta:
    return CampaignMeta(
        schema_version=1,
        campaign_id=EntityId("camp-test"),
        campaign_version=SemanticVersion("1.0.0"),
        title="Test Campaign",
        theme=Theme.FANTASY,
        source_type=SourceType.PROMPT,
        source_summary="A brief summary.",
        default_difficulty=DefaultDifficulty.NORMAL,
        campaign_length=CampaignLength.MEDIUM,
        art_style_ref=EntityId("style-test"),
        created_at=datetime.datetime.now(datetime.UTC),
        status=CampaignStatus.DRAFT,
    )


def _make_valid_style() -> StyleBibleFile:
    return StyleBibleFile(
        schema_version=1,
        campaign_id=EntityId("camp-test"),
        campaign_version=SemanticVersion("1.0.0"),
        style_bible=StyleBible(
            style_id=EntityId("style-test"),
            tone="Dark and gritty",
            narrative_voice="Third-person limited",
            sensory_palette=SensoryPalette(
                sounds=["wind howling"],
                smells=["pine smoke"],
                materials=["rough granite"],
                lighting=["dim torchlight"],
                textures=["coarse wool"],
            ),
            faction_language_notes="Terse northern slang",
            naming_conventions="Old Norse roots",
            banned_phrases=["suddenly", "a sense of dread"],
            description_requirements="Sensory first",
            examples=["The frost crunched under his boots."],
            anti_examples=["Suddenly he was very scared."],
            art_direction="Painterly fantasy",
        ),
    )


def test_meta_style_stage_response_valid() -> None:
    meta = _make_valid_meta()
    style = _make_valid_style()

    resp = MetaStyleStageResponse(
        contract_version=1,
        prompt_version="campaign-meta_style/1.0.0",
        request_id="req-1",
        stage="meta_style",
        meta=meta,
        style=style,
    )
    assert resp.stage == "meta_style"
    assert resp.meta.campaign_id == "camp-test"


def test_meta_style_stage_response_rejects_published_status() -> None:
    meta = _make_valid_meta().model_copy(
        update={"status": CampaignStatus.PUBLISHED, "content_fingerprint": "a" * 64}
    )
    style = _make_valid_style()

    with pytest.raises(ValidationError):
        MetaStyleStageResponse(
            contract_version=1,
            prompt_version="campaign-meta_style/1.0.0",
            request_id="req-1",
            stage="meta_style",
            meta=meta,
            style=style,
        )


def test_meta_style_stage_response_rejects_fingerprint_in_draft() -> None:
    meta = _make_valid_meta().model_copy(update={"content_fingerprint": "a" * 64})
    style = _make_valid_style()

    with pytest.raises(ValidationError):
        MetaStyleStageResponse(
            contract_version=1,
            prompt_version="campaign-meta_style/1.0.0",
            request_id="req-1",
            stage="meta_style",
            meta=meta,
            style=style,
        )
