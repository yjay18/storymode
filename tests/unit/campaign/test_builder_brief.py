"""Unit tests for builder brief models and normalization (BUILD-01)."""

import pytest
from pydantic import ValidationError

from campaign.builder import (
    ALL_DRAFT_STAGES,
    BuilderBrief,
    ContentBoundaries,
    QuickPromptInput,
    SourceMetadata,
    create_initial_draft_state,
    normalize_builder_brief,
    normalize_quick_prompt,
)
from domain.models.common import EntityId


def test_builder_brief_creation_and_normalization() -> None:
    brief = BuilderBrief(
        title="  The Ashen   Crown  ",
        premise="  A fallen kingdom surrounded by mist and monsters.  \n\n ",
        campaign_mode="faithful_story",
        custom_prompt="  Follow the young prince's journey.  ",
        genre="  grimdark fantasy ",
        theme=" loyalty and sacrifice ",
        tone=" bleak and atmospheric ",
        length="short",
        difficulty="hardcore",
        content_boundaries=ContentBoundaries(
            excluded_topics=[" gore ", "gore", " torture "],
            content_rating="mature",
            violence_level="gritty",
        ),
        protected_facts=[
            " The Crown is forged of star-iron. ",
            "The Crown is forged of star-iron.",
        ],
    )

    normalized = normalize_builder_brief(brief)
    assert normalized.title == "The Ashen Crown"
    assert normalized.premise == "A fallen kingdom surrounded by mist and monsters."
    assert normalized.campaign_mode == "faithful_story"
    assert normalized.custom_prompt == "Follow the young prince's journey."
    assert normalized.genre == "grimdark fantasy"
    assert normalized.theme == "loyalty and sacrifice"
    assert normalized.tone == "bleak and atmospheric"
    assert normalized.length == "short"
    assert normalized.difficulty == "hardcore"
    assert normalized.content_boundaries.excluded_topics == ["gore", "torture"]
    assert normalized.protected_facts == ["The Crown is forged of star-iron."]


def test_quick_prompt_mapping_and_defaults() -> None:
    quick = QuickPromptInput(
        premise="A lone ranger guards the frozen northern wall against ancient horrors.",
        campaign_mode="custom_prompt",
        custom_prompt="Explore the forgotten tunnels beneath the wall.",
    )

    normalized = normalize_quick_prompt(quick)
    assert normalized.title == "A lone ranger guards the frozen"
    assert (
        normalized.premise
        == "A lone ranger guards the frozen northern wall against ancient horrors."
    )
    assert normalized.campaign_mode == "custom_prompt"
    assert normalized.custom_prompt == "Explore the forgotten tunnels beneath the wall."
    assert normalized.genre == "dark fantasy"
    assert normalized.length == "medium"
    assert normalized.difficulty == "normal"
    assert normalized.source.source_type == "prompt"


def test_builder_brief_validation_errors() -> None:
    with pytest.raises(ValidationError):
        # Premise cannot be empty
        BuilderBrief(title="Test", premise="")

    with pytest.raises(ValidationError):
        # Title cannot be empty
        BuilderBrief(title="", premise="Valid premise")


def test_create_initial_draft_state() -> None:
    brief = BuilderBrief(
        title="Chronicles of Oakhaven",
        premise="A quiet village discovers an ancient ruin beneath the town well.",
        campaign_mode="llm_decide",
        source=SourceMetadata(source_type="epub", title="Oakhaven Chronicles"),
    )

    draft = create_initial_draft_state(EntityId("draft-123"), brief)
    assert draft.draft_id == "draft-123"
    assert draft.revision == 1
    assert draft.is_published is False
    assert draft.brief.title == "Chronicles of Oakhaven"
    assert len(draft.stages) == len(ALL_DRAFT_STAGES)
    for stage_name in ALL_DRAFT_STAGES:
        st = draft.stages[stage_name]
        assert st.stage == stage_name
        assert st.status == "not_started"
        assert st.attempts == 0
        assert st.diagnostics == []
        assert st.artifact_data is None
