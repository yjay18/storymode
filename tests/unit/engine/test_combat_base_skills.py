"""Unit tests for COMBAT-04 skill commands and guaranteed base effects."""

import pytest

from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.models.runtime_common import KnownCombatSkill, ResourceValue, StatusInstance
from domain.models.skill import (
    CombatSkill,
    CombatSkillLevel,
    EffectDefinition,
    EffectKind,
    TargetRule,
)
from engine.combat.commands import CombatCommandKind, get_allowed_combat_actions
from engine.combat.skills import execute_skill_command


def make_skill(
    skill_id: str,
    target_rule: TargetRule = TargetRule.SINGLE_ENEMY,
    mana_cost: int = 2,
    base_effects: list[EffectDefinition] | None = None,
) -> CombatSkill:
    effects = base_effects or [
        EffectDefinition(
            effect_id=EntityId(f"{skill_id}_eff"),
            kind=EffectKind.DAMAGE,
            magnitude=6,
        )
    ]
    level = CombatSkillLevel(
        level=1,
        mana_cost=mana_cost,
        target_rule=target_rule,
        base_effects=effects,
    )
    # 5 levels
    levels = [
        level,
        CombatSkillLevel(
            level=2, mana_cost=mana_cost, target_rule=target_rule, base_effects=effects
        ),
        CombatSkillLevel(
            level=3, mana_cost=mana_cost, target_rule=target_rule, base_effects=effects
        ),
        CombatSkillLevel(
            level=4, mana_cost=mana_cost, target_rule=target_rule, base_effects=effects
        ),
        CombatSkillLevel(
            level=5, mana_cost=mana_cost, target_rule=target_rule, base_effects=effects
        ),
    ]
    return CombatSkill(
        id=EntityId(skill_id),
        name=DisplayString(skill_id.title()),
        description=DisplayString(f"A {skill_id} skill"),
        tags=[],
        acquisition_source_ids=[],
        levels=levels,
        allowed_actor_types=[],
    )


def make_test_combat() -> CombatState:
    hero = CombatParticipant(
        hp=ResourceValue(current=20, maximum=20),
        armour=ResourceValue(current=5, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        statuses=[],
        known_combat_skills=[
            KnownCombatSkill(
                skill_id=EntityId("strike"), level=1, acquisition_source_id=EntityId("tree")
            ),
            KnownCombatSkill(
                skill_id=EntityId("heal"), level=1, acquisition_source_id=EntityId("tree")
            ),
            KnownCombatSkill(
                skill_id=EntityId("cleave"), level=1, acquisition_source_id=EntityId("tree")
            ),
        ],
        combat_loadout=[EntityId("strike"), EntityId("heal"), EntityId("cleave")],
        side=ParticipantSide.PARTY,
    )
    enemy = CombatParticipant(
        hp=ResourceValue(current=15, maximum=15),
        armour=ResourceValue(current=4, maximum=4),
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
        escape_policy=EntityId("esc_1"),
    )


def test_execute_skill_valid_damage_and_armour_spill() -> None:
    combat = make_test_combat()
    strike_skill = make_skill(
        "strike",
        mana_cost=2,
        base_effects=[
            EffectDefinition(effect_id=EntityId("strike_dmg"), kind=EffectKind.DAMAGE, magnitude=7)
        ],
    )
    skills_map = {EntityId("strike"): strike_skill}

    # Strike enemy: 7 damage vs 4 armour -> 4 absorbed, 3 to HP -> enemy HP is 12/15, armour is 0/4
    result = execute_skill_command(
        combat=combat,
        actor_id=EntityId("hero"),
        skill_id=EntityId("strike"),
        target_ids=[EntityId("enemy")],
        skills_by_id=skills_map,
    )

    assert result.success
    assert result.mana_spent == 2
    assert result.combat_state.participants[EntityId("hero")].mana.current == 8

    enemy_after = result.combat_state.participants[EntityId("enemy")]
    assert enemy_after.armour.current == 0
    assert enemy_after.hp.current == 12


def test_execute_skill_guarded_reduction() -> None:
    combat = make_test_combat()
    # Enemy is Guarded
    enemy_guarded = combat.participants[EntityId("enemy")].model_copy(
        update={"statuses": [StatusInstance(status_id=EntityId("guarded"), duration_remaining=1)]}
    )
    combat = combat.model_copy(
        update={
            "participants": {
                EntityId("hero"): combat.participants[EntityId("hero")],
                EntityId("enemy"): enemy_guarded,
            }
        }
    )

    strike_skill = make_skill(
        "strike",
        mana_cost=2,
        base_effects=[
            EffectDefinition(effect_id=EntityId("strike_dmg"), kind=EffectKind.DAMAGE, magnitude=8)
        ],
    )
    skills_map = {EntityId("strike"): strike_skill}

    # 8 damage - 25% (2) = 6 damage. Enemy has 4 armour -> 4 absorbed, 2 to HP. Guarded is consumed.
    result = execute_skill_command(
        combat=combat,
        actor_id=EntityId("hero"),
        skill_id=EntityId("strike"),
        target_ids=[EntityId("enemy")],
        skills_by_id=skills_map,
    )

    enemy_after = result.combat_state.participants[EntityId("enemy")]
    assert enemy_after.armour.current == 0
    assert enemy_after.hp.current == 13  # 15 - 2
    assert len(enemy_after.statuses) == 0  # Guarded consumed


def test_execute_skill_multi_target_all_enemies() -> None:
    combat = make_test_combat()
    enemy_2 = CombatParticipant(
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=0),
        mana=ResourceValue(current=0, maximum=0),
        side=ParticipantSide.ENEMY,
    )
    new_parts = dict(combat.participants)
    new_parts[EntityId("enemy_2")] = enemy_2
    combat = combat.model_copy(
        update={
            "participants": new_parts,
            "order": [EntityId("hero"), EntityId("enemy"), EntityId("enemy_2")],
        }
    )

    cleave_skill = make_skill(
        "cleave",
        target_rule=TargetRule.ALL_ENEMIES,
        mana_cost=3,
        base_effects=[
            EffectDefinition(effect_id=EntityId("cleave_dmg"), kind=EffectKind.DAMAGE, magnitude=5)
        ],
    )
    skills_map = {EntityId("cleave"): cleave_skill}

    result = execute_skill_command(
        combat=combat,
        actor_id=EntityId("hero"),
        skill_id=EntityId("cleave"),
        target_ids=[],
        skills_by_id=skills_map,
    )

    assert result.success
    # Enemy 1: 5 dmg vs 4 armour -> 0 armour, 14 HP
    assert result.combat_state.participants[EntityId("enemy")].armour.current == 0
    assert result.combat_state.participants[EntityId("enemy")].hp.current == 14
    # Enemy 2: 5 dmg vs 0 armour -> 0 armour, 5 HP
    assert result.combat_state.participants[EntityId("enemy_2")].hp.current == 5


