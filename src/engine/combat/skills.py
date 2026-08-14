"""Combat skill validation, guaranteed base effects, and optional effect die execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.audit import RollRecord
from domain.models.combat_state import CombatState
from domain.models.common import DisplayString, EntityId
from domain.models.skill import CombatSkill, EffectDefinition, TargetRule
from domain.rules.combat_resources import apply_mana_delta
from engine.combat.commands import resolve_valid_targets
from engine.combat.effects import EffectApplicationResult, apply_effect
from engine.dice.effects import CombatEffectBand, calculate_combat_band
from engine.dice.service import DiceService


@dataclass(frozen=True)
class SkillExecutionResult:
    """Outcome of executing a combat skill command."""

    success: bool
    actor_id: EntityId
    skill_id: EntityId
    mana_spent: int
    base_effect_results: list[EffectApplicationResult]
    bonus_effect_results: list[EffectApplicationResult] = field(default_factory=list)
    effect_die_roll: int | None = None
    effect_die_band: CombatEffectBand | None = None
    roll_records: list[RollRecord] = field(default_factory=list)
    combat_state: CombatState = field(default_factory=lambda: None)  # type: ignore[assignment]
    logs: list[str] = field(default_factory=list)

    @property
    def effect_results(self) -> list[EffectApplicationResult]:
        """All applied effects (base + bonus)."""
        return self.base_effect_results + self.bonus_effect_results


def execute_skill_command(
    combat: CombatState,
    actor_id: EntityId,
    skill_id: EntityId,
    target_ids: list[EntityId],
    skills_by_id: dict[EntityId, CombatSkill],
    immunities_by_id: dict[EntityId, set[EntityId]] | None = None,
    dice_service: DiceService | None = None,
    transaction_id: EntityId | None = None,
    revision: int = 1,
    command_id: EntityId | None = None,
) -> SkillExecutionResult:
    """Validate and execute a skill command.

    Applies guaranteed base effects and an optional effect die.
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
    base_effect_results: list[EffectApplicationResult] = []
    bonus_effect_results: list[EffectApplicationResult] = []
    roll_records: list[RollRecord] = []
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
            base_effect_results.append(eff_result)
            logs.append(f"[Base] {eff_result.log_message}")

    # 8. Optional Effect Die
    effect_roll: int | None = None
    effect_band: CombatEffectBand | None = None

    living_targets = [tid for tid in resolved_targets if new_participants[tid].hp.current > 0]

    if skill_level.effect_die is not None and dice_service is not None and living_targets:
        tx_id = transaction_id or EntityId("tx_combat_effect")
        cmd_id = command_id or EntityId("cmd_skill_use")
        reason = DisplayString(f"Effect die roll for {skill_def.name}")

        effect_roll, roll_rec = dice_service.roll_combat_effect(
            transaction_id=tx_id,
            revision=revision,
            command_id=cmd_id,
            reason=reason,
        )
        effect_band = calculate_combat_band(effect_roll)
        logs.append(f"Rolled effect die: {effect_roll} ({effect_band.value}).")

        bonus_effects: list[EffectDefinition] = []
        match effect_band:
            case CombatEffectBand.NATURAL_1:
                bonus_effects = skill_level.effect_die.natural_1
            case CombatEffectBand.LOW:
                bonus_effects = skill_level.effect_die.low
            case CombatEffectBand.STANDARD:
                bonus_effects = skill_level.effect_die.standard
            case CombatEffectBand.STRONG:
                bonus_effects = skill_level.effect_die.strong
            case CombatEffectBand.NATURAL_20:
                bonus_effects = skill_level.effect_die.natural_20

        confirmed_effect_ids: list[EntityId] = []

        for tid in living_targets:
            if new_participants[tid].hp.current <= 0:
                continue

            target_participant = new_participants[tid]
            target_immunities = immunity_map.get(tid, set())

            for b_eff in bonus_effects:
                updated_target, b_res = apply_effect(
                    effect=b_eff,
                    target_id=tid,
                    target=target_participant,
                    immunities=target_immunities,
                )
                target_participant = updated_target
                new_participants[tid] = target_participant
                bonus_effect_results.append(b_res)
                if b_res.applied:
                    confirmed_effect_ids.append(b_eff.effect_id)
                logs.append(f"[Bonus] {b_res.log_message}")

        updated_rec = roll_rec.model_copy(update={"confirmed_effect_ids": confirmed_effect_ids})
        roll_records.append(updated_rec)

    updated_combat = combat.model_copy(update={"participants": new_participants})

    return SkillExecutionResult(
        success=True,
        actor_id=actor_id,
        skill_id=skill_id,
        mana_spent=skill_level.mana_cost,
        base_effect_results=base_effect_results,
        bonus_effect_results=bonus_effect_results,
        effect_die_roll=effect_roll,
        effect_die_band=effect_band,
        roll_records=roll_records,
        combat_state=updated_combat,
        logs=logs,
    )
