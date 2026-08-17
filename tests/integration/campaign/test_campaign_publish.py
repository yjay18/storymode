"""Integration tests for CampaignPublisher (BUILD-08)."""

import json
from pathlib import Path

import pytest

from campaign.builder import BuilderBrief, create_initial_draft_state
from campaign.builder.models import DraftStageState, DraftState
from campaign.builder.review import DraftReviewService
from campaign.storage.drafts import DraftRepository
from campaign.storage.publisher import (
    CampaignAlreadyExistsError,
    CampaignPublisher,
    InvalidDraftPublishError,
    UnconfirmedPublishError,
)
from domain.models.common import EntityId
from engine.campaign import load_campaign


def _build_full_valid_draft(draft_id: EntityId) -> DraftState:
    """Build a complete valid draft using fixture files."""
    fixtures_dir = Path("tests/fixtures/campaigns/valid-minimal")
    brief = BuilderBrief(title="Minimal Realm", premise="A valid minimal world.")
    draft = create_initial_draft_state(draft_id, brief)

    stages = dict(draft.stages)

    # meta_style
    meta_json = json.loads((fixtures_dir / "campaign.json").read_text(encoding="utf-8"))
    meta_json["status"] = "draft"
    meta_json.pop("content_fingerprint", None)
    style_json = json.loads((fixtures_dir / "style.json").read_text(encoding="utf-8"))
    stages["meta_style"] = DraftStageState(
        stage="meta_style",
        status="valid",
        artifact_data={"meta": meta_json, "style": style_json},
    )

    # rules
    world_json = json.loads((fixtures_dir / "world.json").read_text(encoding="utf-8"))
    stages["rules"] = DraftStageState(
        stage="rules",
        status="valid",
        artifact_data={"world": world_json},
    )

    # areas
    areas_json = json.loads((fixtures_dir / "areas.json").read_text(encoding="utf-8"))
    stages["areas"] = DraftStageState(
        stage="areas",
        status="valid",
        artifact_data={"areas": areas_json},
    )

    # plot
    plot_json = json.loads((fixtures_dir / "plot.json").read_text(encoding="utf-8"))
    stages["plot"] = DraftStageState(
        stage="plot",
        status="valid",
        artifact_data={"plot": plot_json},
    )

    # characters
    chars_json = json.loads((fixtures_dir / "characters.json").read_text(encoding="utf-8"))
    stages["characters"] = DraftStageState(
        stage="characters",
        status="valid",
        artifact_data={"characters": chars_json},
    )

    # skills
    skills_json = json.loads((fixtures_dir / "skills.json").read_text(encoding="utf-8"))
    items_json = json.loads((fixtures_dir / "items.json").read_text(encoding="utf-8"))
    enemies_json = json.loads((fixtures_dir / "enemies.json").read_text(encoding="utf-8"))
    balance_json = json.loads((fixtures_dir / "balance.json").read_text(encoding="utf-8"))
    stages["skills"] = DraftStageState(
        stage="skills",
        status="valid",
        artifact_data={
            "skills": skills_json,
            "items": items_json,
            "enemies": enemies_json,
            "balance": balance_json,
        },
    )

    # review
    stages["review"] = DraftStageState(stage="review", status="valid")

    return draft.model_copy(update={"stages": stages})


def test_publish_unconfirmed_fails(tmp_path: Path) -> None:
    draft_repo = DraftRepository(tmp_path)
    review_svc = DraftReviewService(draft_repo)
    publisher = CampaignPublisher(tmp_path / "campaigns", draft_repo, review_svc)

    draft = _build_full_valid_draft(EntityId("draft-pub-1"))
    draft_repo.save_draft(draft)

    with pytest.raises(UnconfirmedPublishError):
        publisher.publish_draft("draft-pub-1", confirmed=False)


def test_publish_incomplete_draft_fails(tmp_path: Path) -> None:
    draft_repo = DraftRepository(tmp_path)
    review_svc = DraftReviewService(draft_repo)
    publisher = CampaignPublisher(tmp_path / "campaigns", draft_repo, review_svc)

    brief = BuilderBrief(title="Incomplete", premise="Not done.")
    draft = create_initial_draft_state(EntityId("draft-pub-2"), brief)
    draft_repo.save_draft(draft)

    with pytest.raises(InvalidDraftPublishError):
        publisher.publish_draft("draft-pub-2", confirmed=True)


def test_publish_success(tmp_path: Path) -> None:
    draft_repo = DraftRepository(tmp_path)
    review_svc = DraftReviewService(draft_repo)
    campaigns_dir = tmp_path / "campaigns"
    publisher = CampaignPublisher(campaigns_dir, draft_repo, review_svc)

    draft = _build_full_valid_draft(EntityId("draft-pub-3"))
    draft_repo.save_draft(draft)

    result = publisher.publish_draft("draft-pub-3", confirmed=True)

    assert result.campaign_id == "minimal-campaign"
    assert result.campaign_dir.exists()
    assert len(result.fingerprint) == 64

    # Verify published pack loads directly from engine loader
    pack, diags = load_campaign(result.campaign_dir)
    assert pack is not None
    assert len(diags) == 0
    assert pack.meta.status == "published"
    assert pack.meta.content_fingerprint == result.fingerprint

    # Verify draft state marked is_published
    updated_draft = draft_repo.load_draft("draft-pub-3")
    assert updated_draft.is_published is True
    assert updated_draft.published_campaign_id == "minimal-campaign"


def test_publish_already_exists_fails(tmp_path: Path) -> None:
    draft_repo = DraftRepository(tmp_path)
    review_svc = DraftReviewService(draft_repo)
    campaigns_dir = tmp_path / "campaigns"
    publisher = CampaignPublisher(campaigns_dir, draft_repo, review_svc)

    draft = _build_full_valid_draft(EntityId("draft-pub-4"))
    draft_repo.save_draft(draft)

    # First publication succeeds
    publisher.publish_draft("draft-pub-4", confirmed=True)

    # Second publication with same ID fails
    draft2 = _build_full_valid_draft(EntityId("draft-pub-5"))
    draft_repo.save_draft(draft2)

    with pytest.raises(CampaignAlreadyExistsError):
        publisher.publish_draft("draft-pub-5", confirmed=True)
