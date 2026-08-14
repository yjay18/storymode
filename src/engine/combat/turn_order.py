"""Turn order calculation with Speed/Dexterity sorting and deterministic tie-breaks."""

from __future__ import annotations

from dataclasses import dataclass

from domain.models.audit import RollRecord
from domain.models.combat_state import TieBreakRecord
from domain.models.common import DisplayString, EntityId
from engine.dice.ports import RandomSource
from engine.dice.service import DiceService


@dataclass(frozen=True)
class ParticipantInitiative:
    """Initiative values for a combat participant."""

    participant_id: EntityId
    speed: int
    dexterity: int


@dataclass(frozen=True)
class TurnOrderResult:
    """Result of turn order calculation including tie-break records and audit logs."""

    order: list[EntityId]
    tie_break_records: list[TieBreakRecord]
    roll_records: list[RollRecord]


def calculate_turn_order(
    participants: list[ParticipantInitiative],
    rng: RandomSource | None = None,
    existing_tie_breaks: list[TieBreakRecord] | None = None,
    dice_service: DiceService | None = None,
    transaction_id: EntityId | None = None,
    revision: int = 1,
    command_id: EntityId | None = None,
) -> TurnOrderResult:
    """Calculate deterministic turn order for combat participants.

    Ordering rules:
    1. Speed descending.
    2. Dexterity descending.
    3. Tie-break: one d20 per tied participant (reusing existing tie-break if available).
    4. Exact tie-break score tie falls back to stable participant_id ascending.

    Returns TurnOrderResult containing the sorted participant IDs, updated tie-break
    records, and any generated roll audit records.
    """
    if not participants:
        return TurnOrderResult(order=[], tie_break_records=[], roll_records=[])

    # Map existing tie-break records
    tie_break_map: dict[EntityId, int] = {}
    tie_break_records_list: list[TieBreakRecord] = []
    if existing_tie_breaks:
        for tb in existing_tie_breaks:
            tie_break_map[tb.participant_id] = tb.roll_total
            tie_break_records_list.append(tb)

    roll_records: list[RollRecord] = []

    # Group participants by (speed, dexterity)
    groups: dict[tuple[int, int], list[ParticipantInitiative]] = {}
    for p in participants:
        key = (p.speed, p.dexterity)
        if key not in groups:
            groups[key] = []
        groups[key].append(p)

    # Sort groups descending by (speed, dexterity)
    sorted_group_keys = sorted(groups.keys(), reverse=True)

    order: list[EntityId] = []

    for key in sorted_group_keys:
        tied_participants = groups[key]
        if len(tied_participants) == 1:
            order.append(tied_participants[0].participant_id)
        else:
            # Need tie-break resolution for participants in this group
            for p in tied_participants:
                if p.participant_id not in tie_break_map:
                    if dice_service is not None and transaction_id and command_id:
                        roll, record = dice_service.roll_tie_break(
                            transaction_id=transaction_id,
                            revision=revision,
                            command_id=command_id,
                            reason=DisplayString(f"Initiative tie-break for {p.participant_id}"),
                        )
                        roll_records.append(record)
                    elif rng is not None:
                        roll = rng.roll(20)
                    else:
                        raise ValueError(
                            "Cannot resolve tie-break: neither rng nor dice_service provided"
                        )

                    tb_record = TieBreakRecord(
                        participant_id=p.participant_id,
                        roll_total=roll,
                    )
                    tie_break_map[p.participant_id] = roll
                    tie_break_records_list.append(tb_record)

            # Sort tied participants by (-roll_total, participant_id)
            sorted_tied = sorted(
                tied_participants,
                key=lambda p: (-tie_break_map[p.participant_id], p.participant_id),
            )
            for p in sorted_tied:
                order.append(p.participant_id)

    return TurnOrderResult(
        order=order,
        tie_break_records=tie_break_records_list,
        roll_records=roll_records,
    )
