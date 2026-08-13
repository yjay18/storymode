"""Tests for campaign meta and style bible models."""

import datetime
from typing import Any

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
from domain.models.style_bible import SensoryPalette, StyleBible, StyleBibleFile


def make_valid_meta(status: CampaignStatus = CampaignStatus.DRAFT) -> dict[str, Any]:
    d = {
        "schema_version": 1,
        "campaign_id": "test-campaign",
        "campaign_version": "1.0.0",
        "title": "A Great Campaign",
        "theme": Theme.FANTASY,
        "source_type": SourceType.PROMPT,
        "source_summary": "A brief summary.",
        "default_difficulty": DefaultDifficulty.NORMAL,
        "campaign_length": CampaignLength.MEDIUM,
        "art_style_ref": "style-01",
        "created_at": datetime.datetime.now(datetime.UTC),
        "status": status,
    }
    if status == CampaignStatus.PUBLISHED:
        d["content_fingerprint"] = "a" * 64
    return d


def test_meta_valid_draft() -> None:
    meta = CampaignMeta(**make_valid_meta(CampaignStatus.DRAFT))
    assert meta.status == CampaignStatus.DRAFT
    assert meta.content_fingerprint is None


def test_meta_valid_published() -> None:
    meta = CampaignMeta(**make_valid_meta(CampaignStatus.PUBLISHED))
    assert meta.status == CampaignStatus.PUBLISHED
    assert meta.content_fingerprint == "a" * 64


def test_meta_invalid_fingerprint_draft() -> None:
    data = make_valid_meta(CampaignStatus.DRAFT)
    data["content_fingerprint"] = "a" * 64
    with pytest.raises(ValidationError) as exc:
        CampaignMeta(**data)
    assert "Draft campaigns must not have a content_fingerprint" in str(exc.value)


def test_meta_invalid_fingerprint_published() -> None:
    data = make_valid_meta(CampaignStatus.PUBLISHED)
    del data["content_fingerprint"]
    with pytest.raises(ValidationError) as exc:
        CampaignMeta(**data)
    assert "Published campaigns require a content_fingerprint" in str(exc.value)


def test_meta_fingerprint_format() -> None:
    data = make_valid_meta(CampaignStatus.PUBLISHED)
    data["content_fingerprint"] = "A" * 64  # Uppercase not allowed
    with pytest.raises(ValidationError):
        CampaignMeta(**data)

    data["content_fingerprint"] = "a" * 63  # Too short
    with pytest.raises(ValidationError):
        CampaignMeta(**data)


def test_sensory_palette_non_empty() -> None:
    with pytest.raises(ValidationError):
        SensoryPalette(
            sounds=[],
            smells=["smell"],
            materials=["mat"],
            lighting=["light"],
            textures=["tex"],
        )


def make_valid_style_bible() -> dict[str, Any]:
    return {
        "style_id": "style-01",
        "tone": "Dark",
        "narrative_voice": "First person",
        "sensory_palette": SensoryPalette(
            sounds=["wind"],
            smells=["dust"],
            materials=["stone"],
            lighting=["dim"],
            textures=["rough"],
        ),
        "faction_language_notes": "None",
        "naming_conventions": "Short",
        "banned_phrases": ["suddenly", "in a flash"],
        "description_requirements": "Be brief",
        "examples": ["Example 1"],
        "anti_examples": ["Anti 1"],
        "art_direction": "Grim",
    }


def test_style_bible_valid() -> None:
    bible = StyleBible(**make_valid_style_bible())
    assert bible.style_id == "style-01"


def test_style_bible_examples_bounds() -> None:
    data = make_valid_style_bible()

    # Empty not allowed
    data["examples"] = []
    with pytest.raises(ValidationError):
        StyleBible(**data)

    # More than 5 not allowed
    data["examples"] = ["1", "2", "3", "4", "5", "6"]
    with pytest.raises(ValidationError):
        StyleBible(**data)


def test_style_bible_banned_phrases_case_folding() -> None:
    data = make_valid_style_bible()
    data["banned_phrases"] = ["Apple", "APPLE"]
    with pytest.raises(ValidationError) as exc:
        StyleBible(**data)
    assert "banned_phrases must be unique when case-folded" in str(exc.value)


def test_style_bible_file_valid() -> None:
    file_model = StyleBibleFile(
        campaign_id="test-campaign",
        campaign_version="1.0.0",
        style_bible=StyleBible(**make_valid_style_bible()),
    )
    assert file_model.schema_version == 1
    assert file_model.campaign_id == "test-campaign"
