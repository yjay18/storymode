"""Integration tests for COMBAT-09 full combat pipeline and use cases."""

import datetime

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.combat_state import CombatPhase
from domain.models.common import DisplayString, EntityId, SemanticVersion
from domain.models.enemy import EnemyArchetype, LootEntry
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import KnownCombatSkill, ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.skill import (
    CombatSkill,
    CombatSkillLevel,
    EffectDefinition,
    EffectKind,
    TargetRule,
)
from domain.models.world_state import LocationState
from engine.combat.consequences import AuthoredConsequence
from engine.combat.escape import EscapePolicyDefinition, YieldPolicyDefinition
from engine.combat.use_cases import CombatUseCases
from engine.dice.checks import ExplorationBand
from engine.dice.service import DiceService
from engine.dice.testing import ScriptedRandomSource


def make_skill(
    skill_id: str,
    target_rule: TargetRule = TargetRule.SINGLE_ENEMY,
    mana_cost: int = 2,
    damage: int = 6,
) -> CombatSkill:
    effects = [
        EffectDefinition(
            effect_id=EntityId(f"{skill_id}_eff"),
            kind=EffectKind.DAMAGE,
            magnitude=damage,
        )
    ]
    levels = [
        CombatSkillLevel(
            level=lvl,
            mana_cost=mana_cost,
            target_rule=target_rule,
            base_effects=effects,
        )
        for lvl in range(1, 6)
    ]
    return CombatSkill(
        id=EntityId(skill_id),
        name=DisplayString(skill_id.title()),
        description=DisplayString(f"A {skill_id} skill"),
        tags=[],
        acquisition_source_ids=[],
        levels=levels,
        allowed_actor_types=[DisplayString("protagonist"), DisplayString("enemy")],
    )


def make_initial_state(hp: int = 20) -> RuntimeState:
    player = PlayerState(
        id=EntityId("hero"),
        name=DisplayString("Hero"),
        background_id=EntityId("bg_warrior"),
        stats=StatBlock(
            strength=14, dexterity=12, constitution=12, intelligence=10, wisdom=10, charisma=10
        ),
        hp=ResourceValue(current=hp, maximum=20),
        armour=ResourceValue(current=5, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        mana_regen=2,
        speed=14,  # Hero goes first (speed 14 vs goblin speed 10)
        luck_capacity=3,
        known_combat_skills=[
            KnownCombatSkill(
                skill_id=EntityId("slash"),
                level=1,
                acquisition_source_id=EntityId("bg_warrior"),
            )
        ],
        combat_loadout=[EntityId("slash")],
    )
    location = LocationState(area_id=EntityId("forest_trail"))
    party = PartyState(protagonist_id=EntityId("hero"), active_companion_ids=[])
    plot = PlotState()
    return RuntimeState(
        campaign_id=EntityId("camp_1"),
        campaign_version=SemanticVersion("1.0.0"),
        campaign_fingerprint="fp_123",
        save_id=EntityId("save_1"),
        player=player,
        party=party,
        location=location,
        plot=plot,
        difficulty=DefaultDifficulty.NORMAL,
        revision=1,
    )


def make_test_fixture(rolls: list[int] | None = None) -> tuple[CombatUseCases, RuntimeState]:
    slash_skill = make_skill("slash", damage=8, mana_cost=2)
    bite_skill = make_skill("bite", damage=4, mana_cost=0)

    skills = {
        EntityId("slash"): slash_skill,
        EntityId("bite"): bite_skill,
    }
    goblin = EnemyArchetype(
        id=EntityId("goblin"),
        name=DisplayString("Goblin"),
        description=DisplayString("A sly goblin"),
        base_hp=10,
        base_armour=2,
        speed=10,
        dexterity=10,
        base_mana=0,
        mana_regen=0,
        combat_skill_ids=[EntityId("bite")],
        behavior_profile=DisplayString("Aggressive"),
        escape_policy_id=EntityId("esc_goblin"),
        power_rating=30,
        loot_table=[
            LootEntry(
                item_id=EntityId("goblin_ear"),
                minimum_quantity=1,
                maximum_quantity=1,
                weight=1,
            )
        ],
        portrait_prompt=DisplayString("Goblin"),
        art_style_ref=DisplayString("dark_fantasy"),
    )
    enemy_archetypes = {EntityId("goblin"): goblin}

    rng = ScriptedRandomSource(rolls or [10, 10, 10])

    def clock() -> datetime.datetime:
        return datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)

    def id_gen() -> EntityId:
        return EntityId("roll_1")

    dice_service = DiceService(rng=rng, clock=clock, id_generator=id_gen)

    escape_policy = EscapePolicyDefinition(
        id=EntityId("enc_goblin"),
        dc=10,
        consequences={
            ExplorationBand.SUCCESS: AuthoredConsequence(
                consequence_id=EntityId("escaped_goblin"),
                kind="escape",
                description=DisplayString("Fled from the goblin!"),
                world_flags={EntityId("fled_goblin"): True},
            ),
        },
    )
    yield_policy = YieldPolicyDefinition(
        id=EntityId("enc_goblin"),
        allowed=True,
        consequence=AuthoredConsequence(
            consequence_id=EntityId("goblin_hostage"),
            kind="capture",
            description=DisplayString("Surrendered to the goblin."),
            relocation_area_id=EntityId("goblin_cage"),
        ),
    )
    defeat_consequence = AuthoredConsequence(
        consequence_id=EntityId("left_for_dead"),
        kind="relocation",
        description=DisplayString("Left knocked out in the dirt."),
        relocation_area_id=EntityId("roadside"),
    )

    use_cases = CombatUseCases(
        skills=skills,
        enemy_archetypes=enemy_archetypes,
        dice_service=dice_service,
        rng=rng,
        escape_policies={EntityId("enc_goblin"): escape_policy},
        yield_policies={EntityId("enc_goblin"): yield_policy},
        defeat_consequences={EntityId("enc_goblin"): defeat_consequence},
    )

    state = make_initial_state()
    return use_cases, state


