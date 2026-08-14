"""Progression skill fusion transactions (PROG-03, PROG-04)."""

from __future__ import annotations

from domain.models.character import CompanionDefinition
from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.runtime_common import FusionRecord, InventoryEntry, KnownCombatSkill
from domain.models.runtime_state import RuntimeState
from domain.models.skill import CombatSkill, FusionRecipe


class PlayerFusionResult(FrozenModel):
    """Summary of a completed player skill fusion."""

    recipe_id: EntityId
    source_skill_ids: list[EntityId]
    result_skill_id: EntityId
    catalyst_item_id: EntityId
    catalyst_quantity_consumed: int
    loadout_before: list[EntityId]
    loadout_after: list[EntityId]


def _evaluate_fusion_condition(cond: DisplayString | str, state: RuntimeState) -> bool:
    """Evaluate whether an authored fusion unlock condition is met."""
    text = str(cond).strip()
    if not text:
        return True

    # Milestone checks: "milestone:X" or "milestone:X=resolved"
    if text.startswith("milestone:"):
        parts = text.split(":", 1)[1].strip().split("=", 1)
        m_id = EntityId(parts[0].strip())
        expected_status = parts[1].strip().lower() if len(parts) > 1 else "resolved"
        actual_status = state.plot.milestones.get(m_id)
        if actual_status is not None:
            return actual_status.value == expected_status
        return False

    # Fact checks: "fact:X" or direct entity in known_facts
    if text.startswith("fact:"):
        f_id = EntityId(text.split(":", 1)[1].strip())
        return f_id in state.known_fact_ids
    if EntityId(text) in state.known_fact_ids:
        return True

    # Flag checks: "flag:X" or "flag:X=val"
    if text.startswith("flag:"):
        flag_expr = text.split(":", 1)[1].strip()
        if "=" in flag_expr:
            k, v = flag_expr.split("=", 1)
            flag_val = state.world_flags.get(EntityId(k.strip()))
            return str(flag_val).lower() == v.strip().lower()
        flag_val = state.world_flags.get(EntityId(flag_expr))
        return bool(flag_val)

    if EntityId(text) in state.world_flags:
        return bool(state.world_flags[EntityId(text)])

    # Resolved milestone fallback
    if EntityId(text) in state.plot.milestones:
        from domain.models.plot_state import MilestoneState

        return state.plot.milestones[EntityId(text)] == MilestoneState.RESOLVED

    return False


def _check_location_or_specialist(
    location_or_specialist_ids: list[EntityId],
    state: RuntimeState,
) -> bool:
    """Check if the party is at one of the required locations or specialists."""
    if not location_or_specialist_ids:
        return True

    req_set = set(location_or_specialist_ids)

    # 1. Current area check
    if state.location.area_id in req_set:
        return True

    # 2. Specialist NPC co-located check
    for npc_id, override in state.npc_overrides.items():
        if npc_id in req_set and override.location_area_id == state.location.area_id:
            return True

    return False


def _consume_inventory_items(
    inventory: list[InventoryEntry],
    item_id: EntityId,
    quantity_to_consume: int,
) -> list[InventoryEntry]:
    """Consume a specified quantity of an item from inventory."""
    remaining = quantity_to_consume
    updated_inventory: list[InventoryEntry] = []

    for entry in inventory:
        if entry.item_id == item_id and remaining > 0:
            if entry.quantity <= remaining:
                remaining -= entry.quantity
                # Omit entry since quantity reached 0
            else:
                updated_inventory.append(
                    entry.model_copy(update={"quantity": entry.quantity - remaining})
                )
                remaining = 0
        else:
            updated_inventory.append(entry)

    if remaining > 0:
        raise ValueError(
            f"Insufficient inventory items: need {quantity_to_consume} of {item_id}, missing"
            f" {remaining}"
        )

    return updated_inventory


