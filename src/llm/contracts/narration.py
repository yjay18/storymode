"""Narration output contract (LLM-06)."""

from typing import Literal

from pydantic import Field

from llm.contracts.common import StrictContractModel


class NarrationV1(StrictContractModel):
    """Authoritative structured output from the Narrator LLM."""

    contract_version: Literal[1] = 1
    prompt_version: str = Field(min_length=1, max_length=50)
    request_id: str = Field(min_length=1, max_length=100)
    narration: str = Field(min_length=1, max_length=4000)
    speaker_ordinals_used: list[int] = Field(default_factory=list)
    fact_ordinals_referenced: list[int] = Field(default_factory=list)