def test_full_combat_victory_pipeline() -> None:
    use_cases, state = make_test_fixture()

    # 1. Start combat
    res1 = use_cases.start_combat(
        state=state,
        encounter_id=EntityId("enc_goblin"),
        enemy_archetype_ids=[EntityId("goblin")],
        command_id=EntityId("cmd_start"),
        expected_revision=1,
    )
    assert res1.state.combat is not None
    assert res1.state.combat.phase == CombatPhase.ACTIVE
    assert res1.state.revision == 2
    assert len(res1.allowed_actions) > 0
    # Hero acts first (speed 14 vs 10)
    assert res1.state.combat.order[res1.state.combat.current_index] == EntityId("hero")
    enemy_target_id = res1.allowed_actions[0].valid_target_ids[0]

    # 2. Hero attacks goblin: goblin has 2 armour, 10 HP.
    # Slash does 8 damage -> 2 armour gone, 6 HP damage -> 4 HP left.
    # After hero turn, turn advances to goblin. Goblin AI bites hero (4 damage -> 4 armour).
    # Then turn advances back to hero!
    res2 = use_cases.execute_skill(
        state=res1.state,
        skill_id=EntityId("slash"),
        target_ids=[enemy_target_id],
        command_id=EntityId("cmd_slash_1"),
        expected_revision=2,
    )
    assert res2.state.combat is not None
    assert res2.state.revision == 3
    # Goblin has 4 HP left
    assert res2.state.combat.participants[enemy_target_id].hp.current == 4

    # 3. Hero attacks again: 8 damage kills goblin (4 HP -> 0 HP).
    # Side defeat detected -> Victory!
    res3 = use_cases.execute_skill(
        state=res2.state,
        skill_id=EntityId("slash"),
        target_ids=[enemy_target_id],
        command_id=EntityId("cmd_slash_2"),
        expected_revision=3,
    )
    assert res3.is_terminal
    assert res3.outcome == "Victory"
    assert res3.state.combat is None
    assert res3.state.player.xp == 30
    assert len(res3.state.player.inventory) == 1
    assert res3.state.player.inventory[0].item_id == EntityId("goblin_ear")
    assert len(res3.state.encounter_history) == 1
    assert res3.state.encounter_history[0].outcome == DisplayString("Victory")


