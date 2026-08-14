"""Tests for companion fusion safeguard and transactions (PROG-04)."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import CompanionDefinition, StatBlock
from domain.models.common import DisplayString, EntityId
from domain.models.party_state import CompanionRuntimeState, LifeState, PartyState
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
from domain.models.world_state import LocationState
from engine.progression.fusion import execute_companion_fusion

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


def _make_comp_def(
    comp_id: str = "comp-1",
    minimum_usable_actions: int = 1,
    skill_ids: list[str] | None = None,
    loadout: list[str] | None = None,
) -> CompanionDefinition:
    skills = skill_ids or ["slash", "parry"]
    return CompanionDefinition(
        id=EntityId(comp_id),
        name=DisplayString("Ally"),
        role=DisplayString("Warrior"),
        home_area_id=EntityId("forge-area"),
        knowledge_tags=[DisplayString("combat")],
        goal=DisplayString("Fight"),
        interaction_hooks=[DisplayString("Hook")],
        combat_role=DisplayString("melee"),
        base_stats=_STATS,
        skill_tree_id=EntityId("tree-1"),
        starting_skill_ids=[EntityId(s) for s in skills],
        starting_loadout=[EntityId(s) for s in (loadout or skills[:1])],
        relationship_rules=[DisplayString("neutral")],
        story_hook_ids=[EntityId("milestone-1")],
        availability_rules=[DisplayString("available")],
        minimum_usable_actions=minimum_usable_actions,
    )


def _make_recipe(
    recipe_id: str = "rec-comp-fusion-1",
    sources: tuple[str, str] = ("slash", "parry"),
    result: str = "blade_dance",
    backup: str | None = "basic_strike",
    catalyst: str = "iron_core",
    catalyst_qty: int = 2,
    location_or_specialist: list[str] | None = None,
) -> FusionRecipe:
    src_sorted = sorted([EntityId(sources[0]), EntityId(sources[1])])
    return FusionRecipe(
        id=EntityId(recipe_id),
        source_skill_ids=src_sorted,
        result_skill_id=EntityId(result),
        companion_backup_skill_id=EntityId(backup) if backup else None,
        catalyst_item_id=EntityId(catalyst),
        catalyst_quantity=catalyst_qty,
        unlock_conditions=[],
        location_or_specialist_ids=[
            EntityId(s) for s in (location_or_specialist or ["forge-area"])
        ],
        power_budget=20,
    )


def _make_state(
    companion: CompanionRuntimeState,
    inventory: list[tuple[str, int]] | None = None,
    area_id: str = "forge-area",
) -> RuntimeState:
    inv_entries = [
        InventoryEntry(item_id=EntityId(item_id), quantity=qty)
        for item_id, qty in (inventory or [("iron_core", 5)])
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
    )
    return RuntimeState(
        campaign_id=EntityId("camp"),
        campaign_version="1.0.0",
        campaign_fingerprint="fp",
        save_id=EntityId("save"),
        revision=0,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(
            protagonist_id=EntityId("hero"),
            active_companion_ids=[companion.id],
            companions={companion.id: companion},
        ),
        location=LocationState(area_id=EntityId(area_id)),
        plot=PlotState(milestones={EntityId("milestone-1"): MilestoneState.RESOLVED}),
    )


# ---------------------------------------------------------------------------
# Companion Fusion Tests
# ---------------------------------------------------------------------------


def test_companion_fusion_grants_immediate_backup_skill() -> None:
    comp_def = _make_comp_def(comp_id="comp-1", minimum_usable_actions=1)
    recipe = _make_recipe(
        sources=("slash", "parry"),
        result="blade_dance",
        backup="basic_strike",
    )
    skills_map = {
        EntityId("slash"): _make_skill("slash"),
        EntityId("parry"): _make_skill("parry"),
        EntityId("blade_dance"): _make_skill("blade_dance"),
        EntityId("basic_strike"): _make_skill("basic_strike"),
    }
    comp_state = CompanionRuntimeState(
        id=EntityId("comp-1"),
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        life_state=LifeState.ALIVE,
        is_available=True,
        known_combat_skills=[
            KnownCombatSkill(
                skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("tree")
            ),
            KnownCombatSkill(
                skill_id=EntityId("parry"), level=5, acquisition_source_id=EntityId("tree")
            ),
        ],
        combat_loadout=[EntityId("slash"), EntityId("parry")],
    )
    state = _make_state(companion=comp_state, inventory=[("iron_core", 3)])

    new_state, result = execute_companion_fusion(
        state, EntityId("comp-1"), recipe, comp_def, skills_map
    )

    # Result checks
    assert result.result_skill_id == EntityId("blade_dance")
    assert result.backup_skill_id == EntityId("basic_strike")
    assert result.catalyst_quantity_consumed == 2

    # Companion state checks
    updated_comp = new_state.party.companions[EntityId("comp-1")]
    known_skill_ids = {k.skill_id for k in updated_comp.known_combat_skills}
    assert EntityId("blade_dance") in known_skill_ids
    assert EntityId("basic_strike") in known_skill_ids
    assert EntityId("slash") not in known_skill_ids
    assert EntityId("parry") not in known_skill_ids

    # Loadout has blade_dance and backup
    assert EntityId("blade_dance") in updated_comp.combat_loadout
    assert EntityId("basic_strike") in updated_comp.combat_loadout
    assert len(updated_comp.fusion_history) == 1

    # Player inventory consumed
    assert new_state.player.inventory[0].quantity == 1


def test_companion_fusion_minimum_usable_actions_safeguard() -> None:
    """If resulting loadout would fall below minimum_usable_actions, fusion is rejected."""
    # Companion requires 2 usable actions minimum, but fusion leaves only 1 (no backup defined)
    comp_def = _make_comp_def(comp_id="comp-1", minimum_usable_actions=2)
    recipe = _make_recipe(
        sources=("slash", "parry"),
        result="blade_dance",
        backup=None,  # No backup provided
    )
    skills_map = {
        EntityId("slash"): _make_skill("slash"),
        EntityId("parry"): _make_skill("parry"),
        EntityId("blade_dance"): _make_skill("blade_dance"),
    }
    comp_state = CompanionRuntimeState(
        id=EntityId("comp-1"),
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        life_state=LifeState.ALIVE,
        is_available=True,
        known_combat_skills=[
            KnownCombatSkill(
                skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("tree")
            ),
            KnownCombatSkill(
                skill_id=EntityId("parry"), level=5, acquisition_source_id=EntityId("tree")
            ),
        ],
        combat_loadout=[EntityId("slash"), EntityId("parry")],
    )
    state = _make_state(companion=comp_state, inventory=[("iron_core", 5)])

    with pytest.raises(ValueError, match="below minimum 2"):
        execute_companion_fusion(state, EntityId("comp-1"), recipe, comp_def, skills_map)


def test_companion_fusion_rejected_for_unrecruited_companion() -> None:
    comp_def = _make_comp_def(comp_id="ghost-companion")
    recipe = _make_recipe()
    comp_state = CompanionRuntimeState(
        id=EntityId("comp-1"),
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        life_state=LifeState.ALIVE,
        is_available=True,
    )
    state = _make_state(companion=comp_state)

    with pytest.raises(ValueError, match="not recruited"):
        execute_companion_fusion(state, EntityId("ghost-companion"), recipe, comp_def, {})


def test_companion_fusion_rejected_when_definition_mismatch() -> None:
    comp_def = _make_comp_def(comp_id="comp-2")
    recipe = _make_recipe()
    comp_state = CompanionRuntimeState(
        id=EntityId("comp-1"),
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        life_state=LifeState.ALIVE,
        is_available=True,
    )
    state = _make_state(companion=comp_state)

    with pytest.raises(ValueError, match="Companion definition mismatch"):
        execute_companion_fusion(state, EntityId("comp-1"), recipe, comp_def, {})


def test_companion_fusion_rejected_if_source_not_level_5() -> None:
    comp_def = _make_comp_def(comp_id="comp-1")
    recipe = _make_recipe(sources=("slash", "parry"))
    skills_map = {
        EntityId("slash"): _make_skill("slash"),
        EntityId("parry"): _make_skill("parry"),
        EntityId("blade_dance"): _make_skill("blade_dance"),
        EntityId("basic_strike"): _make_skill("basic_strike"),
    }
    comp_state = CompanionRuntimeState(
        id=EntityId("comp-1"),
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        life_state=LifeState.ALIVE,
        is_available=True,
        known_combat_skills=[
            KnownCombatSkill(
                skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("tree")
            ),
            KnownCombatSkill(
                skill_id=EntityId("parry"), level=3, acquisition_source_id=EntityId("tree")
            ),
        ],
        combat_loadout=[EntityId("slash")],
    )
    state = _make_state(companion=comp_state)

    with pytest.raises(ValueError, match="must be at level 5"):
        execute_companion_fusion(state, EntityId("comp-1"), recipe, comp_def, skills_map)


def test_companion_fusion_fails_insufficient_player_catalyst() -> None:
    comp_def = _make_comp_def(comp_id="comp-1")
    recipe = _make_recipe(sources=("slash", "parry"), catalyst="iron_core", catalyst_qty=5)
    skills_map = {
        EntityId("slash"): _make_skill("slash"),
        EntityId("parry"): _make_skill("parry"),
        EntityId("blade_dance"): _make_skill("blade_dance"),
        EntityId("basic_strike"): _make_skill("basic_strike"),
    }
    comp_state = CompanionRuntimeState(
        id=EntityId("comp-1"),
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        life_state=LifeState.ALIVE,
        is_available=True,
        known_combat_skills=[
            KnownCombatSkill(
                skill_id=EntityId("slash"), level=5, acquisition_source_id=EntityId("tree")
            ),
            KnownCombatSkill(
                skill_id=EntityId("parry"), level=5, acquisition_source_id=EntityId("tree")
            ),
        ],
        combat_loadout=[EntityId("slash")],
    )
    state = _make_state(companion=comp_state, inventory=[("iron_core", 2)])

    with pytest.raises(ValueError, match="Insufficient catalyst"):
        execute_companion_fusion(state, EntityId("comp-1"), recipe, comp_def, skills_map)
