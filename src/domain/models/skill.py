"""Skill, effect, tree, and fusion campaign models."""

import enum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from domain.models.character import StatName
from domain.models.common import DisplayString, EntityId, FrozenModel, SemanticVersion


class EffectKind(enum.StrEnum):
    """Closed set of allowed combat effects."""

    DAMAGE = "damage"
    HEAL = "heal"
    BUFF = "buff"
    DEBUFF = "debuff"
    STATUS = "status"
    RESOURCE_DRAIN = "resource_drain"
    RESOURCE_RESTORE = "resource_restore"


class TargetRule(enum.StrEnum):
    """Who a skill can target."""

    SELF = "self"
    SINGLE_ALLY = "single_ally"
    SINGLE_ENEMY = "single_enemy"
    ALL_ALLIES = "all_allies"
    ALL_ENEMIES = "all_enemies"
    ANY = "any"


class EffectDefinition(FrozenModel):
    """An atomic combat effect."""

    effect_id: EntityId
    kind: EffectKind
    magnitude: int
    duration: int | None = None
    status_id: EntityId | None = None
    stacking_key: DisplayString | None = None


class EffectDieTable(FrozenModel):
    """Effect bands for a d20 roll."""

    natural_1: list[EffectDefinition]
    low: list[EffectDefinition]
    standard: list[EffectDefinition]
    strong: list[EffectDefinition]
    natural_20: list[EffectDefinition]


class CombatSkillLevel(FrozenModel):
    """One of the 5 levels of a combat skill."""

    level: Annotated[int, Field(ge=1, le=5)]
    mana_cost: Annotated[int, Field(ge=0, le=10)]
    target_rule: TargetRule
    base_effects: list[EffectDefinition]
    effect_die: EffectDieTable | None = None
    prerequisite: DisplayString | None = None


class CombatSkill(FrozenModel):
    """A combat skill definition."""

    id: EntityId
    name: DisplayString
    description: DisplayString
    tags: list[DisplayString]
    acquisition_source_ids: list[EntityId]
    levels: list[CombatSkillLevel]
    allowed_actor_types: list[DisplayString]

    @model_validator(mode="after")
    def check_levels(self) -> "CombatSkill":
        """Skill must have exactly 5 levels in ascending order (1-5)."""
        if len(self.levels) != 5:
            raise ValueError("skill must have exactly 5 levels")
        for i, lvl in enumerate(self.levels, start=1):
            if lvl.level != i:
                raise ValueError(f"skill level {lvl.level} out of order or invalid")
        return self


class NonCombatSkill(FrozenModel):
    """An exploration or social skill."""

    id: EntityId
    name: DisplayString
    description: DisplayString
    stat: StatName
    rank_min: Literal[0] = 0
    rank_max: Literal[5] = 5
    availability_tags: list[DisplayString]
    capability_tags: list[DisplayString]


class SkillTreeNode(FrozenModel):
    """A node in a progression tree."""

    id: EntityId
    skill_id: EntityId
    cost: int


class SkillTreeEdge(FrozenModel):
    """A directed edge between skill nodes."""

    source_node_id: EntityId
    target_node_id: EntityId


class SkillTree(FrozenModel):
    """A progression tree of skills."""

    id: EntityId
    owner_companion_id: EntityId | None = None
    nodes: list[SkillTreeNode]
    edges: list[SkillTreeEdge]

    @model_validator(mode="after")
    def check_graph(self) -> "SkillTree":
        """Edges must be valid and non-self-referencing."""
        node_ids = {n.id for n in self.nodes}
        for edge in self.edges:
            if edge.source_node_id == edge.target_node_id:
                raise ValueError("tree edge cannot self-reference")
            if edge.source_node_id not in node_ids:
                raise ValueError("source node not in tree")
            if edge.target_node_id not in node_ids:
                raise ValueError("target node not in tree")
        return self


class FusionRecipe(FrozenModel):
    """A recipe to combine two level-5 skills."""

    id: EntityId
    source_skill_ids: list[EntityId] = Field(min_length=2, max_length=2)
    result_skill_id: EntityId
    catalyst_item_id: EntityId
    catalyst_quantity: int
    unlock_conditions: list[DisplayString]
    location_or_specialist_ids: list[EntityId]
    companion_backup_skill_id: EntityId | None = None
    power_budget: int

    @model_validator(mode="after")
    def check_recipe(self) -> "FusionRecipe":
        """Sources must be sorted, and result/backup cannot equal a source."""
        if self.source_skill_ids[0] >= self.source_skill_ids[1]:
            raise ValueError("source_skill_ids must be strictly sorted")

        for src in self.source_skill_ids:
            if src == self.result_skill_id:
                raise ValueError("result skill cannot equal a source")
            if src == self.companion_backup_skill_id:
                raise ValueError("backup skill cannot equal a source")

        return self


class PointBuyDefinition(FrozenModel):
    """Rules for initial stat point buy."""

    budget: Literal[27] = 27
    minimum: Literal[8] = 8
    maximum_before_bonus: Literal[15] = 15
    maximum_after_bonus: Literal[17] = 17
    cost_map: dict[int, int]

    @model_validator(mode="after")
    def check_cost_map(self) -> "PointBuyDefinition":
        """Cost map must exactly match the standard rule table."""
        expected = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
        if self.cost_map != expected:
            raise ValueError("cost_map does not match the standard progression rules")
        return self


class SkillsFile(FrozenModel):
    """The root skills file structure."""

    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    point_buy: PointBuyDefinition
    non_combat_skills: list[NonCombatSkill]
    combat_skills: list[CombatSkill]
    skill_trees: list[SkillTree]
    fusion_recipes: list[FusionRecipe]
