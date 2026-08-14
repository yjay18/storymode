"""Progression skill discovery, upgrades, and loadout management (PROG-02)."""

from __future__ import annotations

from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.runtime_common import KnownCombatSkill
from domain.models.runtime_state import RuntimeState
from domain.models.skill import CombatSkill


class SkillDiscoveryResult(FrozenModel):
    """Summary of a skill discovery grant."""

    entity_id: EntityId
    skill_id: EntityId
    source_id: EntityId
    level: int = 1


class SkillUpgradeResult(FrozenModel):
    """Summary of a skill level upgrade."""

    entity_id: EntityId
    skill_id: EntityId
    previous_level: int
    new_level: int
    tokens_remaining: int


class LoadoutChangeResult(FrozenModel):
    """Summary of a combat loadout change."""

    entity_id: EntityId
    previous_loadout: list[EntityId]
    new_loadout: list[EntityId]


def _evaluate_prerequisite(prereq: DisplayString | str, state: RuntimeState) -> bool:
    """Evaluate whether a skill upgrade prerequisite is met by current state."""
    text = str(prereq).strip()
    if not text:
        return True

    # Level requirement: "min_level:X" or "level:X"
    if text.startswith("min_level:"):
        req_lvl = int(text.split(":", 1)[1].strip())
        return state.player.level >= req_lvl
    if text.startswith("level:"):
        req_lvl = int(text.split(":", 1)[1].strip())
        return state.player.level >= req_lvl

    # Fact requirement: "fact:X" or direct fact id
    if text.startswith("fact:"):
        fact_id = text.split(":", 1)[1].strip()
        return EntityId(fact_id) in state.known_fact_ids
    if EntityId(text) in state.known_fact_ids:
        return True

    # World flag requirement: "flag:X" or "flag:X=val"
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

    return False


def discover_skill(
    state: RuntimeState,
    skill_id: EntityId,
    source_id: EntityId,
    skills_by_id: dict[EntityId, CombatSkill],
    *,
    target_id: EntityId | None = None,
) -> tuple[RuntimeState, SkillDiscoveryResult]:
    """Grant level 1 of an authored skill from a valid acquisition source.

    Raises ValueError if:
    - skill_id not in skills_by_id
    - source_id not in skill's acquisition_source_ids
    - skill is already known by the target entity
    """
    if skill_id not in skills_by_id:
        raise ValueError(f"Skill {skill_id} not found in campaign definitions")

    skill_def = skills_by_id[skill_id]
    if source_id not in skill_def.acquisition_source_ids:
        raise ValueError(
            f"Source {source_id} is not an authorized acquisition source for skill {skill_id}"
        )

    actor_id = target_id or state.player.id

    if actor_id == state.player.id:
        if any(k.skill_id == skill_id for k in state.player.known_combat_skills):
            raise ValueError(f"Skill {skill_id} is already known by protagonist")

        new_known = [
            *state.player.known_combat_skills,
            KnownCombatSkill(skill_id=skill_id, level=1, acquisition_source_id=source_id),
        ]
        new_player = state.player.model_copy(update={"known_combat_skills": new_known})
        new_state = state.model_copy(update={"player": new_player})
    elif actor_id in state.party.companions:
        comp = state.party.companions[actor_id]
        if any(k.skill_id == skill_id for k in comp.known_combat_skills):
            raise ValueError(f"Skill {skill_id} is already known by companion {actor_id}")

        new_known = [
            *comp.known_combat_skills,
            KnownCombatSkill(skill_id=skill_id, level=1, acquisition_source_id=source_id),
        ]
        new_comp = comp.model_copy(update={"known_combat_skills": new_known})
        new_party = state.party.model_copy(
            update={"companions": {**state.party.companions, actor_id: new_comp}}
        )
        new_state = state.model_copy(update={"party": new_party})
    else:
        raise ValueError(f"Target entity {actor_id} not found in player or party")

    result = SkillDiscoveryResult(
        entity_id=actor_id,
        skill_id=skill_id,
        source_id=source_id,
        level=1,
    )
    return new_state, result


