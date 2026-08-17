"""Strict design-generation LLM contracts per campaign artifact (BUILD-04).

Guarantees:
- Strict Pydantic models for each stage's LLM draft response.
- Prohibits setting published status or artificial fingerprints in drafts.
- Directly wraps the owning domain root models for zero-reshaping validation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from domain.models.area import AreasFile
from domain.models.balance import BalanceFile
from domain.models.campaign_meta import CampaignMeta, CampaignStatus
from domain.models.character import CharactersFile
from domain.models.common import FrozenModel
from domain.models.enemy import EnemiesFile
from domain.models.item import ItemsFile
from domain.models.plot import PlotFile
from domain.models.skill import SkillsFile
from domain.models.style_bible import StyleBibleFile
from domain.models.world import WorldFile


class BaseStageDraftResponse(FrozenModel):
    """Base envelope for LLM-generated campaign stage drafts."""

    contract_version: int = 1
    prompt_version: str = Field(min_length=1)
    request_id: str = Field(min_length=1)


class MetaStyleStageResponse(BaseStageDraftResponse):
    """Stage 1: Meta and Style Bible paired generation."""

    stage: Literal["meta_style"] = "meta_style"
    meta: CampaignMeta
    style: StyleBibleFile

    @model_validator(mode="after")
    def verify_draft_status(self) -> MetaStyleStageResponse:
        if self.meta.status != CampaignStatus.DRAFT:
            raise ValueError("Draft meta must have status='draft'")
        if self.meta.content_fingerprint is not None:
            raise ValueError("Draft meta must not contain a content_fingerprint")
        return self


class WorldStageResponse(BaseStageDraftResponse):
    """Stage 2: Macro world, factions, and power system generation."""

    stage: Literal["rules"] = "rules"
    world: WorldFile


class AreasStageResponse(BaseStageDraftResponse):
    """Stage 3: Areas, locations, objects, and residents generation."""

    stage: Literal["areas"] = "areas"
    areas: AreasFile


class PlotStageResponse(BaseStageDraftResponse):
    """Stage 4: Plot milestones, threads, clocks, and endings generation."""

    stage: Literal["plot"] = "plot"
    plot: PlotFile


class CharactersStageResponse(BaseStageDraftResponse):
    """Stage 5: Major characters and companions generation."""

    stage: Literal["characters"] = "characters"
    characters: CharactersFile


class SkillsStageResponse(BaseStageDraftResponse):
    """Stage 6: Skills, items, enemies, and balance generation."""

    stage: Literal["skills"] = "skills"
    skills: SkillsFile
    items: ItemsFile
    enemies: EnemiesFile
    balance: BalanceFile
