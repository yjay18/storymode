"""Combat snapshot models."""

import enum

from pydantic import Field, model_validator

from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.runtime_common import KnownCombatSkill, ResourceValue, StatusInstance


class CombatPhase(enum.StrEnum):
    """The current phase of a combat encounter."""

    ACTIVE = "active"
    RESOLVING = "resolving"
    VICTORY = "victory"
    DEFEAT = "defeat"
    ESCAPED = "escaped"
    YIELDED = "yielded"


class ParticipantSide(enum.StrEnum):
    """Which side a participant is on."""

    PARTY = "party"
    ENEMY = "enemy"
    NEUTRAL = "neutral"


class CombatParticipant(FrozenModel):
    """A combat participant snapshot."""

    hp: ResourceValue
    armour: ResourceValue
    mana: ResourceValue

    statuses: list[StatusInstance] = Field(default_factory=list)
    known_combat_skills: list[KnownCombatSkill] = Field(default_factory=list)
    combat_loadout: list[EntityId] = Field(default_factory=list)

    faction_id: EntityId | None = None
    side: ParticipantSide


class TieBreakRecord(FrozenModel):
    """Record of a random tie-break used to order participants."""

    participant_id: EntityId
    roll_total: int


class CombatState(FrozenModel):
    """The snapshot of an active combat encounter."""

    encounter_id: EntityId
    phase: CombatPhase = CombatPhase.ACTIVE
    round: int = Field(default=1, ge=1)
    order: list[EntityId] = Field(default_factory=list)
    current_index: int = Field(default=0, ge=0)

    participants: dict[EntityId, CombatParticipant] = Field(default_factory=dict)
    tie_break_records: list[TieBreakRecord] = Field(default_factory=list)

    escape_policy: EntityId | None = None
    yield_policy: EntityId | None = None

    encounter_modifiers: list[DisplayString] = Field(default_factory=list)
    origin_ids: list[EntityId] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_combat_invariants(self) -> "CombatState":
        """Verify phase constraints and order consistency."""
        # Terminal phase rejection for normally persisted state
        # A normal persisted state should only be ACTIVE. Other phases are transient.
        # Note: The requirement "terminal stored-phase rejection" implies that we
        # should raise an error if phase is terminal, as terminal states reduce to
        # encounter history instead of being persisted as a CombatState.
        terminal_phases = {
            CombatPhase.VICTORY,
            CombatPhase.DEFEAT,
            CombatPhase.ESCAPED,
            CombatPhase.YIELDED,
        }
        if self.phase in terminal_phases:
            raise ValueError(f"CombatState cannot be persisted in terminal phase: {self.phase}")

        # Duplicate order checking
        if len(self.order) != len(set(self.order)):
            raise ValueError("combat order contains duplicates")

        # Current index bounds checking
        if self.order and self.current_index >= len(self.order):
            msg = (
                f"current_index ({self.current_index}) is out of bounds "
                f"for order of size {len(self.order)}"
            )
            raise ValueError(msg)

        # All order IDs must exist in participants
        for actor_id in self.order:
            if actor_id not in self.participants:
                raise ValueError(f"actor {actor_id} in order is not in participants dict")

        return self
