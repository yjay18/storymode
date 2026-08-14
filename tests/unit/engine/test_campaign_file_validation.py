"""Tests for campaign file validation."""

import json

from engine.validation.campaign_files import validate_campaign_files


def test_missing_and_extra_files() -> None:
    # Empty contents
    pack, diagnostics = validate_campaign_files({})
    assert pack is None
    assert len(diagnostics) == 10
    assert all(d.code == "file_missing" for d in diagnostics)

    # Extra file
    pack, diagnostics = validate_campaign_files({"extra.json": "{}"})
    assert pack is None
    assert any(d.code == "file_extra" and d.file == "extra.json" for d in diagnostics)


def test_malformed_root() -> None:
    # Provide arrays instead of dicts for all required files to bypass missing checks
    # but fail the type check
    file_contents = dict.fromkeys(["campaign.json", "style.json", "world.json", "areas.json", "characters.json", "skills.json", "items.json", "enemies.json", "plot.json", "balance.json"], "[]")

    pack, diagnostics = validate_campaign_files(file_contents)
    assert pack is None
    assert len(diagnostics) == 10
    assert all(d.code == "model_type" for d in diagnostics)


def test_pydantic_errors_collected() -> None:
    # Provide empty dicts for all required files, triggering Pydantic ValidationErrors
    file_contents = dict.fromkeys(["campaign.json", "style.json", "world.json", "areas.json", "characters.json", "skills.json", "items.json", "enemies.json", "plot.json", "balance.json"], "{}")

    pack, diagnostics = validate_campaign_files(file_contents)
    assert pack is None
    # Just asserting it collected multiple errors from Pydantic
    assert len(diagnostics) > 10
    assert any(d.code == "missing" for d in diagnostics)

    # Ensure diagnostics are sorted
    sorted_diagnostics = sorted(diagnostics)
    assert diagnostics == sorted_diagnostics


def test_mismatched_campaign_version() -> None:
    from domain.models.campaign_meta import (
        CampaignLength,
        CampaignMeta,
        CampaignStatus,
        DefaultDifficulty,
        SourceType,
        Theme,
    )
    from domain.models.style_bible import StyleBibleFile

    meta = {
        "schema_version": 1,
        "campaign_id": "test-camp",
        "campaign_version": "1.0.0",
        "title": "Test",
        "theme": Theme.CUSTOM,
        "source_type": SourceType.CUSTOM,
        "source_summary": "x",
        "default_difficulty": DefaultDifficulty.NORMAL,
        "campaign_length": CampaignLength.SHORT,
        "art_style_ref": "style-1",
        "created_at": __import__("datetime").datetime.now(__import__("datetime").UTC),
        "content_fingerprint": None,
        "status": CampaignStatus.DRAFT,
    }

    style = {
        "schema_version": 1,
        "campaign_id": "test-camp",
        "campaign_version": "1.0.1",  # MISMATCH
        "style_bible": {
            "style_id": "style-1",
            "tone": "x",
            "narrative_voice": "x",
            "sensory_palette": {
                "sounds": ["x"],
                "smells": ["x"],
                "materials": ["x"],
                "lighting": ["x"],
                "textures": ["x"],
            },
            "faction_language_notes": "x",
            "naming_conventions": "x",
            "banned_phrases": [],
            "description_requirements": "x",
            "examples": ["ex"],
            "anti_examples": ["anti"],
            "art_direction": "x",
        },
    }

    from unittest.mock import patch

    with patch(
        "engine.validation.campaign_files.REQUIRED_FILES",
        {"campaign.json": CampaignMeta, "style.json": StyleBibleFile},
    ):
        pack, diagnostics = validate_campaign_files({
            "campaign.json": json.dumps(meta, default=str),
            "style.json": json.dumps(style, default=str)
        })

        assert pack is None
        assert len(diagnostics) == 1
        assert diagnostics[0].code == "mismatched_campaign_version"
        assert diagnostics[0].file == "style.json"


def test_mismatched_campaign_id() -> None:
    from unittest.mock import patch

    from domain.models.campaign_meta import (
        CampaignLength,
        CampaignMeta,
        CampaignStatus,
        DefaultDifficulty,
        SourceType,
        Theme,
    )
    from domain.models.style_bible import StyleBibleFile

    meta = {
        "schema_version": 1,
        "campaign_id": "test-camp",
        "campaign_version": "1.0.0",
        "title": "Test",
        "theme": Theme.CUSTOM,
        "source_type": SourceType.CUSTOM,
        "source_summary": "x",
        "default_difficulty": DefaultDifficulty.NORMAL,
        "campaign_length": CampaignLength.SHORT,
        "art_style_ref": "style-1",
        "created_at": __import__("datetime").datetime.now(__import__("datetime").UTC),
        "content_fingerprint": None,
        "status": CampaignStatus.DRAFT,
    }

    style = {
        "schema_version": 1,
        "campaign_id": "other-camp",  # MISMATCH
        "campaign_version": "1.0.0",
        "style_bible": {
            "style_id": "style-1",
            "tone": "x",
            "narrative_voice": "x",
            "sensory_palette": {
                "sounds": ["x"],
                "smells": ["x"],
                "materials": ["x"],
                "lighting": ["x"],
                "textures": ["x"],
            },
            "faction_language_notes": "x",
            "naming_conventions": "x",
            "banned_phrases": [],
            "description_requirements": "x",
            "examples": ["ex"],
            "anti_examples": ["anti"],
            "art_direction": "x",
        },
    }

    with patch(
        "engine.validation.campaign_files.REQUIRED_FILES",
        {"campaign.json": CampaignMeta, "style.json": StyleBibleFile},
    ):
        pack, diagnostics = validate_campaign_files({
            "campaign.json": json.dumps(meta, default=str),
            "style.json": json.dumps(style, default=str)
        })

        assert pack is None
        assert len(diagnostics) == 1
        assert diagnostics[0].code == "mismatched_campaign_id"
        assert diagnostics[0].file == "style.json"
