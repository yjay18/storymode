"""Unit tests for COMBAT-08 combat resolution, victory rewards, and soft defeat."""

import pytest

from domain.models.character import StatBlock
from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.models.enemy import EnemyArchetype, LootEntry
from domain.models.player_state import PlayerState
from domain.models.runtime_common import InventoryEntry, ResourceValue
from domain.models.world_state import LocationState
from engine.combat.consequences import AuthoredConsequence
from engine.combat.resolution import (
    add_item_to_inventory,
    calculate_loot_drops,
    resolve_combat_if_terminal,
)
from engine.dice.testing import ScriptedRandomSource


def make_player(
    hp: int = 20, xp: int = 100, inventory: list[InventoryEntry] | None = None
) -> PlayerState:
    return PlayerState(
        id=EntityId("hero"),
        name=DisplayString("Hero"),
        background_id=EntityId("bg_hero"),
        stats=StatBlock(
            strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10
        ),
        hp=ResourceValue(current=hp, maximum=20),
        armour=ResourceValue(current=5, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        mana_regen=2,
        speed=10,
        luck_capacity=3,
        xp=xp,
        inventory=inventory or [],
    )


def make_enemy_archetype(
    arch_id: str = "wolf",
    power: int = 50,
    loot: list[LootEntry] | None = None,
) -> EnemyArchetype:
    return EnemyArchetype(
        id=EntityId(arch_id),
        name=DisplayString("Wolf"),
        description=DisplayString("A timber wolf"),
        base_hp=10,
        base_armour=2,
        speed=12,
        dexterity=14,
        base_mana=0,
        mana_regen=0,
        combat_skill_ids=[EntityId("bite")],
        behavior_profile=DisplayString("Aggressive"),
        escape_policy_id=EntityId("esc_wolf"),
        power_rating=power,
        loot_table=loot or [],
        portrait_prompt=DisplayString("A snarling wolf"),
        art_style_ref=DisplayString("dark_fantasy"),
    )


def test_add_item_to_inventory_stacking() -> None:
    inv = [InventoryEntry(item_id=EntityId("potion"), quantity=2)]

    # Adding existing item -> increases stack to 5
    inv = add_item_to_inventory(inv, EntityId("potion"), 3)
    assert len(inv) == 1
    assert inv[0].quantity == 5

    # Adding new item -> appends
    inv = add_item_to_inventory(inv, EntityId("herb"), 1)
    assert len(inv) == 2
    assert inv[1].item_id == EntityId("herb")
    assert inv[1].quantity == 1


def test_calculate_loot_drops_fixed_and_rng() -> None:
    table = [
        LootEntry(item_id=EntityId("pelt"), minimum_quantity=1, maximum_quantity=1, weight=1),
        LootEntry(item_id=EntityId("fang"), minimum_quantity=1, maximum_quantity=3, weight=1),
    ]

    # Without RNG -> minimums
    drops = calculate_loot_drops(table, rng=None)
    assert len(drops) == 2
    assert drops[0].quantity == 1
    assert drops[1].quantity == 1

    # With RNG: span for fang is 3 - 1 + 1 = 3. Roll 2 -> 1 + (2 % 3) = 3
    rng = ScriptedRandomSource([2])
    drops_rng = calculate_loot_drops(table, rng=rng)
    assert drops_rng[1].quantity == 3


def test_resolve_victory_grants_xp_and_loot() -> None:
    player = make_player(xp=50)
    location = LocationState(area_id=EntityId("forest"))
    wolf_arch = make_enemy_archetype(
        arch_id="wolf",
        power=40,
        loot=[
            LootEntry(
                item_id=EntityId("wolf_pelt"), minimum_quantity=2, maximum_quantity=2, weight=1
            )
        ],
    )
    archetypes = {EntityId("wolf"): wolf_arch}

    # Combat with 1 living hero and 1 defeated wolf
    hero = CombatParticipant(
        hp=ResourceValue(current=15, maximum=20),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=6, maximum=10),
        side=ParticipantSide.PARTY,
    )
    dead_wolf = CombatParticipant(
        hp=ResourceValue(current=0, maximum=10),
        armour=ResourceValue(current=0, maximum=2),
        mana=ResourceValue(current=0, maximum=0),
        side=ParticipantSide.ENEMY,
    )
    combat = CombatState(
        encounter_id=EntityId("enc_wolf"),
        phase=CombatPhase.ACTIVE,
        round=3,
        order=[EntityId("hero"), EntityId("wolf_1")],
        current_index=0,
        participants={
            EntityId("hero"): hero,
            EntityId("wolf_1"): dead_wolf,
        },
    )

    res = resolve_combat_if_terminal(
        combat=combat,
        player=player,
        location=location,
        world_flags={},
        encounter_history=[],
        enemy_archetypes=archetypes,
        victory_flags={EntityId("cleared_woods"): True},
    )

    assert res.is_resolved
    assert res.outcome == "Victory"
    assert res.combat is None
    assert res.player.xp == 90  # 50 + 40
    assert len(res.player.inventory) == 1
    assert res.player.inventory[0].item_id == EntityId("wolf_pelt")
    assert res.player.inventory[0].quantity == 2
    assert res.world_flags[EntityId("cleared_woods")] is True
    assert len(res.encounter_history) == 1
    assert res.encounter_history[0].encounter_id == EntityId("enc_wolf")
    assert res.encounter_history[0].round_count == 3