def test_execute_skill_explicit_immunity() -> None:
    combat = make_test_combat()
    strike_skill = make_skill(
        "strike",
        mana_cost=2,
        base_effects=[
            EffectDefinition(effect_id=EntityId("strike_dmg"), kind=EffectKind.DAMAGE, magnitude=10)
        ],
    )
    skills_map = {EntityId("strike"): strike_skill}

    result = execute_skill_command(
        combat=combat,
        actor_id=EntityId("hero"),
        skill_id=EntityId("strike"),
        target_ids=[EntityId("enemy")],
        skills_by_id=skills_map,
        immunities_by_id={EntityId("enemy"): {EntityId("strike_dmg")}},
    )

    assert result.success
    # Target immune: HP and armour unmutated
    enemy_after = result.combat_state.participants[EntityId("enemy")]
    assert enemy_after.hp.current == 15
    assert enemy_after.armour.current == 4


def test_execute_skill_validation_failures() -> None:
    combat = make_test_combat()
    strike_skill = make_skill("strike", mana_cost=2)
    skills_map = {EntityId("strike"): strike_skill}

    # 1. Wrong turn (enemy attempts to act on hero's turn)
    with pytest.raises(ValueError, match="Not enemy's turn"):
        execute_skill_command(
            combat, EntityId("enemy"), EntityId("strike"), [EntityId("hero")], skills_map
        )

    # 2. Insufficient mana
    low_mana_hero = combat.participants[EntityId("hero")].model_copy(
        update={"mana": ResourceValue(current=1, maximum=10)}
    )
    combat_low_mana = combat.model_copy(
        update={
            "participants": {
                EntityId("hero"): low_mana_hero,
                EntityId("enemy"): combat.participants[EntityId("enemy")],
            }
        }
    )
    with pytest.raises(ValueError, match="Insufficient mana"):
        execute_skill_command(
            combat_low_mana, EntityId("hero"), EntityId("strike"), [EntityId("enemy")], skills_map
        )

    # 3. Invalid target (single_enemy targeting self)
    with pytest.raises(ValueError, match="Target hero is invalid"):
        execute_skill_command(
            combat, EntityId("hero"), EntityId("strike"), [EntityId("hero")], skills_map
        )

    # 4. Unequipped skill
    with pytest.raises(ValueError, match="is not equipped"):
        execute_skill_command(
            combat, EntityId("hero"), EntityId("fireball"), [EntityId("enemy")], skills_map
        )

    # 5. Incapacitated actor (Stun)
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
        execute_skill_command(
            combat_stunned, EntityId("hero"), EntityId("strike"), [EntityId("enemy")], skills_map
        )


def test_get_allowed_combat_actions() -> None:
    combat = make_test_combat()
    strike_skill = make_skill("strike", mana_cost=2)
    heal_skill = make_skill("heal", target_rule=TargetRule.SINGLE_ALLY, mana_cost=3)
    skills_map = {
        EntityId("strike"): strike_skill,
        EntityId("heal"): heal_skill,
    }

    actions = get_allowed_combat_actions(combat, EntityId("hero"), skills_map, can_act=True)
    kinds = [a.action_kind for a in actions]

    assert CombatCommandKind.USE_SKILL in kinds
    assert CombatCommandKind.DEFEND in kinds
    assert CombatCommandKind.FLEE in kinds
    assert len([a for a in actions if a.action_kind == CombatCommandKind.USE_SKILL]) == 2
