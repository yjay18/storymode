"""Unit tests for COMBAT-06 Defend and Guarded status."""

import pytest

from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.common import EntityId
from domain.models.runtime_common import ResourceValue, StatusInstance
from domain.models.skill import EffectDefinition, EffectKind
from engine.combat.defend import execute_defend_command
from engine.combat.effects import apply_effect
from engine.combat.statuses import process_actor_statuses


def make_test_combat(
    actor_statuses: list[StatusInstance] | None = None,
    hp: int = 20,
    armour: int = 5,
) -> CombatState:
    hero = CombatParticipant(
        hp=ResourceValue(current=hp, maximum=hp),
        armour=ResourceValue(current=armour, maximum=armour),
        mana=ResourceValue(current=10, maximum=10),
        statuses=actor_statuses or [],
        known_combat_skills=[],
        combat_loadout=[],
        side=ParticipantSide.PARTY,
    )
    enemy = CombatParticipant(
        hp=ResourceValue(current=15, maximum=15),
        armour=ResourceValue(current=2, maximum=2),
        mana=ResourceValue(current=0, maximum=0),
        statuses=[],
        known_combat_skills=[],
        combat_loadout=[],
        side=ParticipantSide.ENEMY,
    )
    return CombatState(
        encounter_id=EntityId("enc_1"),
        phase=CombatPhase.ACTIVE,
        round=1,
        order=[EntityId("hero"), EntityId("enemy")],
        current_index=0,
        participants={
            EntityId("hero"): hero,
            EntityId("enemy"): enemy,
        },
    )


def test_defend_applies_guarded_and_redefend_refreshes() -> None:
    combat = make_test_combat()

    # Hero executes Defend
    res = execute_defend_command(combat, EntityId("hero"))
    assert res.success
    hero_after = res.combat_state.participants[EntityId("hero")]
    assert len(hero_after.statuses) == 1
    assert hero_after.statuses[0].status_id == EntityId("guarded")
    assert hero_after.statuses[0].duration_remaining == 1

    # Re-defend refreshes duration to 1 without duplicating
    res2 = execute_defend_command(res.combat_state, EntityId("hero"))
    hero_after_2 = res2.combat_state.participants[EntityId("hero")]
    assert len(hero_after_2.statuses) == 1
    assert hero_after_2.statuses[0].status_id == EntityId("guarded")
    assert hero_after_2.statuses[0].duration_remaining == 1


@pytest.mark.parametrize(
    ("incoming_damage", "expected_reduction", "expected_final_damage"),
    [
        (1, 1, 0),  # 25% of 1 = 0, floored to min 1 -> dmg 0
        (3, 1, 2),  # 25% of 3 = 0, floored to min 1 -> dmg 2
        (4, 1, 3),  # 25% of 4 = 1 -> dmg 3
        (5, 1, 4),  # 25% of 5 = 1 -> dmg 4
        (8, 2, 6),  # 25% of 8 = 2 -> dmg 6
    ],
)
def test_guarded_reductions_and_consumption(
    incoming_damage: int,
    expected_reduction: int,
    expected_final_damage: int,
) -> None:
    # Target has Guarded and 0 armour
    guarded_hero = CombatParticipant(
        hp=ResourceValue(current=20, maximum=20),
        armour=ResourceValue(current=0, maximum=0),
        mana=ResourceValue(current=10, maximum=10),
        statuses=[StatusInstance(status_id=EntityId("guarded"), duration_remaining=1)],
        side=ParticipantSide.PARTY,
    )

    effect = EffectDefinition(
        effect_id=EntityId("attack"),
        kind=EffectKind.DAMAGE,
        magnitude=incoming_damage,
    )

    updated_target, result = apply_effect(
        effect=effect,
        target_id=EntityId("hero"),
        target=guarded_hero,
    )

    assert result.applied
    assert result.details["reduced_by_guard"] == expected_reduction
    assert result.details["final_damage"] == expected_final_damage
    assert updated_target.hp.current == 20 - expected_final_damage
    # Guarded must be consumed upon receiving damage
    assert not any(s.status_id == EntityId("guarded") for s in updated_target.statuses)


def test_guarded_with_armour_routing() -> None:
    # Hero has 3 armour and Guarded. Incoming 5 damage -> 25% reduction (1) = 4 dmg.
    # 3 absorbed by armour, 1 to HP.
    hero = CombatParticipant(
        hp=ResourceValue(current=20, maximum=20),
        armour=ResourceValue(current=3, maximum=3),
        mana=ResourceValue(current=10, maximum=10),
        statuses=[StatusInstance(status_id=EntityId("guarded"), duration_remaining=1)],
        side=ParticipantSide.PARTY,
    )
    effect = EffectDefinition(
        effect_id=EntityId("attack"),
        kind=EffectKind.DAMAGE,
        magnitude=5,
    )

    updated_target, result = apply_effect(
        effect=effect,
        target_id=EntityId("hero"),
        target=hero,
    )

    assert result.details["reduced_by_guard"] == 1
    assert result.details["final_damage"] == 4
    assert result.details["armour_absorbed"] == 3
    assert result.details["hp_damage"] == 1
    assert updated_target.armour.current == 0
    assert updated_target.hp.current == 19


def test_guarded_not_consumed_by_heal() -> None:
    # Healing effect does not consume Guarded
    hero = CombatParticipant(
        hp=ResourceValue(current=10, maximum=20),
        armour=ResourceValue(current=0, maximum=0),
        mana=ResourceValue(current=10, maximum=10),
        statuses=[StatusInstance(status_id=EntityId("guarded"), duration_remaining=1)],
        side=ParticipantSide.PARTY,
    )
    effect = EffectDefinition(
        effect_id=EntityId("cure"),
        kind=EffectKind.HEAL,
        magnitude=5,
    )

    updated_target, result = apply_effect(
        effect=effect,
        target_id=EntityId("hero"),
        target=hero,
    )

    assert result.applied
    assert updated_target.hp.current == 15
    assert any(s.status_id == EntityId("guarded") for s in updated_target.statuses)


def test_guarded_expires_at_turn_start() -> None:
    # Guarded with duration 1 expires at turn start
    hero = CombatParticipant(
        hp=ResourceValue(current=20, maximum=20),
        armour=ResourceValue(current=0, maximum=0),
        mana=ResourceValue(current=10, maximum=10),
        statuses=[StatusInstance(status_id=EntityId("guarded"), duration_remaining=1)],
        side=ParticipantSide.PARTY,
    )

    _updated_hero, remaining, prevent_action, logs = process_actor_statuses(hero)
    assert not prevent_action
    assert len(remaining) == 0
    assert any("Guarded expired" in log for log in logs)


def test_defend_validation_errors() -> None:
    combat = make_test_combat()

    # 1. Wrong turn
    with pytest.raises(ValueError, match="Not enemy's turn"):
        execute_defend_command(combat, EntityId("enemy"))

    # 2. Incapacitated (Stun)
    stunned_hero = combat.participants[EntityId("hero")].model_copy(
        update={"statuses": [StatusInstance(status_id=EntityId("stun"), duration_remaining=1)]}
    )
    combat_stunned = combat.model_copy(
        update={
            "participants": {
                EntityId("hero"): stunned_hero,
                EntityId("enemy"): combat.participants[EntityId("enemy")],
            }
        }
    )
    with pytest.raises(ValueError, match="is incapacitated"):
        execute_defend_command(combat_stunned, EntityId("hero"))
