"""Combat command types and allowed action calculation."""

from __future__ import annotations

import enum

from pydantic import Field

from domain.models.combat_state import CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.skill import CombatSkill, TargetRule


class CombatCommandKind(enum.StrEnum):
    """Types of actions permitted during combat."""

    USE_SKILL = "use_skill"
    DEFEND = "defend"
    FLEE = "flee"
    YIELD = "yield"


class AllowedCombatAction(FrozenModel):
    """An engine-calculated allowed combat action."""

    action_kind: CombatCommandKind
    skill_id: EntityId | None = None
    skill_name: DisplayString | None = None
    mana_cost: int = 0
    target_rule: TargetRule | None = None
    valid_target_ids: list[EntityId] = Field(default_factory=list)
    description: DisplayString | None = None


def resolve_valid_targets(
    combat: CombatState,
    actor_id: EntityId,
    target_rule: TargetRule,
) -> list[EntityId]:
    """Resolve valid living target participant IDs for an actor and target rule."""
    if actor_id not in combat.participants:
        return []

    actor = combat.participants[actor_id]
    actor_side = actor.side

    living_participants = [(pid, p) for pid, p in combat.participants.items() if p.hp.current > 0]

    match target_rule:
        case TargetRule.SELF:
            return [actor_id] if actor.hp.current > 0 else []
        case TargetRule.SINGLE_ALLY:
            return [pid for pid, p in living_participants if p.side == actor_side]
        case TargetRule.SINGLE_ENEMY:
            return [pid for pid, p in living_participants if p.side != actor_side]
        case TargetRule.ALL_ALLIES:
            return [pid for pid, p in living_participants if p.side == actor_side]
        case TargetRule.ALL_ENEMIES:
            return [pid for pid, p in living_participants if p.side != actor_side]
        case TargetRule.ANY:
            return [pid for pid, p in living_participants]


def get_allowed_combat_actions(
    combat: CombatState,
    actor_id: EntityId,
    skills_by_id: dict[EntityId, CombatSkill],
    can_act: bool = True,
) -> list[AllowedCombatAction]:
    """Calculate the authoritative set of available actions for the current actor.

    Returns an empty list if can_act is False or the actor is defeated.
    """
    if not can_act or actor_id not in combat.participants:
        return []

    actor = combat.participants[actor_id]
    if actor.hp.current <= 0:
        return []

    allowed: list[AllowedCombatAction] = []

    # 1. Equipped skills with sufficient mana and valid targets
    known_skill_levels: dict[EntityId, int] = {
        k.skill_id: k.level for k in actor.known_combat_skills
    }

    for skill_id in actor.combat_loadout:
        if skill_id not in skills_by_id or skill_id not in known_skill_levels:
            continue

        skill_def = skills_by_id[skill_id]
        level_idx = known_skill_levels[skill_id] - 1
        if level_idx < 0 or level_idx >= len(skill_def.levels):
            continue

        level_def = skill_def.levels[level_idx]

        # Mana check
        if actor.mana.current < level_def.mana_cost:
            continue

        # Target check
        valid_targets = resolve_valid_targets(combat, actor_id, level_def.target_rule)
        if not valid_targets:
            continue

        allowed.append(
            AllowedCombatAction(
                action_kind=CombatCommandKind.USE_SKILL,
                skill_id=skill_id,
                skill_name=skill_def.name,
                mana_cost=level_def.mana_cost,
                target_rule=level_def.target_rule,
                valid_target_ids=valid_targets,
                description=skill_def.description,
            )
        )

    # 2. Defend is always available for 0 mana
    allowed.append(
        AllowedCombatAction(
            action_kind=CombatCommandKind.DEFEND,
            mana_cost=0,
            description=DisplayString("Take a defensive stance to reduce incoming damage by 25%."),
        )
    )

    # 3. Flee if policy allows and protagonist is acting
    if combat.escape_policy and actor.side == ParticipantSide.PARTY:
        allowed.append(
            AllowedCombatAction(
                action_kind=CombatCommandKind.FLEE,
                mana_cost=0,
                description=DisplayString("Attempt to flee from combat."),
            )
        )

    # 4. Yield if policy allows and protagonist is acting
    if combat.yield_policy and actor.side == ParticipantSide.PARTY:
        allowed.append(
            AllowedCombatAction(
                action_kind=CombatCommandKind.YIELD,
                mana_cost=0,
                description=DisplayString("Yield to the enemy."),
            )
        )

    return allowed
