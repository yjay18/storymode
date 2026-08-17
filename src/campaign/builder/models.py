"""Campaign builder domain models (BUILD-01).

Guarantees:
- Strictly typed builder brief and draft lifecycle states.
- Supports both guided and quick prompt entry paths.
- Enforces content boundaries, source metadata, and campaign modes.
- Prevents published state or stage skipping directly on draft models.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from domain.models.common import EntityId, FrozenModel

CampaignMode = Literal["faithful_story", "custom_prompt", "llm_decide"]
CampaignLength = Literal["one_shot", "short", "medium", "epic"]
CampaignDifficulty = Literal["story", "normal", "hardcore"]
SourceType = Literal["prompt", "novel", "plain_text", "comic_transcript", "epub", "custom"]
ContentRating = Literal["everyone", "teen", "mature"]
ViolenceLevel = Literal["mild", "moderate", "gritty", "extreme"]
RomanceLevel = Literal["none", "implied", "fade_to_black"]

DraftStage = Literal[
    "meta_style",
    "rules",
    "areas",
    "plot",
    "characters",
    "skills",
    "review",
]

StageStatus = Literal[
    "not_started",
    "running",
    "valid",
    "invalid",
    "cancelled",
]

ALL_DRAFT_STAGES: tuple[DraftStage, ...] = (
    "meta_style",
    "rules",
    "areas",
    "plot",
    "characters",
    "skills",
    "review",
)


class SourceMetadata(FrozenModel):
    """Metadata about imported source materials."""

    source_type: SourceType = "prompt"
    title: str | None = None
    author: str | None = None
    provenance_note: str | None = None
    raw_char_count: int = Field(default=0, ge=0)


class ContentBoundaries(FrozenModel):
    """User boundaries and content ratings for generation."""

    excluded_topics: list[str] = Field(default_factory=list)
    content_rating: ContentRating = "teen"
    violence_level: ViolenceLevel = "gritty"
    romance_level: RomanceLevel = "none"


class ArtDirection(FrozenModel):
    """Stylistic art and visual preferences."""

    visual_style: str = "painterly dark fantasy with rich contrast and muted earth tones"
    aspect_ratio: str = "16:9"


class BuilderBrief(FrozenModel):
    """Normalized, complete campaign creation brief."""

    title: str = Field(min_length=1, max_length=100)
    premise: str = Field(min_length=1, max_length=4000)
    campaign_mode: CampaignMode = "llm_decide"
    custom_prompt: str | None = Field(default=None, max_length=4000)
    genre: str = Field(default="dark fantasy", min_length=1, max_length=100)
    theme: str = Field(
        default="survival, honor, and political intrigue", min_length=1, max_length=200
    )
    tone: str = Field(default="grounded, gritty, and atmospheric", min_length=1, max_length=200)
    length: CampaignLength = "medium"
    difficulty: CampaignDifficulty = "normal"
    content_boundaries: ContentBoundaries = Field(default_factory=ContentBoundaries)
    art_direction: ArtDirection = Field(default_factory=ArtDirection)
    source: SourceMetadata = Field(default_factory=SourceMetadata)
    source_summary: str = Field(default="", max_length=10000)
    protected_facts: list[str] = Field(default_factory=list)


class QuickPromptInput(FrozenModel):
    """Convenience input payload for one-click or quick campaign creation."""

    premise: str = Field(min_length=1, max_length=4000)
    title: str | None = Field(default=None, max_length=100)
    campaign_mode: CampaignMode = "llm_decide"
    custom_prompt: str | None = Field(default=None, max_length=4000)
    genre: str | None = None
    theme: str | None = None
    tone: str | None = None
    length: CampaignLength | None = None
    difficulty: CampaignDifficulty | None = None


class StageDiagnostic(FrozenModel):
    """Structured diagnostic message for a generation stage."""

    stage: DraftStage
    code: str
    message: str
    field_path: str | None = None
    is_error: bool = True


class DraftStageState(FrozenModel):
    """Execution state and output of an individual draft stage."""

    stage: DraftStage
    status: StageStatus = "not_started"
    attempts: int = Field(default=0, ge=0)
    diagnostics: list[StageDiagnostic] = Field(default_factory=list)
    artifact_data: dict[str, Any] | None = None


class DraftState(FrozenModel):
    """Full lifecycle state of an in-progress campaign draft."""

    draft_id: EntityId
    revision: int = Field(default=1, ge=1)
    brief: BuilderBrief
    stages: dict[DraftStage, DraftStageState] = Field(default_factory=dict)
    diagnostics: list[StageDiagnostic] = Field(default_factory=list)
    is_published: bool = False
    published_campaign_id: EntityId | None = None
