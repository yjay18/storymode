"""Tests for balance validation."""

from unittest.mock import MagicMock

from engine.validation.balance import validate_balance


def test_validate_balance_success() -> None:
    pack = MagicMock()
    pack.balance.enemy_power_formula = {"max_loot_weight_ratio": 1.0}
    pack.balance.modifier_limits = {"max_companion_stat_cost": 35}
    pack.balance.fusion_limits = {"max_power_budget": 100}

    enemy = MagicMock()
    enemy.id = "e1"
    enemy.power_rating = 100
    loot = MagicMock()
    loot.weight = 50
    enemy.loot_table = [loot, loot]  # total 100 <= 100
    pack.enemies.enemy_archetypes = [enemy]

    comp = MagicMock()
    comp.id = "c1"
    comp.minimum_usable_actions = 2
    comp.starting_loadout = ["s1", "s2"]

    comp.base_stats.strength = 10
    comp.base_stats.dexterity = 10
    comp.base_stats.intelligence = 10
    comp.base_stats.charisma = 10
    comp.base_stats.constitution = 10
    comp.base_stats.wisdom = 10
    # Cost = 6 * 2 = 12 <= 35
    pack.characters.companions = [comp]

    recipe = MagicMock()
    recipe.id = "r1"
    recipe.power_budget = 50
    pack.skills.fusion_recipes = [recipe]

    diagnostics = validate_balance(pack)
    assert len(diagnostics) == 0


def test_validate_balance_overweight_loot() -> None:
    pack = MagicMock()
    pack.balance.enemy_power_formula = {"max_loot_weight_ratio": 1.0}
    pack.balance.modifier_limits = {"max_companion_stat_cost": 35}
    pack.balance.fusion_limits = {"max_power_budget": 100}

    enemy = MagicMock()
    enemy.id = "e1"
    enemy.power_rating = 50
    loot = MagicMock()
    loot.weight = 60
    enemy.loot_table = [loot]  # 60 > 50
    pack.enemies.enemy_archetypes = [enemy]

    pack.characters.companions = []
    pack.skills.fusion_recipes = []

    diagnostics = validate_balance(pack)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "overweight_loot"


def test_validate_balance_insufficient_actions() -> None:
    pack = MagicMock()
    pack.balance.enemy_power_formula = {"max_loot_weight_ratio": 1.0}
    pack.balance.modifier_limits = {"max_companion_stat_cost": 35}
    pack.balance.fusion_limits = {"max_power_budget": 100}

    pack.enemies.enemy_archetypes = []

    comp = MagicMock()
    comp.id = "c1"
    comp.minimum_usable_actions = 3
    comp.starting_loadout = ["s1", "s2"]  # 2 < 3

    comp.base_stats.strength = 10
    comp.base_stats.dexterity = 10
    comp.base_stats.intelligence = 10
    comp.base_stats.charisma = 10
    comp.base_stats.constitution = 10
    comp.base_stats.wisdom = 10
    pack.characters.companions = [comp]

    pack.skills.fusion_recipes = []

    diagnostics = validate_balance(pack)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "insufficient_companion_actions"


def test_validate_balance_overloaded_companion_stats() -> None:
    pack = MagicMock()
    pack.balance.enemy_power_formula = {"max_loot_weight_ratio": 1.0}
    pack.balance.modifier_limits = {"max_companion_stat_cost": 35}
    pack.balance.fusion_limits = {"max_power_budget": 100}

    pack.enemies.enemy_archetypes = []

    comp = MagicMock()
    comp.id = "c1"
    comp.minimum_usable_actions = 1
    comp.starting_loadout = ["s1"]

    # Cost = 6 * 9 = 54 > 35
    comp.base_stats.strength = 15
    comp.base_stats.dexterity = 15
    comp.base_stats.intelligence = 15
    comp.base_stats.charisma = 15
    comp.base_stats.constitution = 15
    comp.base_stats.wisdom = 15
    pack.characters.companions = [comp]

    pack.skills.fusion_recipes = []

    diagnostics = validate_balance(pack)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "overloaded_companion_stats"


def test_validate_balance_negative_power_fusion() -> None:
    pack = MagicMock()
    pack.balance.enemy_power_formula = {"max_loot_weight_ratio": 1.0}
    pack.balance.modifier_limits = {"max_companion_stat_cost": 35}
    pack.balance.fusion_limits = {"max_power_budget": 100}

    pack.enemies.enemy_archetypes = []
    pack.characters.companions = []

    recipe = MagicMock()
    recipe.id = "r1"
    recipe.power_budget = -10
    pack.skills.fusion_recipes = [recipe]

    diagnostics = validate_balance(pack)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "negative_power_fusion"


def test_validate_balance_over_budget_fusion() -> None:
    pack = MagicMock()
    pack.balance.enemy_power_formula = {"max_loot_weight_ratio": 1.0}
    pack.balance.modifier_limits = {"max_companion_stat_cost": 35}
    pack.balance.fusion_limits = {"max_power_budget": 100}

    pack.enemies.enemy_archetypes = []
    pack.characters.companions = []

    recipe = MagicMock()
    recipe.id = "r1"
    recipe.power_budget = 110
    pack.skills.fusion_recipes = [recipe]

    diagnostics = validate_balance(pack)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "fusion_over_budget"
