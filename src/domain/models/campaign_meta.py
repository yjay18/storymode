"""Campaign metadata models."""

import enum
from typing import Literal

from pydantic import Field, model_validator

from domain.models.common import (
    DisplayString,
    EntityId,
    FrozenModel,
    SemanticVersion,
    UtcDatetime,
)


class Theme(enum.StrEnum):
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    APOCALYPTIC = "apocalyptic"
    CUSTOM = "custom"


class SourceType(enum.StrEnum):
    PROMPT = "prompt"
    NOVEL = "novel"
    PLAIN_TEXT = "plain_text"
    COMIC_TRANSCRIPT = "comic_transcript"
    CUSTOM = "custom"


class DefaultDifficulty(enum.StrEnum):
    STORY = "story"
    NORMAL = "normal"
    HARD = "hard"


class CampaignLength(enum.StrEnum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    CUSTOM = "custom"


class CampaignStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class CampaignMeta(FrozenModel):
    """Metadata representing a campaign's state and configuration."""

    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    title: DisplayString
    theme: Theme
    source_type: SourceType
    source_summary: str = Field(min_length=1, max_length=4000)
    default_difficulty: DefaultDifficulty
    campaign_length: CampaignLength
    art_style_ref: EntityId
    created_at: UtcDatetime
    content_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    status: CampaignStatus

    @model_validator(mode="after")
    def check_status_fingerprint(self) -> "CampaignMeta":
        """Drafts must not have a fingerprint; published requires one."""
        if self.status == CampaignStatus.DRAFT and self.content_fingerprint is not None:
            raise ValueError("Draft campaigns must not have a content_fingerprint")
        if self.status == CampaignStatus.PUBLISHED and self.content_fingerprint is None:
            raise ValueError("Published campaigns require a content_fingerprint")
        return self