def execute_player_fusion(
    state: RuntimeState,
    recipe: FusionRecipe,
    skills_by_id: dict[EntityId, CombatSkill],
) -> tuple[RuntimeState, PlayerFusionResult]:
    """Execute an atomic player skill fusion transaction.

    Validates all 7 prerequisites:
    1. No active combat
    2. Result skill not already known
    3. Both source skills known by protagonist
    4. Both source skills at level 5
    5. Location or specialist prerequisite satisfied
    6. All unlock conditions satisfied
    7. Catalyst item and quantity present in inventory

    Consumes source skills and catalyst, updates loadout, grants result skill,
    records fusion history, and returns updated state.
    """
    # 1. Combat check
    if state.combat is not None:
        raise ValueError("Cannot perform skill fusion during combat")

    # 2. Result skill check
    result_id = recipe.result_skill_id
    if any(k.skill_id == result_id for k in state.player.known_combat_skills):
        raise ValueError(f"Result skill {result_id} is already known by protagonist")

    if result_id not in skills_by_id:
        raise ValueError(f"Result skill {result_id} is not defined in campaign skills")

    # 3 & 4. Source skills presence and level 5 check
    sources = recipe.source_skill_ids
    if len(sources) != 2:
        raise ValueError(f"Fusion recipe must have exactly 2 source skills, got {len(sources)}")

    src_map: dict[EntityId, KnownCombatSkill] = {
        k.skill_id: k for k in state.player.known_combat_skills
    }
    for src_id in sources:
        if src_id not in src_map:
            raise ValueError(f"Protagonist does not know source skill {src_id}")
        if src_map[src_id].level != 5:
            raise ValueError(
                f"Source skill {src_id} must be at level 5 "
                f"(currently level {src_map[src_id].level})"
            )

    # 5. Location / Specialist check
    if not _check_location_or_specialist(recipe.location_or_specialist_ids, state):
        raise ValueError(
            f"Protagonist is not at an authorized fusion location or specialist:"
            f" {recipe.location_or_specialist_ids}"
        )

    # 6. Unlock conditions check
    for cond in recipe.unlock_conditions:
        if not _evaluate_fusion_condition(cond, state):
            raise ValueError(f"Fusion unlock condition not met: '{cond}'")

    # 7. Catalyst inventory check
    catalyst_id = recipe.catalyst_item_id
    total_catalyst = sum(
        entry.quantity for entry in state.player.inventory if entry.item_id == catalyst_id
    )
    if total_catalyst < recipe.catalyst_quantity:
        raise ValueError(
            f"Insufficient catalyst {catalyst_id}: requires {recipe.catalyst_quantity},"
            f" has {total_catalyst}"
        )

    # All validations passed -> execute atomic mutation
    # A. Consume catalyst
    new_inventory = _consume_inventory_items(
        state.player.inventory, catalyst_id, recipe.catalyst_quantity
    )

    # B. Remove source skills and grant result skill at level 1
    new_known = [k for k in state.player.known_combat_skills if k.skill_id not in sources]
    new_known.append(
        KnownCombatSkill(
            skill_id=result_id,
            level=1,
            acquisition_source_id=recipe.id,
        )
    )

    # C. Adjust combat loadout
    loadout_before = list(state.player.combat_loadout)
    any_source_equipped = any(src_id in loadout_before for src_id in sources)
    new_loadout = [s for s in loadout_before if s not in sources]
    if any_source_equipped:
        new_loadout.append(result_id)

    # D. Record fusion history
    record = FusionRecord(
        recipe_id=recipe.id,
        source_skill_ids=list(sources),
        result_skill_id=result_id,
    )
    new_history = [*state.player.fusion_history, record]

    new_player = state.player.model_copy(
        update={
            "inventory": new_inventory,
            "known_combat_skills": new_known,
            "combat_loadout": new_loadout,
            "fusion_history": new_history,
        }
    )
    new_state = state.model_copy(update={"player": new_player})

    result = PlayerFusionResult(
        recipe_id=recipe.id,
        source_skill_ids=list(sources),
        result_skill_id=result_id,
        catalyst_item_id=catalyst_id,
        catalyst_quantity_consumed=recipe.catalyst_quantity,
        loadout_before=loadout_before,
        loadout_after=new_loadout,
    )

    return new_state, result


class CompanionFusionResult(FrozenModel):
    """Summary of a completed companion skill fusion."""

    companion_id: EntityId
    recipe_id: EntityId
    source_skill_ids: list[EntityId]
    result_skill_id: EntityId
    backup_skill_id: EntityId | None
    catalyst_item_id: EntityId
    catalyst_quantity_consumed: int
    loadout_before: list[EntityId]
    loadout_after: list[EntityId]


