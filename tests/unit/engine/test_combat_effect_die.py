"""Unit tests for COMBAT-05 combat effect die and bonus tables."""

import datetime

from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.models.runtime_common import KnownCombatSkill, ResourceValue
from domain.models.skill import (
    CombatSkill,
    CombatSkillLevel,
    EffectDefinition,
    EffectDieTable,
    EffectKind,
    TargetRule,
)
from engine.combat.skills import execute_skill_command
from engine.dice.effects import CombatEffectBand
from engine.dice.service import DiceService
from engine.dice.testing import ScriptedRandomSource


def make_skill_with_die_table() -> CombatSkill:
    base_eff = [
        EffectDefinition(
            effect_id=EntityId("slash_base"),
            kind=EffectKind.DAMAGE,
            magnitude=5,
        )
    ]
    die_table = EffectDieTable(
        natural_1=[
            EffectDefinition(
                effect_id=EntityId("slash_recoil"),
                kind=EffectKind.DAMAGE,
                magnitude=1,
            )
        ],
        low=[],  # No bonus
        standard=[
            EffectDefinition(
                effect_id=EntityId("slash_bleed"),
                kind=EffectKind.STATUS,
                magnitude=2,
                duration=2,
                status_id=EntityId("bleed"),
            )
        ],
        strong=[
            EffectDefinition(
                effect_id=EntityId("slash_bonus_dmg"),
                kind=EffectKind.DAMAGE,
                magnitude=4,
            )
        ],
        natural_20=[
            EffectDefinition(
                effect_id=EntityId("slash_crit_dmg"),
                kind=EffectKind.DAMAGE,
                magnitude=8,
            ),
            EffectDefinition(
                effect_id=EntityId("slash_crit_bleed"),
                kind=EffectKind.STATUS,
                magnitude=3,
                duration=2,
                status_id=EntityId("bleed"),
            ),
        ],
    )

    lvl = CombatSkillLevel(
        level=1,
        mana_cost=2,
        target_rule=TargetRule.SINGLE_ENEMY,
        base_effects=base_eff,
        effect_die=die_table,
    )
    levels = [
        lvl,
        CombatSkillLevel(
            level=2,
            mana_cost=2,
            target_rule=TargetRule.SINGLE_ENEMY,
            base_effects=base_eff,
            effect_die=die_table,
        ),
        CombatSkillLevel(
            level=3,
            mana_cost=2,
            target_rule=TargetRule.SINGLE_ENEMY,
            base_effects=base_eff,
            effect_die=die_table,
        ),
        CombatSkillLevel(
            level=4,
            mana_cost=2,
            target_rule=TargetRule.SINGLE_ENEMY,
            base_effects=base_eff,
            effect_die=die_table,
        ),
        CombatSkillLevel(
            level=5,
            mana_cost=2,
            target_rule=TargetRule.SINGLE_ENEMY,
            base_effects=base_eff,
            effect_die=die_table,
        ),
    ]

    return CombatSkill(
        id=EntityId("slash"),
        name=DisplayString("Slash"),
        description=DisplayString("Slash enemy with blade"),
        tags=[],
        acquisition_source_ids=[],
        levels=levels,
        allowed_actor_types=[],
    )


