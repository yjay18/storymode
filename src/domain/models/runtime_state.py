"""Runtime root state model."""

from typing import Literal

from pydantic import Field, model_validator

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.check_state import PendingCheck
from domain.models.combat_state import CombatState
from domain.models.common import DisplayString, EntityId, FrozenModel, SemanticVersion
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import ClockState, PlotState
from domain.models.world_state import LocationState, NpcOverride, ObjectOverride


class CommandReceipt(FrozenModel):
    """Receipt of a processed command."""

    command_id: EntityId
    canonical_request_hash: str
    committed_revision: int
    result_kind: DisplayString
    safe_result_summary: DisplayString
    roll_ids: list[EntityId] = Field(default_factory=list)


class EncounterSummary(FrozenModel):
    """Summary of a completed encounter."""

    encounter_id: EntityId
    outcome: DisplayString
    round_count: int


class RuntimeState(FrozenModel):
    """The authoritative root state of a save game."""

    schema_version: Literal[1] = 1

    campaign_id: EntityId
    campaign_version: SemanticVersion
    campaign_fingerprint: str
    save_id: EntityId

    revision: int = Field(ge=0)
    last_command_receipts: list[CommandReceipt] = Field(default_factory=list)

    difficulty: DefaultDifficulty
    play_seconds: int = Field(default=0, ge=0)

    player: PlayerState
    party: PartyState
    location: LocationState
    plot: PlotState

    known_fact_ids: set[EntityId] = Field(default_factory=set)
    world_flags: dict[EntityId, bool | int | str] = Field(default_factory=dict)

    npc_overrides: dict[EntityId, NpcOverride] = Field(default_factory=dict)
    area_object_overrides: dict[EntityId, ObjectOverride] = Field(default_factory=dict)
    clocks: dict[EntityId, ClockState] = Field(default_factory=dict)

    encounter_history: list[EncounterSummary] = Field(default_factory=list)

    pending_check: PendingCheck | None = None
    combat: CombatState | None = None

    @model_validator(mode="after")
    def check_runtime_invariants(self) -> "RuntimeState":
        """Verify global invariants."""
        if len(self.last_command_receipts) > 100:
            raise ValueError("last_command_receipts cannot exceed 100")

        if self.pending_check is not None and self.combat is not None:
            raise ValueError("cannot have both a pending check and active combat")

        # Revision must not trail command receipts
        if self.last_command_receipts:
            max_receipt_rev = max(r.committed_revision for r in self.last_command_receipts)
            if self.revision < max_receipt_rev:
                raise ValueError("revision cannot trail a committed command receipt")

        return self
