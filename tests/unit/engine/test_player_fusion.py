"""Tests for player fusion transactions (PROG-03)."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import MilestoneState, PlotState
from domain.models.runtime_common import InventoryEntry, KnownCombatSkill, ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.skill import (
    CombatSkill,
    CombatSkillLevel,
    EffectDefinition,
    EffectKind,
    FusionRecipe,
    TargetRule,
)
from domain.models.world_state import LocationState, NpcOverride
from engine.progression.fusion import execute_player_fusion

# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

_STATS = StatBlock(
    strength=10,
    dexterity=10,
    intelligence=10,
    charisma=10,
    constitution=10,
    wisdom=10,
)
_RES = ResourceValue(current=10, maximum=10)
_ZERO = ResourceValue(current=0, maximum=5)


def _make_skill(skill_id: str) -> CombatSkill:
    eff = EffectDefinition(
        effect_id=EntityId(f"{skill_id}-eff"),
        kind=EffectKind.DAMAGE,
        magnitude=5,
    )
    levels = [
        CombatSkillLevel(
            level=i,
            mana_cost=2,
            target_rule=TargetRule.SINGLE_ENEMY,
            base_effects=[eff],
        )
        for i in range(1, 6)
    ]
    return CombatSkill(
        id=EntityId(skill_id),
        name=DisplayString(skill_id.title()),
        description=DisplayString("Skill description"),
        tags=[],
        acquisition_source_ids=[],
        levels=levels,
        allowed_actor_types=[],
    )


def _make_recipe(
    recipe_id: str = "rec-fusion-1",
    sources: tuple[str, str] = ("slash", "fireball"),
    result: str = "flame_strike",
    catalyst: str = "fire_gem",
    catalyst_qty: int = 2,
    location_or_specialist: list[str] | None = None,
    unlock_conditions: list[str] | None = None,
) -> FusionRecipe:
    src_sorted = sorted([EntityId(sources[0]), EntityId(sources[1])])
    return FusionRecipe(
        id=EntityId(recipe_id),
        source_skill_ids=src_sorted,
        result_skill_id=EntityId(result),
        catalyst_item_id=EntityId(catalyst),
        catalyst_quantity=catalyst_qty,
        unlock_conditions=[DisplayString(c) for c in (unlock_conditions or [])],
        location_or_specialist_ids=[
            EntityId(s) for s in (location_or_specialist or ["forge-area"])
        ],
        power_budget=20,
    )


def _make_state(
    known_skills: list[KnownCombatSkill] | None = None,
    loadout: list[str] | None = None,
    inventory: list[tuple[str, int]] | None = None,
    area_id: str = "forge-area",
    in_combat: bool = False,
    facts: set[EntityId] | None = None,
    resolved_milestones: set[EntityId] | None = None,
    npc_overrides: dict[EntityId, NpcOverride] | None = None,
) -> RuntimeState:
    inv_entries = [
        InventoryEntry(item_id=EntityId(item_id), quantity=qty)
        for item_id, qty in (inventory or [("fire_gem", 5)])
    ]
    player = PlayerState(
        id=EntityId("hero"),
        name=DisplayString("Hero"),
        background_id=EntityId("bg-1"),
        stats=_STATS,
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        mana_regen=2,
        speed=30,
        luck_current=0,
        luck_capacity=3,
        inventory=inv_entries,
        known_combat_skills=known_skills or [],
        combat_loadout=[EntityId(s) for s in (loadout or [])],
    )
    combat = None
    if in_combat:
        combat = CombatState(
            encounter_id=EntityId("enc-1"),
            phase=CombatPhase.ACTIVE,
            round=1,
            order=[EntityId("hero")],
            current_index=0,
            participants={
                EntityId("hero"): CombatParticipant(
                    hp=_RES,
                    armour=_ZERO,
                    mana=_RES,
                    side=ParticipantSide.PARTY,
                )
            },
        )
    milestones_dict = dict.fromkeys(resolved_milestones or set(), MilestoneState.RESOLVED)
    return RuntimeState(
        campaign_id=EntityId("camp"),
        campaign_version="1.0.0",
        campaign_fingerprint="fp",
        save_id=EntityId("save"),
        revision=0,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(protagonist_id=EntityId("hero")),
        location=LocationState(area_id=EntityId(area_id)),
        plot=PlotState(milestones=milestones_dict),
        known_fact_ids=facts or set(),
        npc_overrides=npc_overrides or {},
        combat=combat,
    )


# ---------------------------------------------------------------------------
# Successful Fusion Tests
# ---------------------------------------------------------------------------


def test_fusion_both_sources_equipped() -> None:
    recipe = _make_recipe(sources=("slash", "fireball"), result="flame_strike")
    skills_map = {
        EntityId("slash"): _make_skill("slash"),
        EntityId("fireball"): _make_skill("fireball"),
        EntityId("flame_strike"): _make_skill("flame_strike"),
    }
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("fireball"), level=5, acquisition_source_id=EntityId("src")
        ),
    ]
    state = _make_state(
        known_skills=known,
        loadout=["slash", "fireball"],
        inventory=[("fire_gem", 3)],
    )

    new_state, result = execute_player_fusion(state, recipe, skills_map)

    # Result checks
    assert result.result_skill_id == EntityId("flame_strike")
    assert result.catalyst_quantity_consumed == 2
    assert result.loadout_before == [EntityId("slash"), EntityId("fireball")]
    assert result.loadout_after == [EntityId("flame_strike")]

    # State checks
    assert len(new_state.player.known_combat_skills) == 1
    assert new_state.player.known_combat_skills[0].skill_id == EntityId("flame_strike")
    assert new_state.player.known_combat_skills[0].level == 1
    assert new_state.player.combat_loadout == [EntityId("flame_strike")]
    assert new_state.player.inventory[0].quantity == 1
    assert len(new_state.player.fusion_history) == 1
    assert new_state.player.fusion_history[0].recipe_id == recipe.id


def test_fusion_one_source_equipped() -> None:
    recipe = _make_recipe(sources=("slash", "fireball"), result="flame_strike")
    skills_map = {
        EntityId("slash"): _make_skill("slash"),
        EntityId("fireball"): _make_skill("fireball"),
        EntityId("flame_strike"): _make_skill("flame_strike"),
        EntityId("guard"): _make_skill("guard"),
    }
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("fireball"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("guard"), level=1, acquisition_source_id=EntityId("src")
        ),
    ]
    state = _make_state(
        known_skills=known,
        loadout=["slash", "guard"],
        inventory=[("fire_gem", 2)],
    )

    new_state, result = execute_player_fusion(state, recipe, skills_map)

    assert result.loadout_after == [EntityId("guard"), EntityId("flame_strike")]
    assert new_state.player.combat_loadout == [EntityId("guard"), EntityId("flame_strike")]
    # Inventory emptied
    assert len(new_state.player.inventory) == 0


def test_fusion_neither_source_equipped() -> None:
    recipe = _make_recipe(sources=("slash", "fireball"), result="flame_strike")
    skills_map = {
        EntityId("slash"): _make_skill("slash"),
        EntityId("fireball"): _make_skill("fireball"),
        EntityId("flame_strike"): _make_skill("flame_strike"),
        EntityId("guard"): _make_skill("guard"),
    }
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("fireball"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("guard"), level=1, acquisition_source_id=EntityId("src")
        ),
    ]
    state = _make_state(
        known_skills=known,
        loadout=["guard"],
        inventory=[("fire_gem", 2)],
    )

    new_state, result = execute_player_fusion(state, recipe, skills_map)

    assert result.loadout_after == [EntityId("guard")]
    assert new_state.player.combat_loadout == [EntityId("guard")]
    known_ids = {k.skill_id for k in new_state.player.known_combat_skills}
    assert EntityId("flame_strike") in known_ids


# ---------------------------------------------------------------------------
# Failure & Prerequisite Rejection Tests
# ---------------------------------------------------------------------------


def test_fusion_fails_during_combat() -> None:
    recipe = _make_recipe()
    skills_map = {EntityId("flame_strike"): _make_skill("flame_strike")}
    state = _make_state(in_combat=True)

    with pytest.raises(ValueError, match="during combat"):
        execute_player_fusion(state, recipe, skills_map)


def test_fusion_fails_when_result_already_known() -> None:
    recipe = _make_recipe(result="flame_strike")
    skills_map = {EntityId("flame_strike"): _make_skill("flame_strike")}
    known = [
        KnownCombatSkill(
            skill_id=EntityId("flame_strike"), level=1, acquisition_source_id=EntityId("src")
        )
    ]
    state = _make_state(known_skills=known)

    with pytest.raises(ValueError, match="already known"):
        execute_player_fusion(state, recipe, skills_map)


def test_fusion_fails_when_result_skill_undefined() -> None:
    recipe = _make_recipe(result="undefined_skill")
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("fireball"), level=5, acquisition_source_id=EntityId("src")
        ),
    ]
    state = _make_state(known_skills=known)

    with pytest.raises(ValueError, match="not defined in campaign"):
        execute_player_fusion(state, recipe, {})


def test_fusion_fails_when_source_skill_not_known() -> None:
    recipe = _make_recipe(sources=("slash", "fireball"), result="flame_strike")
    skills_map = {EntityId("flame_strike"): _make_skill("flame_strike")}
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
    ]
    state = _make_state(known_skills=known)

    with pytest.raises(ValueError, match="does not know source skill"):
        execute_player_fusion(state, recipe, skills_map)


def test_fusion_fails_when_source_skill_not_level_5() -> None:
    recipe = _make_recipe(sources=("slash", "fireball"), result="flame_strike")
    skills_map = {EntityId("flame_strike"): _make_skill("flame_strike")}
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("fireball"), level=4, acquisition_source_id=EntityId("src")
        ),
    ]
    state = _make_state(known_skills=known)

    with pytest.raises(ValueError, match="must be at level 5"):
        execute_player_fusion(state, recipe, skills_map)


def test_fusion_fails_wrong_location_or_specialist() -> None:
    recipe = _make_recipe(
        sources=("slash", "fireball"),
        result="flame_strike",
        location_or_specialist=["arcane_sanctum"],
    )
    skills_map = {EntityId("flame_strike"): _make_skill("flame_strike")}
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("fireball"), level=5, acquisition_source_id=EntityId("src")
        ),
    ]
    state = _make_state(known_skills=known, area_id="village_square")

    with pytest.raises(ValueError, match="not at an authorized fusion location"):
        execute_player_fusion(state, recipe, skills_map)


def test_fusion_succeeds_with_colocated_specialist() -> None:
    recipe = _make_recipe(
        sources=("slash", "fireball"),
        result="flame_strike",
        location_or_specialist=["master_blacksmith"],
    )
    skills_map = {
        EntityId("slash"): _make_skill("slash"),
        EntityId("fireball"): _make_skill("fireball"),
        EntityId("flame_strike"): _make_skill("flame_strike"),
    }
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("fireball"), level=5, acquisition_source_id=EntityId("src")
        ),
    ]
    overrides = {
        EntityId("master_blacksmith"): NpcOverride(location_area_id=EntityId("village_square"))
    }
    state = _make_state(
        known_skills=known,
        area_id="village_square",
        npc_overrides=overrides,
    )

    _new_state, result = execute_player_fusion(state, recipe, skills_map)
    assert result.result_skill_id == EntityId("flame_strike")


def test_fusion_fails_unmet_unlock_condition() -> None:
    recipe = _make_recipe(
        sources=("slash", "fireball"),
        result="flame_strike",
        unlock_conditions=["milestone:dragon_slain"],
    )
    skills_map = {EntityId("flame_strike"): _make_skill("flame_strike")}
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("fireball"), level=5, acquisition_source_id=EntityId("src")
        ),
    ]
    state = _make_state(known_skills=known, resolved_milestones=set())

    with pytest.raises(ValueError, match="unlock condition not met"):
        execute_player_fusion(state, recipe, skills_map)


def test_fusion_fails_insufficient_catalyst() -> None:
    recipe = _make_recipe(
        sources=("slash", "fireball"),
        result="flame_strike",
        catalyst="fire_gem",
        catalyst_qty=5,
    )
    skills_map = {EntityId("flame_strike"): _make_skill("flame_strike")}
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("fireball"), level=5, acquisition_source_id=EntityId("src")
        ),
    ]
    state = _make_state(
        known_skills=known,
        inventory=[("fire_gem", 3)],
    )

    with pytest.raises(ValueError, match="Insufficient catalyst"):
        execute_player_fusion(state, recipe, skills_map)


def test_fusion_input_unchanged_on_failure() -> None:
    recipe = _make_recipe(
        sources=("slash", "fireball"),
        result="flame_strike",
        catalyst="fire_gem",
        catalyst_qty=10,
    )
    skills_map = {EntityId("flame_strike"): _make_skill("flame_strike")}
    known = [
        KnownCombatSkill(
            skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("src")
        ),
        KnownCombatSkill(
            skill_id=EntityId("fireball"), level=5, acquisition_source_id=EntityId("src")
        ),
    ]
    state = _make_state(known_skills=known, inventory=[("fire_gem", 2)])

    with pytest.raises(ValueError, match="Insufficient catalyst"):
        execute_player_fusion(state, recipe, skills_map)

    # Validate state not mutated
    assert len(state.player.known_combat_skills) == 2
    assert state.player.inventory[0].quantity == 2
