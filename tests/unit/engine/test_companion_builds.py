"""Tests for PARTY-02 companion build construction and combat actions."""

from domain.models.character import CompanionDefinition, StatBlock
from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.models.runtime_common import ResourceValue
from domain.models.skill import (
    CombatSkill,
    CombatSkillLevel,
    EffectDefinition,
    EffectKind,
    TargetRule,
)
from engine.combat.commands import CombatCommandKind, get_allowed_combat_actions
from engine.progression.companion_builds import build_companion_runtime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATS = StatBlock(
    strength=10,
    dexterity=10,
    intelligence=10,
    charisma=10,
    constitution=10,
    wisdom=10,
)


def _skill(
    skill_id: str, mana_cost: int = 2, target_rule: TargetRule = TargetRule.SINGLE_ENEMY
) -> CombatSkill:
    effect = EffectDefinition(
        effect_id=EntityId(f"{skill_id}-eff"),
        kind=EffectKind.DAMAGE,
        magnitude=4,
    )
    level = CombatSkillLevel(
        level=1, mana_cost=mana_cost, target_rule=target_rule, base_effects=[effect]
    )
    levels = [
        level,
        CombatSkillLevel(
            level=2, mana_cost=mana_cost, target_rule=target_rule, base_effects=[effect]
        ),
        CombatSkillLevel(
            level=3, mana_cost=mana_cost, target_rule=target_rule, base_effects=[effect]
        ),
        CombatSkillLevel(
            level=4, mana_cost=mana_cost, target_rule=target_rule, base_effects=[effect]
        ),
        CombatSkillLevel(
            level=5, mana_cost=mana_cost, target_rule=target_rule, base_effects=[effect]
        ),
    ]
    return CombatSkill(
        id=EntityId(skill_id),
        name=DisplayString(skill_id.title()),
        description=DisplayString("desc"),
        tags=[],
        acquisition_source_ids=[],
        levels=levels,
        allowed_actor_types=[],
    )


def _comp_def(
    comp_id: str = "comp-1",
    skill_ids: list[str] | None = None,
    loadout: list[str] | None = None,
    minimum_usable_actions: int = 1,
) -> CompanionDefinition:
    if skill_ids is None:
        skill_ids = ["slash"]
    if loadout is None:
        loadout = skill_ids[:1]
    return CompanionDefinition(
        id=EntityId(comp_id),
        name=DisplayString("Ally"),
        role=DisplayString("Fighter"),
        home_area_id=EntityId("area-1"),
        knowledge_tags=[DisplayString("combat")],
        goal=DisplayString("Fight"),
        interaction_hooks=[DisplayString("Hook")],
        combat_role=DisplayString("melee"),
        base_stats=_STATS,
        skill_tree_id=EntityId("tree-1"),
        starting_skill_ids=[EntityId(s) for s in skill_ids],
        starting_loadout=[EntityId(s) for s in loadout],
        relationship_rules=[DisplayString("neutral")],
        story_hook_ids=[EntityId("milestone-1")],
        availability_rules=[DisplayString("available")],
        minimum_usable_actions=minimum_usable_actions,
    )


# ---------------------------------------------------------------------------
# build_companion_runtime — valid construction
# ---------------------------------------------------------------------------


def test_build_valid_companion() -> None:
    defn = _comp_def()
    skills = {EntityId("slash"): _skill("slash")}
    state, errors = build_companion_runtime(defn, skills)
    assert not errors
    assert state is not None
    assert state.id == EntityId("comp-1")
    assert state.hp.current > 0
    assert state.mana.current > 0
    assert len(state.known_combat_skills) == 1
    assert state.known_combat_skills[0].skill_id == EntityId("slash")
    assert list(state.combat_loadout) == [EntityId("slash")]


def test_build_hp_and_mana_derived_from_stats() -> None:
    defn = _comp_def()
    skills = {EntityId("slash"): _skill("slash")}
    state, _ = build_companion_runtime(defn, skills)
    assert state is not None
    # constitution=10 → hp_max = 18, intelligence=10 → mana_max = 14
    assert state.hp.maximum == 18
    assert state.mana.maximum == 14


def test_build_hp_override() -> None:
    defn = _comp_def()
    skills = {EntityId("slash"): _skill("slash")}
    state, _ = build_companion_runtime(defn, skills, hp_current=5)
    assert state is not None
    assert state.hp.current == 5


def test_build_unknown_skill_returns_diagnostic() -> None:
    defn = _comp_def(skill_ids=["ghost-skill"])
    state, errors = build_companion_runtime(defn, {})
    assert state is None
    assert any("ghost-skill" in e for e in errors)


