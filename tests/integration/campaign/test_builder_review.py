"""Integration tests for DraftReviewService (BUILD-07)."""

import datetime
from pathlib import Path
from typing import Any

import pytest

from campaign.builder import BuilderBrief, create_initial_draft_state
from campaign.builder.review import DraftReviewService
from campaign.storage.drafts import DraftRepository, DraftRevisionConflictError
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


def _make_valid_stage1_dict() -> dict[str, Any]:
    meta = CampaignMeta(
        schema_version=1,
        campaign_id=EntityId("camp-review-test"),
        campaign_version=SemanticVersion("1.0.0"),
        title="Review Realm",
        theme=Theme.FANTASY,
        source_type=SourceType.PROMPT,
        source_summary="A world under review.",
        default_difficulty=DefaultDifficulty.NORMAL,
        campaign_length=CampaignLength.MEDIUM,
        art_style_ref=EntityId("style-review-test"),
        created_at=datetime.datetime.now(datetime.UTC),
        status=CampaignStatus.DRAFT,
    )
    style = StyleBibleFile(
        schema_version=1,
        campaign_id=EntityId("camp-review-test"),
        campaign_version=SemanticVersion("1.0.0"),
        style_bible=StyleBible(
            style_id=EntityId("style-review-test"),
            tone="Grounded and serious",
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
        request_id="req-review-1",
        stage="meta_style",
        meta=meta,
        style=style,
    )
    return resp.model_dump(mode="json")


def test_edit_stage_artifact_valid(tmp_path: Path) -> None:
    repo = DraftRepository(tmp_path)
    service = DraftReviewService(repo)

    brief = BuilderBrief(title="Review Realm", premise="A kingdom.")
    draft = create_initial_draft_state(EntityId("draft-review-1"), brief)
    repo.save_draft(draft)

    valid_dict = _make_valid_stage1_dict()
    updated_draft, diags = service.edit_stage_artifact(
        "draft-review-1", "meta_style", valid_dict, expected_revision=1
    )

    assert len(diags) == 0
    assert updated_draft.stages["meta_style"].status == "valid"
    assert updated_draft.revision == 2


def test_edit_stage_artifact_invalid_schema(tmp_path: Path) -> None:
    repo = DraftRepository(tmp_path)
    service = DraftReviewService(repo)

    brief = BuilderBrief(title="Review Realm", premise="A kingdom.")
    draft = create_initial_draft_state(EntityId("draft-review-2"), brief)
    repo.save_draft(draft)

    invalid_dict = {"invalid": "payload"}
    updated_draft, diags = service.edit_stage_artifact(
        "draft-review-2", "meta_style", invalid_dict, expected_revision=1
    )

    assert len(diags) > 0
    assert updated_draft.stages["meta_style"].status == "invalid"


def test_edit_stage_artifact_revision_conflict(tmp_path: Path) -> None:
    repo = DraftRepository(tmp_path)
    service = DraftReviewService(repo)

    brief = BuilderBrief(title="Review Realm", premise="A kingdom.")
    draft = create_initial_draft_state(EntityId("draft-review-3"), brief)
    repo.save_draft(draft)

    valid_dict = _make_valid_stage1_dict()
    with pytest.raises(DraftRevisionConflictError):
        service.edit_stage_artifact(
            "draft-review-3", "meta_style", valid_dict, expected_revision=99
        )


def test_validate_draft_incomplete(tmp_path: Path) -> None:
    repo = DraftRepository(tmp_path)
    service = DraftReviewService(repo)

    brief = BuilderBrief(title="Review Realm", premise="A kingdom.")
    draft = create_initial_draft_state(EntityId("draft-review-4"), brief)
    repo.save_draft(draft)

    report = service.validate_draft("draft-review-4")
    assert report.is_valid is False
    assert report.is_publish_ready is False
    assert any(d.code in ("MISSING_STAGE", "STAGE_NOT_STARTED") for d in report.errors)
