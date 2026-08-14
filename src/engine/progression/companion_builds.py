"""Build and validate companion runtime state from campaign definition."""

from __future__ import annotations

from domain.models.character import CompanionDefinition
from domain.models.common import EntityId
from domain.models.party_state import CompanionRuntimeState, LifeState
from domain.models.runtime_common import KnownCombatSkill, ResourceValue
from domain.models.skill import CombatSkill


def build_companion_runtime(
    definition: CompanionDefinition,
    skills_by_id: dict[EntityId, CombatSkill],
    *,
    hp_current: int | None = None,
    mana_current: int | None = None,
) -> tuple[CompanionRuntimeState | None, list[str]]:
    """Construct a CompanionRuntimeState from a CompanionDefinition.

    Returns (state, []) on success, (None, [errors]) on failure.
    All skills come from the definition — no arbitrary injection.

    Args:
        definition: The authored companion definition.
        skills_by_id: Campaign skill map for validation.
        hp_current: Override current HP (defaults to constitution-derived max).
        mana_current: Override current mana (defaults to intelligence-derived max).
    """
    errors: list[str] = []

    # Validate every starting skill is in the campaign
    for skill_id in definition.starting_skill_ids:
        if skill_id not in skills_by_id:
            errors.append(f"skill {skill_id} not found in campaign")

    # Validate loadout is a subset of starting skills
    known_set = set(definition.starting_skill_ids)
    for skill_id in definition.starting_loadout:
        if skill_id not in known_set:
            errors.append(f"loadout skill {skill_id} is not in starting_skill_ids")

    # Validate minimum_usable_actions: at least that many loadout skills must be usable
    # (loadout >= minimum is guaranteed by authored definition validator, but we re-check)
    if len(definition.starting_loadout) < definition.minimum_usable_actions:
        errors.append(
            f"loadout has {len(definition.starting_loadout)} skills but"
            f" minimum_usable_actions is {definition.minimum_usable_actions}"
        )

    if errors:
        return None, errors

    # Derive HP/mana from stats (simple con/int formula matching engine convention)
    con = definition.base_stats.constitution
    intel = definition.base_stats.intelligence
    hp_max = 8 + con
    mana_max = 4 + intel

    known_skills = [
        KnownCombatSkill(
            skill_id=skill_id,
            level=1,
            acquisition_source_id=definition.id,
        )
        for skill_id in definition.starting_skill_ids
    ]

    state = CompanionRuntimeState(
        id=definition.id,
        hp=ResourceValue(current=hp_current if hp_current is not None else hp_max, maximum=hp_max),
        armour=ResourceValue(current=0, maximum=0),
        mana=ResourceValue(
            current=mana_current if mana_current is not None else mana_max, maximum=mana_max
        ),
        life_state=LifeState.ALIVE,
        is_available=True,
        known_combat_skills=known_skills,
        combat_loadout=list(definition.starting_loadout),
    )

    return state, []
