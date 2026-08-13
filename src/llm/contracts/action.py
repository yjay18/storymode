"""Action proposal contract."""

from typing import Literal

from pydantic import Field

from llm.contracts.common import StrictContractModel


class EntityMention(StrictContractModel):
    """An entity mentioned in the proposal."""
    
    text: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=50)
    candidate_ordinal: int | None = None


class ActionProposal(StrictContractModel):
    """An action proposed by the LLM (ActionProposalV1)."""
    
    contract_version: Literal[1]
    prompt_version: str
    request_id: str
    status: Literal["valid", "valid_creative", "partial", "invalid"]
    operation: Literal[
        "investigate", "alter_environment", "use_item", "persuade", "deceive",
        "intimidate", "avoid_detection", "travel", "talk", "inspect", "search",
        "prepare", "exploration_attack", "other"
    ]
    verb: str = Field(min_length=1, max_length=80)
    entity_mentions: list[EntityMention] = Field(default_factory=list, max_length=8)
    capability_mentions: list[str] = Field(default_factory=list, max_length=8)
    intended_effect: str = Field(min_length=1, max_length=300)
    challenge_label: Literal[
        "none", "easy", "standard", "difficult", "expert", "exceptional", "near_impossible"
    ]
    uncertainty_reason: str | None = Field(None, max_length=300)
    stakes: list[str] = Field(default_factory=list, max_length=5)
    reinterpretation: str | None = None
    redirect: str | None = None
