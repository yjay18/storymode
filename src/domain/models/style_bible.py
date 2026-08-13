"""Style bible models."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from domain.models.common import (
    DisplayString,
    EntityId,
    FrozenModel,
    SemanticVersion,
)


class SensoryPalette(FrozenModel):
    """Lists of sensory elements to incorporate into narration."""

    sounds: list[DisplayString] = Field(min_length=1)
    smells: list[DisplayString] = Field(min_length=1)
    materials: list[DisplayString] = Field(min_length=1)
    lighting: list[DisplayString] = Field(min_length=1)
    textures: list[DisplayString] = Field(min_length=1)


StyleExampleString = Annotated[str, Field(min_length=1, max_length=800)]


class StyleBible(FrozenModel):
    """Core stylistic elements for the campaign text generation."""

    style_id: EntityId
    tone: DisplayString
    narrative_voice: DisplayString
    sensory_palette: SensoryPalette
    faction_language_notes: DisplayString
    naming_conventions: DisplayString
    banned_phrases: list[DisplayString]
    description_requirements: DisplayString
    examples: list[StyleExampleString] = Field(min_length=1, max_length=5)
    anti_examples: list[StyleExampleString] = Field(min_length=1, max_length=5)
    art_direction: DisplayString

    @model_validator(mode="after")
    def check_banned_phrases(self) -> "StyleBible":
        """Banned phrases must be unique case-folded strings."""
        folded = [p.casefold() for p in self.banned_phrases]
        if len(folded) != len(set(folded)):
            raise ValueError("banned_phrases must be unique when case-folded")
        return self


class StyleBibleFile(FrozenModel):
    """The root style bible file structure."""

    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    style_bible: StyleBible
