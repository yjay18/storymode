"""Balance validation for campaign packs."""

from domain.models.diagnostics import Diagnostic
from domain.models.pack import CampaignPack


def _stat_cost(score: int) -> int:
    """Calculate the point-buy cost for a stat score."""
    costs = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    if score < 8:
        return 0
    if score > 15:
        # Extrapolate cost for stats above 15 (though natively capped before background)
        return 9 + (score - 15) * 2
    return costs.get(score, 0)


def validate_balance(pack: CampaignPack) -> list[Diagnostic]:
    """Validate game balance rules."""
    diagnostics: list[Diagnostic] = []

    # 1. Enemy power budget vs loot weight
    max_loot_ratio = pack.balance.enemy_power_formula.get("max_loot_weight_ratio", 1.0)

    for i, enemy in enumerate(pack.enemies.enemy_archetypes):
        total_loot_weight = sum(loot.weight for loot in enemy.loot_table)
        if total_loot_weight > enemy.power_rating * max_loot_ratio:
            diagnostics.append(
                Diagnostic(
                    file="enemies.json",
                    json_pointer=f"/enemy_archetypes/{i}/loot_table",
                    code="overweight_loot",
                    message=(
                        f"Enemy '{enemy.id}' total loot weight "
                        f"({total_loot_weight}) exceeds power rating budget ratio."
                    ),
                    related_ids=[enemy.id],
                )
            )

    # 2. Companion skill limit and stat boundaries
    for i, comp in enumerate(pack.characters.companions):
        # Companion usable actions
        if len(comp.starting_loadout) < comp.minimum_usable_actions:
            diagnostics.append(
                Diagnostic(
                    file="characters.json",
                    json_pointer=f"/companions/{i}/starting_loadout",
                    code="insufficient_companion_actions",
                    message=(
                        f"Companion '{comp.id}' has {len(comp.starting_loadout)} "
                        f"loadout skills, but minimum is {comp.minimum_usable_actions}."
                    ),
                    related_ids=[comp.id],
                )
            )

        # Pydantic already enforces <= 4 loadout skills.
        # Check stat boundaries (27 point buy + max background bonus)
        total_cost = (
            _stat_cost(comp.base_stats.strength)
            + _stat_cost(comp.base_stats.dexterity)
            + _stat_cost(comp.base_stats.intelligence)
            + _stat_cost(comp.base_stats.charisma)
            + _stat_cost(comp.base_stats.constitution)
            + _stat_cost(comp.base_stats.wisdom)
        )

        # 27 points + say up to 2 for background = max cost 35 is safe margin
        max_cost = pack.balance.modifier_limits.get("max_companion_stat_cost", 35)
        if total_cost > max_cost:
            diagnostics.append(
                Diagnostic(
                    file="characters.json",
                    json_pointer=f"/companions/{i}/base_stats",
                    code="overloaded_companion_stats",
                    message=(
                        f"Companion '{comp.id}' stat point-buy cost "
                        f"({total_cost}) exceeds maximum ({max_cost})."
                    ),
                    related_ids=[comp.id],
                )
            )

    # 3. Fusion budget conservation
    max_fusion_budget = pack.balance.fusion_limits.get("max_power_budget", 100)
    for i, recipe in enumerate(pack.skills.fusion_recipes):
        if recipe.power_budget > max_fusion_budget:
            diagnostics.append(
                Diagnostic(
                    file="skills.json",
                    json_pointer=f"/fusion_recipes/{i}/power_budget",
                    code="fusion_over_budget",
                    message=(
                        f"Fusion recipe '{recipe.id}' power budget "
                        f"({recipe.power_budget}) exceeds limit ({max_fusion_budget})."
                    ),
                    related_ids=[recipe.id],
                )
            )
        if recipe.power_budget < 0:
            diagnostics.append(
                Diagnostic(
                    file="skills.json",
                    json_pointer=f"/fusion_recipes/{i}/power_budget",
                    code="negative_power_fusion",
                    message=f"Fusion recipe '{recipe.id}' has negative power budget.",
                    related_ids=[recipe.id],
                )
            )

    return sorted(diagnostics)
