"""Combat skill validation and guaranteed base effect execution."""

from __future__ import annotations

from dataclasses import dataclass

from domain.models.combat_state import CombatState
from domain.models.common import EntityId
from domain.models.skill import CombatSkill, TargetRule
from domain.rules.combat_resources import apply_mana_delta
from engine.combat.commands import resolve_valid_targets
from engine.combat.effects import EffectApplicationResult, apply_effect


@dataclass(frozen=True)
class SkillExecutionResult:
    """Outcome of executing a combat skill command."""

    success: bool
    actor_id: EntityId
    skill_id: EntityId
    mana_spent: int
    effect_results: list[EffectApplicationResult]
    combat_state: CombatState
    logs: list[str]


def execute_skill_command(
    combat: CombatState,
    actor_id: EntityId,
    skill_id: EntityId,
    target_ids: list[EntityId],
    skills_by_id: dict[EntityId, CombatSkill],
    immunities_by_id: dict[EntityId, set[EntityId]] | None = None,
) -> SkillExecutionResult:
    """Validate and execute a skill command, applying guaranteed base effects.

    Atomic: on any validation failure, raises ValueError and performs no mutations.
    """
    # 1. Turn order check
    if not combat.order or combat.order[combat.current_index] != actor_id:
        current_expected = combat.order[combat.current_index] if combat.order else "None"
        raise ValueError(f"Not {actor_id}'s turn. Current active actor is {current_expected}.")

    # 2. Actor existence and living check
    if actor_id not in combat.participants:
        raise ValueError(f"Actor {actor_id} not found in combat participants")

    actor = combat.participants[actor_id]
    if actor.hp.current <= 0:
        raise ValueError(f"Actor {actor_id} is defeated and cannot act")

    # 3. Status prevention (incapacitation check)
    incapacitated_statuses = {EntityId("stun"), EntityId("frozen")}
    for s in actor.statuses:
        if s.status_id in incapacitated_statuses:
            raise ValueError(f"Actor {actor_id} is incapacitated by '{s.status_id}' and cannot act")

    # 4. Loadout & known skill check
    if skill_id not in actor.combat_loadout:
        raise ValueError(f"Skill {skill_id} is not equipped in actor's combat loadout")

    known_entry = next((k for k in actor.known_combat_skills if k.skill_id == skill_id), None)
    if known_entry is None:
        raise ValueError(f"Skill {skill_id} is not known by actor {actor_id}")

    if skill_id not in skills_by_id:
        raise ValueError(f"Skill definition {skill_id} not found in campaign skills")

    skill_def = skills_by_id[skill_id]
    level_idx = known_entry.level - 1
    if level_idx < 0 or level_idx >= len(skill_def.levels):
        raise ValueError(f"Invalid skill level {known_entry.level} for skill {skill_id}")

    skill_level = skill_def.levels[level_idx]

    # 5. Mana check
    if actor.mana.current < skill_level.mana_cost:
        raise ValueError(
            f"Insufficient mana for {skill_id}: requires {skill_level.mana_cost}, "
            f"has {actor.mana.current}"
        )

    # 6. Target validation
    valid_targets = resolve_valid_targets(combat, actor_id, skill_level.target_rule)

    resolved_targets: list[EntityId]
    match skill_level.target_rule:
        case TargetRule.ALL_ALLIES | TargetRule.ALL_ENEMIES:
            resolved_targets = valid_targets
        case TargetRule.SELF | TargetRule.SINGLE_ALLY | TargetRule.SINGLE_ENEMY | TargetRule.ANY:
            if len(target_ids) != 1:
                raise ValueError(
                    f"Target rule {skill_level.target_rule} requires exactly 1 target, "
                    f"got {len(target_ids)}"
                )
            target_id = target_ids[0]
            if target_id not in valid_targets:
                raise ValueError(
                    f"Target {target_id} is invalid for target rule {skill_level.target_rule}"
                )
            resolved_targets = [target_id]

    if not resolved_targets:
        raise ValueError(f"No valid targets found for {skill_id}")

    # 7. Atomic Execution
    new_participants = dict(combat.participants)
    all_effect_results: list[EffectApplicationResult] = []
    logs: list[str] = []

    # Deduct mana
    new_actor_mana, _ = apply_mana_delta(actor.mana, -skill_level.mana_cost)
    new_participants[actor_id] = actor.model_copy(update={"mana": new_actor_mana})
    logs.append(f"{actor_id} used skill '{skill_def.name}' (spent {skill_level.mana_cost} mana).")

    immunity_map = immunities_by_id or {}

    # Apply base effects to each resolved target
    for tid in resolved_targets:
        target_participant = new_participants[tid]
        target_immunities = immunity_map.get(tid, set())

        for effect in skill_level.base_effects:
            updated_target, eff_result = apply_effect(
                effect=effect,
                target_id=tid,
                target=target_participant,
                immunities=target_immunities,
            )
            target_participant = updated_target
            new_participants[tid] = target_participant
            all_effect_results.append(eff_result)
            logs.append(eff_result.log_message)

    updated_combat = combat.model_copy(update={"participants": new_participants})

    return SkillExecutionResult(
        success=True,
        actor_id=actor_id,
        skill_id=skill_id,
        mana_spent=skill_level.mana_cost,
        effect_results=all_effect_results,
        combat_state=updated_combat,
        logs=logs,
    )