def execute_companion_fusion(
    state: RuntimeState,
    companion_id: EntityId,
    recipe: FusionRecipe,
    companion_definition: CompanionDefinition,
    skills_by_id: dict[EntityId, CombatSkill],
) -> tuple[RuntimeState, CompanionFusionResult]:
    """Execute an atomic companion skill fusion transaction with backup safeguard.

    Validates:
    1. No active combat
    2. Companion exists in state.party.companions and matches definition.id
    3. Result skill and backup skill (if any) defined in campaign skills
    4. Result skill not already known by companion
    5. Both source skills known by companion at level 5
    6. Location or specialist prerequisite satisfied
    7. Unlock conditions satisfied
    8. Catalyst item and quantity present in player inventory
    9. Resulting loadout has at least definition.minimum_usable_actions
    """
    if state.combat is not None:
        raise ValueError("Cannot perform companion skill fusion during combat")

    if companion_id not in state.party.companions:
        raise ValueError(f"Companion {companion_id} is not recruited in party")

    if companion_definition.id != companion_id:
        raise ValueError(
            f"Companion definition mismatch: {companion_definition.id} != {companion_id}"
        )

    comp = state.party.companions[companion_id]

    result_id = recipe.result_skill_id
    if any(k.skill_id == result_id for k in comp.known_combat_skills):
        raise ValueError(f"Result skill {result_id} is already known by companion {companion_id}")

    if result_id not in skills_by_id:
        raise ValueError(f"Result skill {result_id} is not defined in campaign skills")

    backup_id = recipe.companion_backup_skill_id
    if backup_id is not None and backup_id not in skills_by_id:
        raise ValueError(f"Backup skill {backup_id} is not defined in campaign skills")

    sources = recipe.source_skill_ids
    if len(sources) != 2:
        raise ValueError(f"Fusion recipe must have exactly 2 source skills, got {len(sources)}")

    src_map: dict[EntityId, KnownCombatSkill] = {k.skill_id: k for k in comp.known_combat_skills}
    for src_id in sources:
        if src_id not in src_map:
            raise ValueError(f"Companion {companion_id} does not know source skill {src_id}")
        if src_map[src_id].level != 5:
            raise ValueError(
                f"Source skill {src_id} must be at level 5 "
                f"(currently level {src_map[src_id].level})"
            )

    if not _check_location_or_specialist(recipe.location_or_specialist_ids, state):
        raise ValueError(
            f"Party is not at an authorized fusion location or specialist:"
            f" {recipe.location_or_specialist_ids}"
        )

    for cond in recipe.unlock_conditions:
        if not _evaluate_fusion_condition(cond, state):
            raise ValueError(f"Fusion unlock condition not met: '{cond}'")

    catalyst_id = recipe.catalyst_item_id
    total_catalyst = sum(
        entry.quantity for entry in state.player.inventory if entry.item_id == catalyst_id
    )
    if total_catalyst < recipe.catalyst_quantity:
        raise ValueError(
            f"Insufficient catalyst {catalyst_id}: requires {recipe.catalyst_quantity},"
            f" has {total_catalyst}"
        )

    # Validations complete -> execute atomic mutations
    new_inventory = _consume_inventory_items(
        state.player.inventory, catalyst_id, recipe.catalyst_quantity
    )

    new_known = [k for k in comp.known_combat_skills if k.skill_id not in sources]
    new_known.append(
        KnownCombatSkill(
            skill_id=result_id,
            level=1,
            acquisition_source_id=recipe.id,
        )
    )
    if backup_id is not None and not any(k.skill_id == backup_id for k in new_known):
        new_known.append(
            KnownCombatSkill(
                skill_id=backup_id,
                level=1,
                acquisition_source_id=recipe.id,
            )
        )

    loadout_before = list(comp.combat_loadout)
    any_source_equipped = any(src_id in loadout_before for src_id in sources)
    new_loadout = [s for s in loadout_before if s not in sources]
    if any_source_equipped:
        new_loadout.append(result_id)

    if (
        backup_id is not None
        and len(new_loadout) < 4
        and (len(new_loadout) < companion_definition.minimum_usable_actions or any_source_equipped)
        and backup_id not in new_loadout
    ):
        new_loadout.append(backup_id)

    if len(new_loadout) < companion_definition.minimum_usable_actions:
        raise ValueError(
            f"Companion fusion would leave companion with {len(new_loadout)} equipped actions, "
            f"below minimum {companion_definition.minimum_usable_actions}"
        )

    record = FusionRecord(
        recipe_id=recipe.id,
        source_skill_ids=list(sources),
        result_skill_id=result_id,
    )
    new_history = [*comp.fusion_history, record]

    new_comp = comp.model_copy(
        update={
            "known_combat_skills": new_known,
            "combat_loadout": new_loadout,
            "fusion_history": new_history,
        }
    )

    new_party = state.party.model_copy(
        update={"companions": {**state.party.companions, companion_id: new_comp}}
    )
    new_player = state.player.model_copy(update={"inventory": new_inventory})
    new_state = state.model_copy(update={"player": new_player, "party": new_party})

    result = CompanionFusionResult(
        companion_id=companion_id,
        recipe_id=recipe.id,
        source_skill_ids=list(sources),
        result_skill_id=result_id,
        backup_skill_id=backup_id,
        catalyst_item_id=catalyst_id,
        catalyst_quantity_consumed=recipe.catalyst_quantity,
        loadout_before=loadout_before,
        loadout_after=new_loadout,
    )

    return new_state, result
