"""Bounded narrator context packet builder (LLM-06).

Guarantees:
- Built strictly POST-COMMIT from authoritative engine events and receipts.
- Includes present speakers with 1-based ordinals and recent narrative memories (3-5 max).
- Enforces strict 20 KiB byte budget with graceful summary/history degradation.
- Explicitly lists forbidden mechanical claims.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from domain.models.common import FrozenModel
from domain.models.pack import CampaignPack
from domain.models.runtime_state import CommandReceipt, RuntimeState

NARRATOR_CONTEXT_MAX_BYTES: int = 20 * 1024  # 20 KiB

STANDARD_FORBIDDEN_CLAIMS: tuple[str, ...] = (
    "Do not declare any character or NPC dead unless explicitly stated in the factual result.",
    "Do not grant new items, currency, or inventory changes not confirmed in the event.",
    "Do not change the party's location unless the event confirmed a successful travel.",
    "Do not contradict dice roll outcomes or state that a failed check was successful.",
)


class NarratorContextOverflowError(Exception):
    """Raised when mandatory narrator context exceeds maximum byte budget."""


class SpeakerEntry(FrozenModel):
    """An available speaker in the current scene with 1-based ordinal."""

    ordinal: int = Field(ge=1)
    id: str
    name: str
    role: str


class CommittedRollView(FrozenModel):
    """Summary of an authoritative dice roll that resolved this action."""

    natural_roll: int
    modifier: int
    total: int
    target_dc: int | None = None
    outcome: str


class RecentMemoryEntry(FrozenModel):
    """Summary of a past narrative event in the campaign."""

    ordinal: int = Field(ge=1)
    revision: int
    summary: str


class NarratorContextPacketV1(FrozenModel):
    """Immutable context packet supplied to the Narrator prompt."""

    schema_version: Literal[1] = 1
    request_id: str
    committed_revision: int
    result_kind: str
    safe_result_summary: str
    location_name: str
    location_description: str | None = None
    roll_display: CommittedRollView | None = None
    present_speakers: list[SpeakerEntry] = Field(default_factory=list)
    recent_memories: list[RecentMemoryEntry] = Field(default_factory=list)
    active_objectives: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=lambda: list(STANDARD_FORBIDDEN_CLAIMS))
    style_guidelines: list[str] = Field(default_factory=list)


def build_narrator_context_packet(
    request_id: str,
    state: RuntimeState,
    pack: CampaignPack,
    receipt: CommandReceipt,
    roll_view: CommittedRollView | None = None,
    raw_recent_memories: list[str] | None = None,
    max_bytes: int = NARRATOR_CONTEXT_MAX_BYTES,
) -> NarratorContextPacketV1:
    """Build an immutable, bounded NarratorContextPacketV1 post-commit."""
    # 1. Location details
    curr_area_id = state.location.area_id
    area_map = {a.id: a for a in pack.areas.areas}
    area = area_map.get(curr_area_id)
    loc_name = str(area.name) if area else curr_area_id
    loc_desc = str(area.description) if area else None

    # 2. Present speakers (active companions + area residents)
    present_speakers: list[SpeakerEntry] = []
    ordinal = 1

    # Protagonist
    present_speakers.append(
        SpeakerEntry(
            ordinal=ordinal,
            id=state.player.id,
            name=state.player.name,
            role="Protagonist",
        )
    )
    ordinal += 1

    # Active Companions
    comp_defs = {c.id: c for c in pack.characters.companions}
    for comp_id in sorted(state.party.active_companion_ids):
        c_def = comp_defs.get(comp_id)
        name = str(c_def.name) if c_def else comp_id
        role = str(c_def.role) if c_def else "Companion"
        present_speakers.append(
            SpeakerEntry(
                ordinal=ordinal,
                id=comp_id,
                name=name,
                role=role,
            )
        )
        ordinal += 1

    # Area Residents
    if area:
        for res in area.residents:
            present_speakers.append(
                SpeakerEntry(
                    ordinal=ordinal,
                    id=res.id,
                    name=str(res.name),
                    role=str(res.role),
                )
            )
            ordinal += 1

    # 3. Recent narrative memories (bounded to last 5)
    recent_mem_entries: list[RecentMemoryEntry] = []
    if raw_recent_memories:
        bounded_mem = raw_recent_memories[-5:]
        for i, mem_str in enumerate(bounded_mem, start=1):
            recent_mem_entries.append(
                RecentMemoryEntry(
                    ordinal=i,
                    revision=state.revision - len(bounded_mem) + i,
                    summary=mem_str,
                )
            )

    # 4. Active milestone/plot objectives
    active_objs: list[str] = []
    milestone_map = {m.id: m for m in pack.plot.milestones}
    for m_id in sorted(state.plot.current_milestone_ids):
        m_def = milestone_map.get(m_id)
        if m_def:
            active_objs.append(f"{m_def.id}: {m_def.canonical_truth}")

    # 5. Style guidelines from style bible
    sb = pack.style.style_bible
    style_rules: list[str] = [
        f"Tone: {sb.tone}",
        f"Narrative voice: {sb.narrative_voice}",
        (
            f"Sensory palette: lighting ({', '.join(sb.sensory_palette.lighting[:2])}), "
            f"sounds ({', '.join(sb.sensory_palette.sounds[:2])})"
        ),
    ]

    packet = NarratorContextPacketV1(
        schema_version=1,
        request_id=request_id,
        committed_revision=receipt.committed_revision,
        result_kind=str(receipt.result_kind),
        safe_result_summary=str(receipt.safe_result_summary),
        location_name=loc_name,
        location_description=loc_desc,
        roll_display=roll_view,
        present_speakers=present_speakers,
        recent_memories=recent_mem_entries,
        active_objectives=active_objs,
        forbidden_claims=list(STANDARD_FORBIDDEN_CLAIMS),
        style_guidelines=style_rules,
    )

    dumped = packet.model_dump_json().encode("utf-8")
    if len(dumped) <= max_bytes:
        return packet

    # Stage 1 pruning: strip location description
    if packet.location_description is not None:
        packet = packet.model_copy(update={"location_description": None})
        dumped = packet.model_dump_json().encode("utf-8")
        if len(dumped) <= max_bytes:
            return packet

    # Stage 2 pruning: reduce memories to most recent 2
    if len(packet.recent_memories) > 2:
        packet = packet.model_copy(update={"recent_memories": packet.recent_memories[-2:]})
        dumped = packet.model_dump_json().encode("utf-8")
        if len(dumped) <= max_bytes:
            return packet

    if len(dumped) > max_bytes:
        raise NarratorContextOverflowError(
            f"Mandatory narrator context exceeds budget of {max_bytes} bytes ({len(dumped)} bytes)"
        )

    return packet