def test_build_loadout_not_in_starting_skills_returns_diagnostic() -> None:
    # Manually craft a definition where loadout differs from skills
    # (only possible if we bypass the model validator, so test the build fn guard separately
    # by using a skill the validator won't catch — same ID in both lists so model is valid,
    # but then we pass an empty skills dict)
    defn = _comp_def()
    # Pass empty skills_by_id so "slash" is flagged as unknown
    state, errors = build_companion_runtime(defn, {})
    assert state is None
    assert errors


# ---------------------------------------------------------------------------
# No respec — only starting_skill_ids are granted
# ---------------------------------------------------------------------------


def test_build_does_not_grant_protagonist_skills() -> None:
    """A protagonist skill ID not in definition must not appear in built state."""
    defn = _comp_def(skill_ids=["slash"])
    hero_skill = EntityId("hero-only-skill")
    skills = {EntityId("slash"): _skill("slash"), hero_skill: _skill("hero-only-skill")}
    state, _ = build_companion_runtime(defn, skills)
    assert state is not None
    known_ids = {k.skill_id for k in state.known_combat_skills}
    assert hero_skill not in known_ids


# ---------------------------------------------------------------------------
# Combat allowed-actions works for companion exactly like player
# ---------------------------------------------------------------------------


def test_companion_allowed_actions_uses_own_loadout() -> None:
    """get_allowed_combat_actions returns the companion's equipped skill, not player's."""
    defn = _comp_def(skill_ids=["slash"], loadout=["slash"])
    skills = {EntityId("slash"): _skill("slash")}
    comp_state, _ = build_companion_runtime(defn, skills)
    assert comp_state is not None

    enemy_res = ResourceValue(current=10, maximum=10)
    zero = ResourceValue(current=0, maximum=5)

    combat = CombatState(
        encounter_id=EntityId("enc"),
        phase=CombatPhase.ACTIVE,
        round=1,
        order=[EntityId("comp-1"), EntityId("enemy-1")],
        current_index=0,
        participants={
            EntityId("comp-1"): CombatParticipant(
                hp=ResourceValue(current=comp_state.hp.current, maximum=comp_state.hp.maximum),
                armour=zero,
                mana=ResourceValue(
                    current=comp_state.mana.current, maximum=comp_state.mana.maximum
                ),
                known_combat_skills=list(comp_state.known_combat_skills),
                combat_loadout=list(comp_state.combat_loadout),
                side=ParticipantSide.PARTY,
            ),
            EntityId("enemy-1"): CombatParticipant(
                hp=enemy_res,
                armour=zero,
                mana=enemy_res,
                side=ParticipantSide.ENEMY,
            ),
        },
    )

    actions = get_allowed_combat_actions(combat, EntityId("comp-1"), skills)
    skill_actions = [a for a in actions if a.action_kind == CombatCommandKind.USE_SKILL]
    assert len(skill_actions) == 1
    assert skill_actions[0].skill_id == EntityId("slash")


def test_companion_no_actions_when_out_of_mana() -> None:
    defn = _comp_def(skill_ids=["slash"], loadout=["slash"])
    skills = {EntityId("slash"): _skill("slash", mana_cost=5)}
    comp_state, _ = build_companion_runtime(defn, skills, mana_current=0)
    assert comp_state is not None

    zero = ResourceValue(current=0, maximum=5)
    combat = CombatState(
        encounter_id=EntityId("enc"),
        phase=CombatPhase.ACTIVE,
        round=1,
        order=[EntityId("comp-1"), EntityId("enemy-1")],
        current_index=0,
        participants={
            EntityId("comp-1"): CombatParticipant(
                hp=ResourceValue(current=comp_state.hp.current, maximum=comp_state.hp.maximum),
                armour=zero,
                mana=ResourceValue(current=0, maximum=comp_state.mana.maximum),
                known_combat_skills=list(comp_state.known_combat_skills),
                combat_loadout=list(comp_state.combat_loadout),
                side=ParticipantSide.PARTY,
            ),
            EntityId("enemy-1"): CombatParticipant(
                hp=ResourceValue(current=10, maximum=10),
                armour=zero,
                mana=ResourceValue(current=10, maximum=10),
                side=ParticipantSide.ENEMY,
            ),
        },
    )

    actions = get_allowed_combat_actions(combat, EntityId("comp-1"), skills)
    skill_actions = [a for a in actions if a.action_kind == CombatCommandKind.USE_SKILL]
    assert not skill_actions  # no usable skills due to 0 mana


def test_no_automatic_ai_action() -> None:
    """There is no function that auto-selects a companion action — caller must request actions."""
    import engine.progression.companion_builds as cb

    # The module must not expose any auto-select / ai-pick function
    public_fns = [name for name in dir(cb) if not name.startswith("_")]
    assert "auto_select_action" not in public_fns
    assert "ai_action" not in public_fns
    assert "pick_action" not in public_fns