def make_test_combat(enemy_hp: int = 20, enemy_armour: int = 0) -> CombatState:
    hero = CombatParticipant(
        hp=ResourceValue(current=20, maximum=20),
        armour=ResourceValue(current=5, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        statuses=[],
        known_combat_skills=[
            KnownCombatSkill(
                skill_id=EntityId("slash"), level=1, acquisition_source_id=EntityId("tree")
            ),
        ],
        combat_loadout=[EntityId("slash")],
        side=ParticipantSide.PARTY,
    )
    enemy = CombatParticipant(
        hp=ResourceValue(current=enemy_hp, maximum=enemy_hp),
        armour=ResourceValue(current=enemy_armour, maximum=enemy_armour),
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


def make_dice_service(rolls: list[int]) -> DiceService:
    rng = ScriptedRandomSource(rolls)

    def clock() -> datetime.datetime:
        return datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)

    def id_gen() -> EntityId:
        return EntityId("roll_1")

    return DiceService(rng=rng, clock=clock, id_generator=id_gen)


def test_effect_die_natural_1_drawback_preserves_base() -> None:
    combat = make_test_combat(enemy_hp=20)
    skill = make_skill_with_die_table()
    skills_map = {EntityId("slash"): skill}

    dice_service = make_dice_service([1])  # Roll Natural 1

    result = execute_skill_command(
        combat=combat,
        actor_id=EntityId("hero"),
        skill_id=EntityId("slash"),
        target_ids=[EntityId("enemy")],
        skills_by_id=skills_map,
        dice_service=dice_service,
    )

    assert result.success
    assert result.effect_die_roll == 1
    assert result.effect_die_band == CombatEffectBand.NATURAL_1
    assert len(result.base_effect_results) == 1
    assert result.base_effect_results[0].applied
    # 5 base damage + 1 drawback damage = 6 total damage
    enemy_after = result.combat_state.participants[EntityId("enemy")]
    assert enemy_after.hp.current == 14  # 20 - 5 - 1


def test_effect_die_low_band() -> None:
    combat = make_test_combat(enemy_hp=20)
    skill = make_skill_with_die_table()
    skills_map = {EntityId("slash"): skill}

    dice_service = make_dice_service([5])  # Roll 5 (Low: 2-9)

    result = execute_skill_command(
        combat=combat,
        actor_id=EntityId("hero"),
        skill_id=EntityId("slash"),
        target_ids=[EntityId("enemy")],
        skills_by_id=skills_map,
        dice_service=dice_service,
    )

    assert result.effect_die_roll == 5
    assert result.effect_die_band == CombatEffectBand.LOW
    assert len(result.bonus_effect_results) == 0
    enemy_after = result.combat_state.participants[EntityId("enemy")]
    assert enemy_after.hp.current == 15  # Only 5 base damage


def test_effect_die_standard_band() -> None:
    combat = make_test_combat(enemy_hp=20)
    skill = make_skill_with_die_table()
    skills_map = {EntityId("slash"): skill}

    dice_service = make_dice_service([12])  # Roll 12 (Standard: 10-14)

    result = execute_skill_command(
        combat=combat,
        actor_id=EntityId("hero"),
        skill_id=EntityId("slash"),
        target_ids=[EntityId("enemy")],
        skills_by_id=skills_map,
        dice_service=dice_service,
    )

    assert result.effect_die_roll == 12
    assert result.effect_die_band == CombatEffectBand.STANDARD
    assert len(result.bonus_effect_results) == 1
    # Bleed status applied
    enemy_after = result.combat_state.participants[EntityId("enemy")]
    assert enemy_after.hp.current == 15
    assert any(s.status_id == EntityId("bleed") for s in enemy_after.statuses)


def test_effect_die_strong_band() -> None:
    combat = make_test_combat(enemy_hp=20)
    skill = make_skill_with_die_table()
    skills_map = {EntityId("slash"): skill}

    dice_service = make_dice_service([17])  # Roll 17 (Strong: 15-19)

    result = execute_skill_command(
        combat=combat,
        actor_id=EntityId("hero"),
        skill_id=EntityId("slash"),
        target_ids=[EntityId("enemy")],
        skills_by_id=skills_map,
        dice_service=dice_service,
    )

    assert result.effect_die_roll == 17
    assert result.effect_die_band == CombatEffectBand.STRONG
    # 5 base damage + 4 strong bonus damage = 9 total damage
    enemy_after = result.combat_state.participants[EntityId("enemy")]
    assert enemy_after.hp.current == 11


def test_effect_die_natural_20_band() -> None:
    combat = make_test_combat(enemy_hp=20)
    skill = make_skill_with_die_table()
    skills_map = {EntityId("slash"): skill}

    dice_service = make_dice_service([20])  # Roll Natural 20

    result = execute_skill_command(
        combat=combat,
        actor_id=EntityId("hero"),
        skill_id=EntityId("slash"),
        target_ids=[EntityId("enemy")],
        skills_by_id=skills_map,
        dice_service=dice_service,
    )

    assert result.effect_die_roll == 20
    assert result.effect_die_band == CombatEffectBand.NATURAL_20
    # 5 base + 8 crit = 13 dmg, plus bleed
    enemy_after = result.combat_state.participants[EntityId("enemy")]
    assert enemy_after.hp.current == 7
    assert any(s.status_id == EntityId("bleed") for s in enemy_after.statuses)
    assert len(result.roll_records) == 1
    assert EntityId("slash_crit_dmg") in result.roll_records[0].confirmed_effect_ids


def test_effect_die_skipped_if_target_defeated_by_base() -> None:
    combat = make_test_combat(enemy_hp=4)  # Enemy has only 4 HP, base does 5 damage
    skill = make_skill_with_die_table()
    skills_map = {EntityId("slash"): skill}

    dice_service = make_dice_service([20])  # Would be a 20, but target dies to base

    result = execute_skill_command(
        combat=combat,
        actor_id=EntityId("hero"),
        skill_id=EntityId("slash"),
        target_ids=[EntityId("enemy")],
        skills_by_id=skills_map,
        dice_service=dice_service,
    )

    # Effect die is not rolled because target was already defeated by base
    assert result.effect_die_roll is None
    assert result.effect_die_band is None
    assert len(result.roll_records) == 0
    assert result.combat_state.participants[EntityId("enemy")].hp.current == 0
