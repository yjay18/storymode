"""Action candidates."""

from dataclasses import dataclass
from typing import Literal

from domain.models.common import EntityId

CandidateType = Literal["object", "npc", "companion", "item", "fact", "area"]

@dataclass(frozen=True)
class Candidate:
    """A bounded candidate that the LLM can reference."""
    id: EntityId
    type: CandidateType
    name: str

@dataclass(frozen=True)
class CandidateSet:
    """A set of candidates available in the current context."""
    candidates: list[Candidate]
    
    def get_by_ordinal(self, ordinal: int) -> Candidate | None:
        """Get a candidate by its 1-based ordinal index."""
        if 1 <= ordinal <= len(self.candidates):
            return self.candidates[ordinal - 1]
        return None
        
    def build_ordinal_map(self) -> dict[int, Candidate]:
        """Build a mapping of ordinal to Candidate."""
        return {i + 1: c for i, c in enumerate(self.candidates)}
