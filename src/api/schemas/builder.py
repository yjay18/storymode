"""API request and response schemas for campaign builder (BUILD-09)."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from campaign.builder.models import (
    BuilderBrief,
    DraftStage,
    QuickPromptInput,
)
from domain.models.common import FrozenModel


class CreateGuidedDraftRequest(FrozenModel):
    """Payload for creating a draft from a complete builder brief."""

    brief: BuilderBrief


class CreateQuickDraftRequest(FrozenModel):
    """Payload for creating a draft from quick prompt inputs."""

    quick_input: QuickPromptInput


class GenerateStageRequest(FrozenModel):
    """Payload for triggering stage or full generation."""

    stage: DraftStage | None = None


class EditStageRequest(FrozenModel):
    """Payload for updating an individual draft stage artifact."""

    expected_revision: int = Field(ge=1)
    artifact_data: dict[str, Any]


class PublishDraftRequest(FrozenModel):
    """Payload for publishing a validated draft."""

    confirmed: bool = False
