"""Common LLM contract models."""

from pydantic import BaseModel, ConfigDict


class StrictContractModel(BaseModel):
    """Base model for strict LLM contracts.
    
    Rejects any extra fields that the LLM might hallucinate.
    """
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
    )
