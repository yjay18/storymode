"""Action proposal contract."""

from typing import Any

from llm.contracts.common import StrictContractModel


class ActionProposal(StrictContractModel):
    """An action proposed by the LLM."""
    
    intention: str
    action_type: str
    target_id: str | None = None
    payload: dict[str, Any]
