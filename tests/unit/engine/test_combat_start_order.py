"""Unit tests for COMBAT-02 encounter initialization and deterministic turn order."""

import datetime
from typing import Any

import pytest

from domain.models.area import EncounterEntry
from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import CompanionDefinition, StatBlock
from domain.models.combat_state import CombatPhase, ParticipantSide, TieBreakRecord
from domain.models.common import DisplayString, EntityId
from domain.models.enemy import EnemyArchetype
from domain.models.party_state import CompanionRuntimeState, LifeState, PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import KnownCombatSkill, ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState
from engine.combat.encounter import start_combat_encounter
from engine.combat.turn_order import ParticipantInitiative, calculate_turn_order
from engine.dice.service import DiceService
from engine.dice.testing import ScriptedRandomSource


def make_test_state(
    player_hp: int = 20,
    player_speed: int = 10,
    player_dex: int = 14,
    active_companion_ids: list[EntityId] | None = None,
    companions: dict[EntityId, CompanionRuntimeState] | None = None,
    with_active_combat: bool = False,
) -> RuntimeState:
    stats = StatBlock(
        strength=10,
        dexterity=player_dex,
        intelligence=10,
        charisma=10,
        constitution=10,
        wisdom=10,
    )
    player = PlayerState(
        id=EntityId("hero"),
        name=DisplayString("Hero"),
        background_id=EntityId("bg_soldier"),
        stats=stats,
        hp=ResourceValue(current=player_hp, maximum=20),
        armour=ResourceValue(current=5, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        mana_regen=2,
        speed=player_speed,
        luck_current=2,
        luck_capacity=2,
        known_combat_skills=[
            KnownCombatSkill(
                skill_id=EntityId("slash"),
                level=1,
                acquisition_source_id=EntityId("combat"),
            )
        ],
        combat_loadout=[EntityId("slash")],
    )

    party = PartyState(
        protagonist_id=EntityId("hero"),
        active_companion_ids=active_companion_ids or [],
        companions=companions or {},
    )

    location = LocationState(
        area_id=EntityId("area_1"),
    )

    combat_state = None
    if with_active_combat:
        from domain.models.combat_state import CombatState

        combat_state = CombatState(
            encounter_id=EntityId("enc_old"),
            phase=CombatPhase.ACTIVE,
            order=[EntityId("hero")],
            participants={
                EntityId("hero"): player_to_participant(player),
            },
        )

    return RuntimeState(
        campaign_id=EntityId("test_camp"),
        campaign_version=DisplayString("1.0.0"),
        campaign_fingerprint="abc",
        save_id=EntityId("save_1"),
        revision=1,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=party,
        location=location,
        plot=PlotState(),
        combat=combat_state,
    )


def player_to_participant(player: PlayerState) -> Any:
    from domain.models.combat_state import CombatParticipant

    return CombatParticipant(
        hp=player.hp,
        armour=player.armour,
        mana=player.mana,
        statuses=[],
        known_combat_skills=list(player.known_combat_skills),
        combat_loadout=list(player.combat_loadout),
        side=ParticipantSide.PARTY,
    )


def make_enemy(
    enemy_id: str = "goblin",
    speed: int = 8,
    dex: int = 12,
    base_hp: int = 10,
    base_armour: int = 2,
    base_mana: int = 0,
) -> EnemyArchetype:
    return EnemyArchetype(
        id=EntityId(enemy_id),
        name=DisplayString("Goblin"),
        description=DisplayString("A vicious goblin"),
        base_hp=base_hp,
        base_armour=base_armour,
        speed=speed,
        dexterity=dex,
        base_mana=base_mana,
        mana_regen=0,
        combat_skill_ids=[EntityId("stab")],
        behavior_profile=DisplayString("aggressive"),
        escape_policy_id=EntityId("flee_easy"),
        power_rating=10,
        loot_table=[],
        portrait_prompt=DisplayString("prompt"),
        art_style_ref=DisplayString("style"),
    )


def test_turn_order_speed_and_dexterity() -> None:
    # Actor 1: speed 12, dex 10
    # Actor 2: speed 10, dex 14
    # Actor 3: speed 10, dex 12
    initiatives = [
        ParticipantInitiative(participant_id=EntityId("actor_2"), speed=10, dexterity=14),
        ParticipantInitiative(participant_id=EntityId("actor_1"), speed=12, dexterity=10),
        ParticipantInitiative(participant_id=EntityId("actor_3"), speed=10, dexterity=12),
    ]

    res = calculate_turn_order(initiatives)
    assert res.order == [EntityId("actor_1"), EntityId("actor_2"), EntityId("actor_3")]
    assert len(res.tie_break_records) == 0


def test_turn_order_tie_break_with_rng() -> None:
    # Actor A and Actor B have same speed and dex
    # RNG gives 15 to Actor A and 8 to Actor B -> Actor A goes first
    initiatives = [
        ParticipantInitiative(participant_id=EntityId("actor_a"), speed=10, dexterity=10),
        ParticipantInitiative(participant_id=EntityId("actor_b"), speed=10, dexterity=10),
    ]
    rng = ScriptedRandomSource([15, 8])
    res = calculate_turn_order(initiatives, rng=rng)

    assert res.order == [EntityId("actor_a"), EntityId("actor_b")]
    assert len(res.tie_break_records) == 2
    assert res.tie_break_records[0].participant_id == EntityId("actor_a")
    assert res.tie_break_records[0].roll_total == 15
    assert res.tie_break_records[1].participant_id == EntityId("actor_b")
    assert res.tie_break_records[1].roll_total == 8


def test_turn_order_tie_break_equal_roll_id_fallback() -> None:
    # Actor Z and Actor A tie on speed, dex, and roll (both 10)
    # Alphabetical fallback orders 'actor_a' before 'actor_z'
    initiatives = [
        ParticipantInitiative(participant_id=EntityId("actor_z"), speed=10, dexterity=10),
        ParticipantInitiative(participant_id=EntityId("actor_a"), speed=10, dexterity=10),
    ]
    rng = ScriptedRandomSource([10, 10])
    res = calculate_turn_order(initiatives, rng=rng)

    assert res.order == [EntityId("actor_a"), EntityId("actor_z")]


def test_turn_order_preserves_existing_tie_breaks() -> None:
    # Existing tie breaks: actor_b has 18, actor_a has 5
    initiatives = [
        ParticipantInitiative(participant_id=EntityId("actor_a"), speed=10, dexterity=10),
        ParticipantInitiative(participant_id=EntityId("actor_b"), speed=10, dexterity=10),
    ]
    existing = [
        TieBreakRecord(participant_id=EntityId("actor_a"), roll_total=5),
        TieBreakRecord(participant_id=EntityId("actor_b"), roll_total=18),
    ]
    res = calculate_turn_order(initiatives, existing_tie_breaks=existing)

    assert res.order == [EntityId("actor_b"), EntityId("actor_a")]
    assert len(res.tie_break_records) == 2


def test_turn_order_audit_records_with_dice_service() -> None:
    initiatives = [
        ParticipantInitiative(participant_id=EntityId("hero"), speed=10, dexterity=10),
        ParticipantInitiative(participant_id=EntityId("enemy"), speed=10, dexterity=10),
    ]
    rng = ScriptedRandomSource([12, 16])
    clock_time = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    dice_svc = DiceService(
        rng=rng,
        clock=lambda: clock_time,
        id_generator=lambda: EntityId("roll_1"),
    )

    res = calculate_turn_order(
        initiatives,
        dice_service=dice_svc,
        transaction_id=EntityId("tx_1"),
        revision=2,
        command_id=EntityId("cmd_1"),
    )

    assert res.order == [EntityId("enemy"), EntityId("hero")]
    assert len(res.roll_records) == 2
    assert res.roll_records[0].transaction_id == EntityId("tx_1")


def test_start_combat_encounter_hero_and_enemy() -> None:
    state = make_test_state(player_hp=20, player_speed=12, player_dex=14)
    enemy = make_enemy("goblin_1", speed=8, dex=10, base_hp=10)
    encounter = EncounterEntry(
        id=EntityId("enc_1"),
        enemy_archetype_ids=[EntityId("goblin_1")],
        condition=DisplayString("always"),
        weight=1,
        escape_policy_id=EntityId("esc_flee"),
        consequence_ids=[],
    )

    combat, _rolls = start_combat_encounter(
        state=state,
        encounter=encounter,
        enemies_by_id={EntityId("goblin_1"): enemy},
        difficulty=DefaultDifficulty.NORMAL,
    )

    assert combat.encounter_id == EntityId("enc_1")
    assert combat.phase == CombatPhase.ACTIVE
    assert combat.round == 1
    assert combat.current_index == 0
    assert combat.order == [EntityId("hero"), EntityId("goblin_1")]
    assert len(combat.participants) == 2

    hero_p = combat.participants[EntityId("hero")]
    assert hero_p.side == ParticipantSide.PARTY
    assert hero_p.hp.current == 20

    gob_p = combat.participants[EntityId("goblin_1")]
    assert gob_p.side == ParticipantSide.ENEMY
    assert gob_p.hp.current == 10
    assert gob_p.armour.current == 2


def test_start_combat_difficulty_scaling() -> None:
    state = make_test_state()
    enemy = make_enemy("orc", base_hp=20, speed=5, dex=10)
    encounter = EncounterEntry(
        id=EntityId("enc_orc"),
        enemy_archetype_ids=[EntityId("orc")],
        condition=DisplayString("always"),
        weight=1,
        escape_policy_id=EntityId("esc_flee"),
        consequence_ids=[],
    )

    # Story: 20 * 7/10 = 14
    combat_story, _ = start_combat_encounter(
        state=state,
        encounter=encounter,
        enemies_by_id={EntityId("orc"): enemy},
        difficulty=DefaultDifficulty.STORY,
    )
    assert combat_story.participants[EntityId("orc")].hp.current == 14

    # Hard: 20 * 5/4 = 25
    combat_hard, _ = start_combat_encounter(
        state=state,
        encounter=encounter,
        enemies_by_id={EntityId("orc"): enemy},
        difficulty=DefaultDifficulty.HARD,
    )
    assert combat_hard.participants[EntityId("orc")].hp.current == 25


def test_start_combat_duplicate_enemy_archetypes() -> None:
    state = make_test_state(player_speed=5)
    enemy = make_enemy("goblin", speed=10, dex=10)
    encounter = EncounterEntry(
        id=EntityId("enc_gobs"),
        enemy_archetype_ids=[EntityId("goblin"), EntityId("goblin")],
        condition=DisplayString("always"),
        weight=1,
        escape_policy_id=EntityId("esc_flee"),
        consequence_ids=[],
    )
    rng = ScriptedRandomSource([15, 10])

    combat, _ = start_combat_encounter(
        state=state,
        encounter=encounter,
        enemies_by_id={EntityId("goblin"): enemy},
        rng=rng,
    )

    assert len(combat.participants) == 3
    assert EntityId("goblin_1") in combat.participants
    assert EntityId("goblin_2") in combat.participants
    assert combat.order[0] == EntityId("goblin_1")  # roll 15 > roll 10
    assert combat.order[1] == EntityId("goblin_2")
    assert combat.order[2] == EntityId("hero")


def test_start_combat_with_living_and_dead_companions() -> None:
    comp_alive = CompanionRuntimeState(
        id=EntityId("comp_alive"),
        hp=ResourceValue(current=15, maximum=15),
        armour=ResourceValue(current=2, maximum=2),
        mana=ResourceValue(current=5, maximum=5),
        is_available=True,
        life_state=LifeState.ALIVE,
    )
    comp_downed = CompanionRuntimeState(
        id=EntityId("comp_downed"),
        hp=ResourceValue(current=0, maximum=15),
        armour=ResourceValue(current=0, maximum=2),
        mana=ResourceValue(current=5, maximum=5),
        is_available=True,
        life_state=LifeState.ALIVE,
    )
    comp_dead = CompanionRuntimeState(
        id=EntityId("comp_dead"),
        hp=ResourceValue(current=0, maximum=15),
        armour=ResourceValue(current=0, maximum=2),
        mana=ResourceValue(current=5, maximum=5),
        is_available=False,
        life_state=LifeState.DEAD,
    )

    stats = StatBlock(
        strength=10, dexterity=12, intelligence=10, charisma=10, constitution=10, wisdom=10
    )
    comp_def = CompanionDefinition(
        id=EntityId("comp_alive"),
        name=DisplayString("Companion"),
        role=DisplayString("Mage"),
        home_area_id=EntityId("area_1"),
        knowledge_tags=[],
        goal=DisplayString("Help"),
        interaction_hooks=[],
        combat_role=DisplayString("Caster"),
        base_stats=stats,
        skill_tree_id=EntityId("tree_1"),
        starting_skill_ids=[EntityId("spark")],
        starting_loadout=[EntityId("spark")],
        relationship_rules=[],
        story_hook_ids=[],
        availability_rules=[],
        minimum_usable_actions=1,
    )

    state = make_test_state(
        active_companion_ids=[EntityId("comp_alive"), EntityId("comp_downed")],
        companions={
            EntityId("comp_alive"): comp_alive,
            EntityId("comp_downed"): comp_downed,
            EntityId("comp_dead"): comp_dead,
        },
    )

    enemy = make_enemy("goblin", speed=4)
    encounter = EncounterEntry(
        id=EntityId("enc_1"),
        enemy_archetype_ids=[EntityId("goblin")],
        condition=DisplayString("always"),
        weight=1,
        escape_policy_id=EntityId("esc_flee"),
        consequence_ids=[],
    )

    combat, _ = start_combat_encounter(
        state=state,
        encounter=encounter,
        enemies_by_id={EntityId("goblin"): enemy},
        companions_by_id={EntityId("comp_alive"): comp_def},
    )

    # Hero (10 speed), comp_alive (0 speed), goblin (4 speed)
    # comp_downed (0 HP) and comp_dead (dead/inactive) must be skipped!
    assert EntityId("comp_dead") not in combat.participants
    assert EntityId("comp_downed") not in combat.participants
    assert EntityId("comp_alive") in combat.participants
    assert combat.order == [EntityId("hero"), EntityId("goblin"), EntityId("comp_alive")]


def test_start_combat_validation_failures() -> None:
    # 1. Combat already active
    state_combat = make_test_state(with_active_combat=True)
    enemy = make_enemy("goblin")
    encounter = EncounterEntry(
        id=EntityId("enc_1"),
        enemy_archetype_ids=[EntityId("goblin")],
        condition=DisplayString("always"),
        weight=1,
        escape_policy_id=EntityId("esc_flee"),
        consequence_ids=[],
    )
    with pytest.raises(ValueError, match="Combat is already active"):
        start_combat_encounter(state_combat, encounter, {EntityId("goblin"): enemy})

    # 2. Hero is dead (0 HP)
    state_dead = make_test_state(player_hp=0)
    with pytest.raises(ValueError, match="Protagonist has 0 HP"):
        start_combat_encounter(state_dead, encounter, {EntityId("goblin"): enemy})

    # 3. Missing enemy definition
    state_valid = make_test_state()
    with pytest.raises(ValueError, match="Enemy archetype goblin not found"):
        start_combat_encounter(state_valid, encounter, {})
