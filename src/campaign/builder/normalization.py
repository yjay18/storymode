"""Normalization helpers for builder briefs and initial draft construction (BUILD-01)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from campaign.builder.models import (
    ALL_DRAFT_STAGES,
    ArtDirection,
    BuilderBrief,
    ContentBoundaries,
    DraftStage,
    DraftStageState,
    DraftState,
    QuickPromptInput,
    SourceMetadata,
)
from domain.models.common import EntityId


def _clean_text(text: str) -> str:
    """Trim leading/trailing whitespace and collapse interior blank runs."""
    return re.sub(r"\s+", " ", text).strip()


def _dedupe_list(items: Sequence[str]) -> list[str]:
    """Deduplicate strings while preserving original order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = _clean_text(item)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def normalize_builder_brief(brief: BuilderBrief) -> BuilderBrief:
    """Normalize a BuilderBrief by cleaning text and deduplicating list fields."""
    cleaned_boundaries = ContentBoundaries(
        excluded_topics=_dedupe_list(brief.content_boundaries.excluded_topics),
        content_rating=brief.content_boundaries.content_rating,
        violence_level=brief.content_boundaries.violence_level,
        romance_level=brief.content_boundaries.romance_level,
    )

    cleaned_art = ArtDirection(
        visual_style=_clean_text(brief.art_direction.visual_style),
        aspect_ratio=_clean_text(brief.art_direction.aspect_ratio),
    )

    return BuilderBrief(
        title=_clean_text(brief.title),
        premise=_clean_text(brief.premise),
        campaign_mode=brief.campaign_mode,
        custom_prompt=_clean_text(brief.custom_prompt) if brief.custom_prompt else None,
        genre=_clean_text(brief.genre),
        theme=_clean_text(brief.theme),
        tone=_clean_text(brief.tone),
        length=brief.length,
        difficulty=brief.difficulty,
        content_boundaries=cleaned_boundaries,
        art_direction=cleaned_art,
        source=brief.source,
        source_summary=_clean_text(brief.source_summary),
        protected_facts=_dedupe_list(brief.protected_facts),
    )


def normalize_quick_prompt(
    quick: QuickPromptInput, source: SourceMetadata | None = None
) -> BuilderBrief:
    """Convert a QuickPromptInput into a full, normalized BuilderBrief."""
    cleaned_premise = _clean_text(quick.premise)

    # Derive title if omitted
    if quick.title and quick.title.strip():
        derived_title = _clean_text(quick.title)
    else:
        # First 5-8 words of premise
        words = cleaned_premise.split()
        derived_title = " ".join(words[:6]) if words else "Untitled Adventure"
        if len(derived_title) > 60:
            derived_title = derived_title[:57] + "..."

    raw_brief = BuilderBrief(
        title=derived_title,
        premise=cleaned_premise,
        campaign_mode=quick.campaign_mode,
        custom_prompt=_clean_text(quick.custom_prompt) if quick.custom_prompt else None,
        genre=_clean_text(quick.genre) if quick.genre else "dark fantasy",
        theme=_clean_text(quick.theme)
        if quick.theme
        else "survival, honor, and political intrigue",
        tone=_clean_text(quick.tone) if quick.tone else "grounded, gritty, and atmospheric",
        length=quick.length or "medium",
        difficulty=quick.difficulty or "normal",
        content_boundaries=ContentBoundaries(),
        art_direction=ArtDirection(),
        source=source or SourceMetadata(source_type="prompt"),
        source_summary="",
        protected_facts=[],
    )
    return normalize_builder_brief(raw_brief)


def create_initial_draft_state(draft_id: EntityId, brief: BuilderBrief) -> DraftState:
    """Create a pristine DraftState with all stages initialized to not_started."""
    normalized = normalize_builder_brief(brief)
    stages: dict[DraftStage, DraftStageState] = {
        st: DraftStageState(stage=st, status="not_started", attempts=0, diagnostics=[])
        for st in ALL_DRAFT_STAGES
    }
    return DraftState(
        draft_id=draft_id,
        revision=1,
        brief=normalized,
        stages=stages,
        diagnostics=[],
        is_published=False,
    )
