"""Unit tests for COMBAT-03 turn-start mana and status processing."""

import pytest

from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.common import EntityId
from domain.models.runtime_common import ResourceValue, StatusInstance
from engine.combat.statuses import process_actor_statuses
from engine.combat.turns import advance_turn, is_side_defeated, process_turn_start


def make_participant(
    side: ParticipantSide = ParticipantSide.PARTY,
    hp: int = 20,
    max_hp: int = 20,
    armour: int = 5,
    max_armour: int = 5,
    mana: int = 2,
    max_mana: int = 10,
    statuses: list[StatusInstance] | None = None,
) -> CombatParticipant:
    return CombatParticipant(
        hp=ResourceValue(current=hp, maximum=max_hp),
        armour=ResourceValue(current=armour, maximum=max_armour),
        mana=ResourceValue(current=mana, maximum=max_mana),
        statuses=statuses or [],
        known_combat_skills=[],
        combat_loadout=[],
        side=side,
    )


def test_process_turn_start_mana_regen_capped() -> None:
    # Mana 8/10, regen 4 -> should cap at 10/10
    actor = make_participant(mana=8, max_mana=10)
    combat = CombatState(
        encounter_id=EntityId("enc_1"),
        phase=CombatPhase.ACTIVE,
        round=1,
        order=[EntityId("hero")],
        current_index=0,
        participants={EntityId("hero"): actor},
    )

    updated_combat, can_act, logs = process_turn_start(combat, EntityId("hero"), mana_regen=4)
    assert can_act
    assert updated_combat.participants[EntityId("hero")].mana.current == 10
    assert any("regenerated 2 mana" in msg for msg in logs)


def test_status_expiry_boundary() -> None:
    # Status with duration=1 expires at turn start
    guarded_status = StatusInstance(status_id=EntityId("guarded"), duration_remaining=1)
    bleed_status = StatusInstance(status_id=EntityId("bleed"), duration_remaining=2, magnitude=3)

    actor = make_participant(hp=10, armour=0, statuses=[guarded_status, bleed_status])

    updated_actor, remaining, prevent_action, _logs = process_actor_statuses(actor)
    assert not prevent_action
    assert updated_actor.hp.current == 7  # 10 - 3 bleed
    assert len(remaining) == 1
    assert remaining[0].status_id == EntityId("bleed")
    assert remaining[0].duration_remaining == 1  # decremented from 2 to 1


def test_status_priority_ordering() -> None:
    # Priority: Bleed (10) < Stun (30) < Guarded (100)
    bleed = StatusInstance(status_id=EntityId("bleed"), duration_remaining=2, magnitude=2)
    stun = StatusInstance(status_id=EntityId("stun"), duration_remaining=1)
    guarded = StatusInstance(status_id=EntityId("guarded"), duration_remaining=1)

    # Supply them in reverse order
    actor = make_participant(hp=10, armour=0, statuses=[guarded, stun, bleed])
    updated_actor, remaining, prevent_action, _logs = process_actor_statuses(actor)

    assert prevent_action  # Stun prevents action
    assert updated_actor.hp.current == 8  # Bleed ran
    assert len(remaining) == 1
    assert remaining[0].status_id == EntityId("bleed")  # only bleed (duration 2->1) remains


def test_dot_defeat_and_skip() -> None:
    # Actor with 2 HP suffers 3 bleed damage -> Dies at turn start
    bleed = StatusInstance(status_id=EntityId("bleed"), duration_remaining=2, magnitude=3)
    actor_hero = make_participant(side=ParticipantSide.PARTY, hp=2, armour=0, statuses=[bleed])
    actor_enemy = make_participant(side=ParticipantSide.ENEMY, hp=10)

    combat = CombatState(
        encounter_id=EntityId("enc_1"),
        phase=CombatPhase.ACTIVE,
        round=1,
        order=[EntityId("hero"), EntityId("enemy")],
        current_index=0,
        participants={
            EntityId("hero"): actor_hero,
            EntityId("enemy"): actor_enemy,
        },
    )

    updated_combat, can_act, _logs = process_turn_start(combat, EntityId("hero"), mana_regen=2)
    assert not can_act
    assert updated_combat.participants[EntityId("hero")].hp.current == 0


def test_advance_turn_round_rollover_and_skip_dead() -> None:
    hero = make_participant(side=ParticipantSide.PARTY, hp=20, mana=2)
    dead_enemy_1 = make_participant(side=ParticipantSide.ENEMY, hp=0)
    living_enemy_2 = make_participant(side=ParticipantSide.ENEMY, hp=10, mana=0)

    combat = CombatState(
        encounter_id=EntityId("enc_1"),
        phase=CombatPhase.ACTIVE,
        round=1,
        order=[EntityId("hero"), EntityId("enemy_1"), EntityId("enemy_2")],
        current_index=0,  # Currently Hero's turn
        participants={
            EntityId("hero"): hero,
            EntityId("enemy_1"): dead_enemy_1,
            EntityId("enemy_2"): living_enemy_2,
        },
    )

    # Advance from index 0 -> should skip dead enemy_1 at index 1 and arrive at enemy_2 at index 2
    updated_combat, active_actor, can_act, _logs = advance_turn(
        combat, mana_regen_by_id={EntityId("enemy_2"): 1}
    )

    assert active_actor == EntityId("enemy_2")
    assert can_act
    assert updated_combat.current_index == 2
    assert updated_combat.round == 1
    assert updated_combat.participants[EntityId("enemy_2")].mana.current == 1

    # Advance from index 2 -> should loop to index 0 and increment round to 2
    updated_combat_2, active_actor_2, can_act_2, logs_2 = advance_turn(
        updated_combat, mana_regen_by_id={EntityId("hero"): 2}
    )

    assert active_actor_2 == EntityId("hero")
    assert can_act_2
    assert updated_combat_2.current_index == 0
    assert updated_combat_2.round == 2
    assert any("Round 2 begins." in log for log in logs_2)


def test_advance_turn_detects_side_defeat() -> None:
    hero = make_participant(side=ParticipantSide.PARTY, hp=20)
    dead_enemy = make_participant(side=ParticipantSide.ENEMY, hp=0)

    combat = CombatState(
        encounter_id=EntityId("enc_1"),
        phase=CombatPhase.ACTIVE,
        round=1,
        order=[EntityId("hero"), EntityId("enemy")],
        current_index=0,
        participants={
            EntityId("hero"): hero,
            EntityId("enemy"): dead_enemy,
        },
    )

    assert is_side_defeated(combat, ParticipantSide.ENEMY)
    assert not is_side_defeated(combat, ParticipantSide.PARTY)

    _updated_combat, active_actor, can_act, logs = advance_turn(combat)
    assert active_actor is None
    assert not can_act
    assert any("All enemies are defeated." in log for log in logs)


def test_unknown_status_raises_validation_error() -> None:
    unknown = StatusInstance(status_id=EntityId("unknown_hex"), duration_remaining=2)
    actor = make_participant(statuses=[unknown])

    with pytest.raises(ValueError, match="Unknown status ID: unknown_hex"):
        process_actor_statuses(actor)