def test_combat_idempotency_and_revision_conflicts() -> None:
    use_cases, state = make_test_fixture()

    # Start combat
    res1 = use_cases.start_combat(
        state=state,
        encounter_id=EntityId("enc_goblin"),
        enemy_archetype_ids=[EntityId("goblin")],
        command_id=EntityId("cmd_start"),
        expected_revision=1,
    )

    # Re-sending same command_id returns idempotent state
    res_idem = use_cases.start_combat(
        state=res1.state,
        encounter_id=EntityId("enc_goblin"),
        enemy_archetype_ids=[EntityId("goblin")],
        command_id=EntityId("cmd_start"),
        expected_revision=2,
    )
    assert res_idem.state.revision == res1.state.revision

    # Submitting with invalid revision raises ValueError
    with pytest.raises(ValueError, match="State revision conflict"):
        use_cases.execute_skill(
            state=res1.state,
            skill_id=EntityId("slash"),
            target_ids=[EntityId("goblin_1")],
            command_id=EntityId("cmd_wrong_rev"),
            expected_revision=999,
        )


def test_combat_defend_pipeline() -> None:
    use_cases, state = make_test_fixture()
    res1 = use_cases.start_combat(
        state=state,
        encounter_id=EntityId("enc_goblin"),
        enemy_archetype_ids=[EntityId("goblin")],
        command_id=EntityId("cmd_start"),
        expected_revision=1,
    )

    # Hero Defends (gets Guarded).
    # Then Goblin AI bites hero (4 damage with 25% Guarded reduction = 3 damage).
    res2 = use_cases.execute_defend(
        state=res1.state,
        command_id=EntityId("cmd_defend"),
        expected_revision=2,
    )
    assert res2.state.combat is not None
    # Hero armour absorbed 3 damage instead of 4
    assert res2.state.combat.participants[EntityId("hero")].armour.current == 2  # 5 - 3


def test_combat_flee_pipeline() -> None:
    use_cases, state = make_test_fixture(rolls=[15])  # 15 vs DC 10 -> Success
    res1 = use_cases.start_combat(
        state=state,
        encounter_id=EntityId("enc_goblin"),
        enemy_archetype_ids=[EntityId("goblin")],
        command_id=EntityId("cmd_start"),
        expected_revision=1,
    )

    res_flee = use_cases.execute_flee(
        state=res1.state,
        command_id=EntityId("cmd_flee"),
        expected_revision=2,
    )
    assert res_flee.is_terminal
    assert res_flee.outcome == "Escaped"
    assert res_flee.state.combat is None
    assert res_flee.state.world_flags[EntityId("fled_goblin")] is True


def test_combat_yield_pipeline() -> None:
    use_cases, state = make_test_fixture()
    res1 = use_cases.start_combat(
        state=state,
        encounter_id=EntityId("enc_goblin"),
        enemy_archetype_ids=[EntityId("goblin")],
        command_id=EntityId("cmd_start"),
        expected_revision=1,
    )

    res_yield = use_cases.execute_yield(
        state=res1.state,
        command_id=EntityId("cmd_yield"),
        expected_revision=2,
    )
    assert res_yield.is_terminal
    assert res_yield.outcome == "Yielded"
    assert res_yield.state.combat is None
    assert res_yield.state.location.area_id == EntityId("goblin_cage")


def test_combat_soft_defeat_pipeline() -> None:
    use_cases, state = make_test_fixture()
    # Hero starts with 1 HP and 0 armour
    fragile_player = state.player.model_copy(
        update={
            "hp": ResourceValue(current=1, maximum=20),
            "armour": ResourceValue(current=0, maximum=5),
        }
    )
    fragile_state = state.model_copy(update={"player": fragile_player})

    res1 = use_cases.start_combat(
        state=fragile_state,
        encounter_id=EntityId("enc_goblin"),
        enemy_archetype_ids=[EntityId("goblin")],
        command_id=EntityId("cmd_start"),
        expected_revision=1,
    )

    # Hero Defends -> then Goblin AI attacks for 3 damage -> 1 HP hero reaches 0 HP.
    # Defeat triggered -> Soft defeat consequence applied -> relocated to roadside.
    res2 = use_cases.execute_defend(
        state=res1.state,
        command_id=EntityId("cmd_defend"),
        expected_revision=2,
    )
    assert res2.is_terminal
    assert res2.outcome == "Defeat"
    assert res2.state.combat is None
    assert res2.state.player.hp.current == 1
    assert res2.state.location.area_id == EntityId("roadside")