def test_resolve_soft_defeat_applies_consequence() -> None:
    player = make_player(hp=0)
    location = LocationState(area_id=EntityId("forest"))
    archetypes = {EntityId("wolf"): make_enemy_archetype()}

    # Hero at 0 HP
    dead_hero = CombatParticipant(
        hp=ResourceValue(current=0, maximum=20),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=0, maximum=10),
        side=ParticipantSide.PARTY,
    )
    living_wolf = CombatParticipant(
        hp=ResourceValue(current=8, maximum=10),
        armour=ResourceValue(current=2, maximum=2),
        mana=ResourceValue(current=0, maximum=0),
        side=ParticipantSide.ENEMY,
    )
    combat = CombatState(
        encounter_id=EntityId("enc_wolf"),
        phase=CombatPhase.ACTIVE,
        round=2,
        order=[EntityId("hero"), EntityId("wolf_1")],
        current_index=0,
        participants={
            EntityId("hero"): dead_hero,
            EntityId("wolf_1"): living_wolf,
        },
    )

    consequence = AuthoredConsequence(
        consequence_id=EntityId("rescued_by_hunter"),
        kind="relocation",
        description=DisplayString("A wandering hunter dragged you to his cabin."),
        relocation_area_id=EntityId("hunter_cabin"),
        world_flags={EntityId("rescued_by_hunter"): True},
    )

    res = resolve_combat_if_terminal(
        combat=combat,
        player=player,
        location=location,
        world_flags={},
        encounter_history=[],
        enemy_archetypes=archetypes,
        authored_consequence=consequence,
        is_endgame_encounter=False,
    )

    assert res.is_resolved
    assert res.outcome == "Defeat"
    assert res.combat is None
    # Soft defeat restores at least 1 HP
    assert res.player.hp.current == 1
    assert res.location.area_id == EntityId("hunter_cabin")
    assert res.world_flags[EntityId("rescued_by_hunter")] is True


def test_game_over_forbidden_in_standard_encounter() -> None:
    player = make_player(hp=0)
    location = LocationState(area_id=EntityId("forest"))
    dead_hero = CombatParticipant(
        hp=ResourceValue(current=0, maximum=20),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=0, maximum=10),
        side=ParticipantSide.PARTY,
    )
    living_enemy = CombatParticipant(
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=0),
        mana=ResourceValue(current=0, maximum=0),
        side=ParticipantSide.ENEMY,
    )
    combat = CombatState(
        encounter_id=EntityId("enc_wolf"),
        phase=CombatPhase.ACTIVE,
        round=1,
        order=[EntityId("hero"), EntityId("wolf_1")],
        current_index=0,
        participants={
            EntityId("hero"): dead_hero,
            EntityId("wolf_1"): living_enemy,
        },
    )

    consequence = AuthoredConsequence(
        consequence_id=EntityId("perma_death"),
        kind="game_over",
        description=DisplayString("You died."),
    )

    # Standard encounter -> game_over consequence must raise ValueError
    with pytest.raises(ValueError, match="True game-over is forbidden in non-endgame"):
        resolve_combat_if_terminal(
            combat=combat,
            player=player,
            location=location,
            world_flags={},
            encounter_history=[],
            enemy_archetypes={},
            authored_consequence=consequence,
            is_endgame_encounter=False,
        )


def test_game_over_allowed_in_endgame_encounter() -> None:
    player = make_player(hp=0)
    location = LocationState(area_id=EntityId("throne_room"))
    dead_hero = CombatParticipant(
        hp=ResourceValue(current=0, maximum=20),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=0, maximum=10),
        side=ParticipantSide.PARTY,
    )
    living_boss = CombatParticipant(
        hp=ResourceValue(current=50, maximum=100),
        armour=ResourceValue(current=10, maximum=20),
        mana=ResourceValue(current=10, maximum=10),
        side=ParticipantSide.ENEMY,
    )
    combat = CombatState(
        encounter_id=EntityId("enc_final_boss"),
        phase=CombatPhase.ACTIVE,
        round=5,
        order=[EntityId("hero"), EntityId("boss")],
        current_index=0,
        participants={
            EntityId("hero"): dead_hero,
            EntityId("boss"): living_boss,
        },
    )

    consequence = AuthoredConsequence(
        consequence_id=EntityId("final_defeat"),
        kind="game_over",
        description=DisplayString("The world falls into darkness."),
    )

    res = resolve_combat_if_terminal(
        combat=combat,
        player=player,
        location=location,
        world_flags={},
        encounter_history=[],
        enemy_archetypes={},
        authored_consequence=consequence,
        is_endgame_encounter=True,
    )

    assert res.is_resolved
    assert res.outcome == "Defeat"
    assert res.defeat_outcome is not None
    assert res.defeat_outcome.is_game_over is True