def upgrade_skill(
    state: RuntimeState,
    skill_id: EntityId,
    skills_by_id: dict[EntityId, CombatSkill],
    *,
    target_id: EntityId | None = None,
) -> tuple[RuntimeState, SkillUpgradeResult]:
    """Upgrade a known combat skill by 1 level (up to 5) consuming 1 token.

    Raises ValueError if:
    - skill_id is not known by the target
    - skill is already at max level (5)
    - player has insufficient upgrade tokens
    - upgrade prerequisite is not met
    """
    if state.player.upgrade_tokens < 1:
        raise ValueError("Insufficient upgrade tokens to upgrade skill")

    if skill_id not in skills_by_id:
        raise ValueError(f"Skill {skill_id} not found in campaign definitions")

    skill_def = skills_by_id[skill_id]
    actor_id = target_id or state.player.id

    if actor_id == state.player.id:
        known_skill = next(
            (k for k in state.player.known_combat_skills if k.skill_id == skill_id), None
        )
        if known_skill is None:
            raise ValueError(f"Skill {skill_id} is not known by protagonist")

        if known_skill.level >= 5:
            raise ValueError(f"Skill {skill_id} is already at maximum level (5)")

        next_level = known_skill.level + 1
        level_def = skill_def.levels[next_level - 1]
        if level_def.prerequisite and not _evaluate_prerequisite(level_def.prerequisite, state):
            raise ValueError(
                f"Prerequisite '{level_def.prerequisite}' not met for skill"
                f" {skill_id} level {next_level}"
            )

        updated_known = [
            k.model_copy(update={"level": next_level}) if k.skill_id == skill_id else k
            for k in state.player.known_combat_skills
        ]
        new_player = state.player.model_copy(
            update={
                "known_combat_skills": updated_known,
                "upgrade_tokens": state.player.upgrade_tokens - 1,
            }
        )
        new_state = state.model_copy(update={"player": new_player})
        tokens_remaining = new_player.upgrade_tokens
    elif actor_id in state.party.companions:
        comp = state.party.companions[actor_id]
        known_skill = next((k for k in comp.known_combat_skills if k.skill_id == skill_id), None)
        if known_skill is None:
            raise ValueError(f"Skill {skill_id} is not known by companion {actor_id}")

        if known_skill.level >= 5:
            raise ValueError(f"Skill {skill_id} is already at maximum level (5)")

        next_level = known_skill.level + 1
        level_def = skill_def.levels[next_level - 1]
        if level_def.prerequisite and not _evaluate_prerequisite(level_def.prerequisite, state):
            raise ValueError(
                f"Prerequisite '{level_def.prerequisite}' not met for skill"
                f" {skill_id} level {next_level}"
            )

        updated_known = [
            k.model_copy(update={"level": next_level}) if k.skill_id == skill_id else k
            for k in comp.known_combat_skills
        ]
        new_comp = comp.model_copy(update={"known_combat_skills": updated_known})
        new_player = state.player.model_copy(
            update={"upgrade_tokens": state.player.upgrade_tokens - 1}
        )
        new_party = state.party.model_copy(
            update={"companions": {**state.party.companions, actor_id: new_comp}}
        )
        new_state = state.model_copy(update={"player": new_player, "party": new_party})
        tokens_remaining = new_player.upgrade_tokens
    else:
        raise ValueError(f"Target entity {actor_id} not found in player or party")

    result = SkillUpgradeResult(
        entity_id=actor_id,
        skill_id=skill_id,
        previous_level=known_skill.level,
        new_level=next_level,
        tokens_remaining=tokens_remaining,
    )
    return new_state, result


def set_loadout(
    state: RuntimeState,
    loadout: list[EntityId],
    *,
    target_id: EntityId | None = None,
) -> tuple[RuntimeState, LoadoutChangeResult]:
    """Change equipped combat loadout (max 4 unique known skills outside combat).

    Raises ValueError if:
    - combat is active
    - loadout has > 4 skills
    - loadout contains duplicate skill IDs
    - any skill in loadout is not known by the target
    """
    if state.combat is not None:
        raise ValueError("Cannot modify combat loadout during active combat")

    if len(loadout) > 4:
        raise ValueError(f"Loadout cannot exceed 4 skills (got {len(loadout)})")

    if len(loadout) != len(set(loadout)):
        raise ValueError("Loadout cannot contain duplicate skills")

    actor_id = target_id or state.player.id

    if actor_id == state.player.id:
        known_skill_ids = {k.skill_id for k in state.player.known_combat_skills}
        for s in loadout:
            if s not in known_skill_ids:
                raise ValueError(f"Skill {s} is not known by protagonist")

        prev_loadout = list(state.player.combat_loadout)
        new_player = state.player.model_copy(update={"combat_loadout": list(loadout)})
        new_state = state.model_copy(update={"player": new_player})
    elif actor_id in state.party.companions:
        comp = state.party.companions[actor_id]
        known_skill_ids = {k.skill_id for k in comp.known_combat_skills}
        for s in loadout:
            if s not in known_skill_ids:
                raise ValueError(f"Skill {s} is not known by companion {actor_id}")

        prev_loadout = list(comp.combat_loadout)
        new_comp = comp.model_copy(update={"combat_loadout": list(loadout)})
        new_party = state.party.model_copy(
            update={"companions": {**state.party.companions, actor_id: new_comp}}
        )
        new_state = state.model_copy(update={"party": new_party})
    else:
        raise ValueError(f"Target entity {actor_id} not found in player or party")

    result = LoadoutChangeResult(
        entity_id=actor_id,
        previous_loadout=prev_loadout,
        new_loadout=list(loadout),
    )
    return new_state, result


def equip_skill(
    state: RuntimeState,
    skill_id: EntityId,
    *,
    target_id: EntityId | None = None,
) -> tuple[RuntimeState, LoadoutChangeResult]:
    """Add a known skill to loadout (max 4)."""
    actor_id = target_id or state.player.id
    if actor_id == state.player.id:
        current_loadout = list(state.player.combat_loadout)
    elif actor_id in state.party.companions:
        current_loadout = list(state.party.companions[actor_id].combat_loadout)
    else:
        raise ValueError(f"Target entity {actor_id} not found in player or party")

    if skill_id in current_loadout:
        raise ValueError(f"Skill {skill_id} is already equipped")

    if len(current_loadout) >= 4:
        raise ValueError("Cannot equip skill: loadout is already full (4/4)")

    return set_loadout(state, [*current_loadout, skill_id], target_id=actor_id)


def unequip_skill(
    state: RuntimeState,
    skill_id: EntityId,
    *,
    target_id: EntityId | None = None,
) -> tuple[RuntimeState, LoadoutChangeResult]:
    """Remove a skill from loadout."""
    actor_id = target_id or state.player.id
    if actor_id == state.player.id:
        current_loadout = list(state.player.combat_loadout)
    elif actor_id in state.party.companions:
        current_loadout = list(state.party.companions[actor_id].combat_loadout)
    else:
        raise ValueError(f"Target entity {actor_id} not found in player or party")

    if skill_id not in current_loadout:
        raise ValueError(f"Skill {skill_id} is not equipped in loadout")

    new_loadout = [s for s in current_loadout if s != skill_id]
    return set_loadout(state, new_loadout, target_id=actor_id)
