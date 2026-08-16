"""Bounded action-interpreter context packet builder (LLM-03).

Guarantees:
- Immutable packet ActionContextPacketV1 with 1-based ordinals for candidates and facts.
- Strictly excludes hidden / unrevealed facts and secret details.
- 12 KiB byte budget with graceful degradation (pruning optional summaries).
- Raises ActionContextOverflowError if mandatory candidate / reference data exceeds budget.
- Quotes player input as data; contains no mutable state or final DC calculations.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from domain.models.common import FrozenModel
from domain.models.pack import CampaignPack
from domain.models.runtime_state import RuntimeState
from engine.actions.candidates import CandidateSet

ACTION_CONTEXT_MAX_BYTES: int = 12 * 1024  # 12 KiB

ALLOWED_OPERATIONS: tuple[str, ...] = (
    "investigate",
    "alter_environment",
    "use_item",
    "persuade",
    "deceive",
    "intimidate",
    "avoid_detection",
    "travel",
    "talk",
    "inspect",
    "search",
    "prepare",
    "exploration_attack",
    "other",
)

PROTECTED_CONSTRAINTS: tuple[str, ...] = (
    "Reference candidate entities strictly by their assigned 1-based candidate ordinal index.",
    "Do not invent new entities, items, locations, or NPCs not present in the candidates list.",
    "Do not determine dice roll outcomes, calculate final target DCs, or mutate state directly.",
    "Classify uncertainty strictly using allowed challenge labels (none, easy, standard, "
    "difficult, expert, exceptional, near_impossible).",
)


class ActionContextOverflowError(Exception):
    """Raised when mandatory action context data exceeds the maximum byte budget."""


class CandidateEntry(FrozenModel):
    """A bounded candidate with 1-based ordinal index."""

    ordinal: int = Field(ge=1)
    id: str
    type: str
    name: str
    summary: str | None = None


class KnownFactEntry(FrozenModel):
    """A known fact revealed to the player with 1-based ordinal index."""

    ordinal: int = Field(ge=1)
    fact_id: str
    summary: str


class ActionContextPacketV1(FrozenModel):
    """Immutable context packet supplied to the action interpreter prompt."""

    schema_version: Literal[1] = 1
    request_id: str
    location_id: str
    location_name: str
    location_danger_level: int = 1
    location_summary: str | None = None
    candidates: list[CandidateEntry]
    known_facts: list[KnownFactEntry] = Field(default_factory=list)
    allowed_operations: list[str] = Field(default_factory=lambda: list(ALLOWED_OPERATIONS))
    player_capabilities: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=lambda: list(PROTECTED_CONSTRAINTS))
    raw_player_input: str


def build_action_context_packet(
    request_id: str,
    state: RuntimeState,
    pack: CampaignPack,
    candidate_set: CandidateSet,
    player_input: str,
    max_bytes: int = ACTION_CONTEXT_MAX_BYTES,
) -> ActionContextPacketV1:
    """Build an immutable, bounded ActionContextPacketV1 from runtime state and candidates.

    Prunes optional summary fields if needed to fit within max_bytes.
    Raises ActionContextOverflowError if mandatory data exceeds max_bytes.
    """
    # 1. Location details
    curr_area_id = state.location.area_id
    area_map = {a.id: a for a in pack.areas.areas}
    area = area_map.get(curr_area_id)
    loc_id = curr_area_id
    loc_name = area.name if area else curr_area_id
    loc_danger = area.danger_level if area else 1
    loc_summary = area.description if area else None

    # 2. Candidate entries with 1-based ordinals
    candidate_entries: list[CandidateEntry] = [
        CandidateEntry(
            ordinal=i + 1,
            id=c.id,
            type=c.type,
            name=c.name,
        )
        for i, c in enumerate(candidate_set.candidates)
    ]

    # 3. Known facts only (facts present in state.known_fact_ids)
    known_fact_entries: list[KnownFactEntry] = [
        KnownFactEntry(
            ordinal=ordinal,
            fact_id=fact_id,
            summary=f"Fact: {fact_id}",
        )
        for ordinal, fact_id in enumerate(sorted(state.known_fact_ids), start=1)
    ]

    # 4. Player capabilities (known combat skills & abilities)
    player_caps: list[str] = [k.skill_id for k in state.player.known_combat_skills]

    # 5. Build candidate packet
    packet = ActionContextPacketV1(
        schema_version=1,
        request_id=request_id,
        location_id=loc_id,
        location_name=loc_name,
        location_danger_level=loc_danger,
        location_summary=loc_summary,
        candidates=candidate_entries,
        known_facts=known_fact_entries,
        allowed_operations=list(ALLOWED_OPERATIONS),
        player_capabilities=player_caps,
        constraints=list(PROTECTED_CONSTRAINTS),
        raw_player_input=player_input,
    )

    # 6. Check size budget and apply graceful degradation if needed
    dumped = packet.model_dump_json().encode("utf-8")
    if len(dumped) <= max_bytes:
        return packet

    # Stage 1 pruning: remove location summary
    if packet.location_summary is not None:
        packet = packet.model_copy(update={"location_summary": None})
        dumped = packet.model_dump_json().encode("utf-8")
        if len(dumped) <= max_bytes:
            return packet

    # If still oversized, check if mandatory data exceeds budget
    if len(dumped) > max_bytes:
        raise ActionContextOverflowError(
            f"Mandatory action context data exceeds budget of {max_bytes} bytes "
            f"({len(dumped)} bytes)"
        )

    return packet
