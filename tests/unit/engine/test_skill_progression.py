"""Tests for skill discovery, upgrades, and loadouts (PROG-02)."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.models.party_state import CompanionRuntimeState, LifeState, PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import KnownCombatSkill, ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.skill import (
    CombatSkill,
    CombatSkillLevel,
    EffectDefinition,
    EffectKind,
    TargetRule,
)
from domain.models.world_state import LocationState
from engine.progression.skills import (
    discover_skill,
    equip_skill,
    set_loadout,
    unequip_skill,
    upgrade_skill,
)

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


def _make_skill(
    skill_id: str,
    source_ids: list[str] | None = None,
    prerequisites: list[str | None] | None = None,
) -> CombatSkill:
    sources = [EntityId(s) for s in (source_ids or ["source-1"])]
    prereqs = prerequisites or [None, None, None, None, None]
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
            prerequisite=DisplayString(prereqs[i - 1]) if prereqs[i - 1] else None,
        )
        for i in range(1, 6)
    ]
    return CombatSkill(
        id=EntityId(skill_id),
        name=DisplayString(skill_id.title()),
        description=DisplayString("A test skill"),
        tags=[],
        acquisition_source_ids=sources,
        levels=levels,
        allowed_actor_types=[],
    )


def _make_state(
    known_skills: list[KnownCombatSkill] | None = None,
    loadout: list[str] | None = None,
    tokens: int = 0,
    level: int = 1,
    in_combat: bool = False,
    companion: CompanionRuntimeState | None = None,
    facts: set[EntityId] | None = None,
    flags: dict[EntityId, bool | int | str] | None = None,
) -> RuntimeState:
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
        level=level,
        upgrade_tokens=tokens,
        known_combat_skills=known_skills or [],
        combat_loadout=[EntityId(s) for s in (loadout or [])],
    )
    companions = {companion.id: companion} if companion else {}
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
            active_companion_ids=[companion.id] if companion else [],
            companions=companions,
        ),
        location=LocationState(area_id=EntityId("area-1")),
        plot=PlotState(),
        known_fact_ids=facts or set(),
        world_flags=flags or {},
        combat=combat,
    )


# ---------------------------------------------------------------------------
# Skill Discovery Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source_type",
    ["mentor-1", "faction-iron", "boss-reward-dragon", "manual-scroll", "quest-shrine"],
)
def test_discover_skill_authorized_sources(source_type: str) -> None:
    skill = _make_skill("fireball", source_ids=[source_type])
    skills_map = {skill.id: skill}
    state = _make_state()

    new_state, result = discover_skill(state, skill.id, EntityId(source_type), skills_map)

    assert result.skill_id == skill.id
    assert result.source_id == EntityId(source_type)
    assert result.level == 1
    assert len(new_state.player.known_combat_skills) == 1
    assert new_state.player.known_combat_skills[0].skill_id == skill.id
    assert new_state.player.known_combat_skills[0].level == 1


def test_discover_skill_unauthorized_source_raises() -> None:
    skill = _make_skill("fireball", source_ids=["mentor-1"])
    skills_map = {skill.id: skill}
    state = _make_state()

    with pytest.raises(ValueError, match="not an authorized acquisition source"):
        discover_skill(state, skill.id, EntityId("wrong-source"), skills_map)


def test_discover_skill_unknown_definition_raises() -> None:
    state = _make_state()
    with pytest.raises(ValueError, match="not found in campaign"):
        discover_skill(state, EntityId("unknown"), EntityId("source-1"), {})


def test_discover_skill_duplicate_grant_raises() -> None:
    skill = _make_skill("fireball", source_ids=["mentor-1"])
    skills_map = {skill.id: skill}
    known = [
        KnownCombatSkill(skill_id=skill.id, level=1, acquisition_source_id=EntityId("mentor-1"))
    ]
    state = _make_state(known_skills=known)

    with pytest.raises(ValueError, match="already known"):
        discover_skill(state, skill.id, EntityId("mentor-1"), skills_map)


def test_discover_skill_for_companion() -> None:
    comp = CompanionRuntimeState(
        id=EntityId("comp-1"),
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        life_state=LifeState.ALIVE,
        is_available=True,
    )
    skill = _make_skill("heal", source_ids=["shrine-1"])
    skills_map = {skill.id: skill}
    state = _make_state(companion=comp)

    new_state, result = discover_skill(
        state, skill.id, EntityId("shrine-1"), skills_map, target_id=comp.id
    )

    assert result.entity_id == comp.id
    assert len(new_state.party.companions[comp.id].known_combat_skills) == 1


# ---------------------------------------------------------------------------
# Skill Upgrade Tests
# ---------------------------------------------------------------------------


def test_upgrade_skill_success() -> None:
    skill = _make_skill("slash")
    skills_map = {skill.id: skill}
    known = [
        KnownCombatSkill(skill_id=skill.id, level=1, acquisition_source_id=EntityId("source-1"))
    ]
    state = _make_state(known_skills=known, tokens=2)

    new_state, result = upgrade_skill(state, skill.id, skills_map)

    assert result.previous_level == 1
    assert result.new_level == 2
    assert result.tokens_remaining == 1
    assert new_state.player.upgrade_tokens == 1
    assert new_state.player.known_combat_skills[0].level == 2


def test_upgrade_skill_insufficient_tokens_raises() -> None:
    skill = _make_skill("slash")
    skills_map = {skill.id: skill}
    known = [
        KnownCombatSkill(skill_id=skill.id, level=1, acquisition_source_id=EntityId("source-1"))
    ]
    state = _make_state(known_skills=known, tokens=0)

    with pytest.raises(ValueError, match="Insufficient upgrade tokens"):
        upgrade_skill(state, skill.id, skills_map)


def test_upgrade_skill_max_level_cap_raises() -> None:
    skill = _make_skill("slash")
    skills_map = {skill.id: skill}
    known = [
        KnownCombatSkill(skill_id=skill.id, level=5, acquisition_source_id=EntityId("source-1"))
    ]
    state = _make_state(known_skills=known, tokens=3)

    with pytest.raises(ValueError, match="maximum level"):
        upgrade_skill(state, skill.id, skills_map)


def test_upgrade_skill_unknown_by_player_raises() -> None:
    skill = _make_skill("slash")
    skills_map = {skill.id: skill}
    state = _make_state(tokens=1)

    with pytest.raises(ValueError, match="not known"):
        upgrade_skill(state, skill.id, skills_map)


def test_upgrade_skill_with_level_prerequisite() -> None:
    # Level 2 requires min_level:3
    skill = _make_skill("meteor", prerequisites=[None, "min_level:3", None, None, None])
    skills_map = {skill.id: skill}
    known = [
        KnownCombatSkill(skill_id=skill.id, level=1, acquisition_source_id=EntityId("source-1"))
    ]

    # Player level 2 -> fails
    state_lvl2 = _make_state(known_skills=known, tokens=1, level=2)
    with pytest.raises(ValueError, match="Prerequisite"):
        upgrade_skill(state_lvl2, skill.id, skills_map)

    # Player level 3 -> succeeds
    state_lvl3 = _make_state(known_skills=known, tokens=1, level=3)
    _new_state, result = upgrade_skill(state_lvl3, skill.id, skills_map)
    assert result.new_level == 2


def test_upgrade_skill_with_fact_prerequisite() -> None:
    skill = _make_skill("divine_strike", prerequisites=[None, "fact:holy_tome", None, None, None])
    skills_map = {skill.id: skill}
    known = [
        KnownCombatSkill(skill_id=skill.id, level=1, acquisition_source_id=EntityId("source-1"))
    ]

    # Without fact -> raises
    state_no_fact = _make_state(known_skills=known, tokens=1)
    with pytest.raises(ValueError, match="Prerequisite"):
        upgrade_skill(state_no_fact, skill.id, skills_map)

    # With fact -> succeeds
    state_with_fact = _make_state(known_skills=known, tokens=1, facts={EntityId("holy_tome")})
    _new_state, result = upgrade_skill(state_with_fact, skill.id, skills_map)
    assert result.new_level == 2


# ---------------------------------------------------------------------------
# Loadout Tests
# ---------------------------------------------------------------------------


def test_set_loadout_success() -> None:
    known = [
        KnownCombatSkill(
            skill_id=EntityId(f"skill-{i}"),
            level=1,
            acquisition_source_id=EntityId("src"),
        )
        for i in range(1, 5)
    ]
    state = _make_state(known_skills=known)

    new_state, result = set_loadout(
        state, [EntityId("skill-1"), EntityId("skill-2"), EntityId("skill-3")]
    )
    assert result.new_loadout == [
        EntityId("skill-1"),
        EntityId("skill-2"),
        EntityId("skill-3"),
    ]
    assert new_state.player.combat_loadout == [
        EntityId("skill-1"),
        EntityId("skill-2"),
        EntityId("skill-3"),
    ]


def test_set_loadout_exceeding_four_slots_raises() -> None:
    known = [
        KnownCombatSkill(
            skill_id=EntityId(f"skill-{i}"),
            level=1,
            acquisition_source_id=EntityId("src"),
        )
        for i in range(1, 6)
    ]
    state = _make_state(known_skills=known)

    with pytest.raises(ValueError, match="cannot exceed 4"):
        set_loadout(state, [EntityId(f"skill-{i}") for i in range(1, 6)])


def test_set_loadout_duplicate_skills_raises() -> None:
    known = [
        KnownCombatSkill(
            skill_id=EntityId("skill-1"),
            level=1,
            acquisition_source_id=EntityId("src"),
        )
    ]
    state = _make_state(known_skills=known)

    with pytest.raises(ValueError, match="duplicate"):
        set_loadout(state, [EntityId("skill-1"), EntityId("skill-1")])


def test_set_loadout_unknown_skill_raises() -> None:
    state = _make_state()
    with pytest.raises(ValueError, match="not known"):
        set_loadout(state, [EntityId("ghost-skill")])


def test_set_loadout_during_combat_raises() -> None:
    known = [
        KnownCombatSkill(
            skill_id=EntityId("skill-1"),
            level=1,
            acquisition_source_id=EntityId("src"),
        )
    ]
    state = _make_state(known_skills=known, in_combat=True)

    with pytest.raises(ValueError, match="during active combat"):
        set_loadout(state, [EntityId("skill-1")])


def test_equip_and_unequip_skill() -> None:
    known = [
        KnownCombatSkill(
            skill_id=EntityId(f"skill-{i}"),
            level=1,
            acquisition_source_id=EntityId("src"),
        )
        for i in range(1, 5)
    ]
    state = _make_state(known_skills=known, loadout=["skill-1", "skill-2"])

    # Equip skill-3
    s1, res1 = equip_skill(state, EntityId("skill-3"))
    assert res1.new_loadout == [
        EntityId("skill-1"),
        EntityId("skill-2"),
        EntityId("skill-3"),
    ]
    assert s1.player.combat_loadout == [
        EntityId("skill-1"),
        EntityId("skill-2"),
        EntityId("skill-3"),
    ]

    # Equip already equipped raises
    with pytest.raises(ValueError, match="already equipped"):
        equip_skill(s1, EntityId("skill-3"))

    # Unequip skill-2
    s2, res2 = unequip_skill(s1, EntityId("skill-2"))
    assert res2.new_loadout == [EntityId("skill-1"), EntityId("skill-3")]
    assert s2.player.combat_loadout == [EntityId("skill-1"), EntityId("skill-3")]

    # Unequip not equipped raises
    with pytest.raises(ValueError, match="not equipped"):
        unequip_skill(s2, EntityId("skill-2"))
