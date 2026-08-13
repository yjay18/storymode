"""Generate a minimal valid campaign pack."""
import json
from pathlib import Path


def main() -> None:
    base_dir = Path("tests/fixtures/campaigns/valid-minimal")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. campaign.json
    campaign = {
        "schema_version": 1,
        "campaign_id": "minimal-campaign",
        "campaign_version": "1.0.0",
        "title": "Minimal",
        "author": "Test",
        "description": "Minimal valid campaign"
    }
    
    # 2. style.json
    style = {
        "schema_version": 1,
        "campaign_id": "minimal-campaign",
        "campaign_version": "1.0.0",
        "style_bible": {
            "tone_and_themes": ["theme1"],
            "forbidden_tropes": [],
            "prose_style": "Simple",
            "dialogue_conventions": "Direct",
            "narrator_perspective": "first_person_limited",
            "environmental_descriptions": "Brief"
        }
    }
    
    # 3. world.json
    world = {
        "schema_version": 1,
        "campaign_id": "minimal-campaign",
        "campaign_version": "1.0.0",
        "world": {
            "name": "World",
            "core_conflict": "Conflict",
            "power_system": "Magic",
            "material_conditions": "Good",
            "values": "Values",
            "factions": [
                {
                    "id": "fac-1",
                    "name": "Fac",
                    "goals": "Goals",
                    "resources": "Res",
                    "hypocrisy": "Hypocrisy",
                    "language_style": "Style",
                    "visual_markings": "Markings",
                    "relationship_edges": []
                }
            ],
            "major_locations": [
                {
                    "id": "loc-1",
                    "name": "Loc",
                    "description": "Loc",
                    "discovery_milestone_id": "milestone-1"
                }
            ]
        }
    }
    
    # 4. areas.json
    areas = {
        "schema_version": 1,
        "campaign_id": "minimal-campaign",
        "campaign_version": "1.0.0",
        "areas": [
            {
                "id": "area-1",
                "major_location_id": "loc-1",
                "name": "Area",
                "description": "Area",
                "environment_tags": ["tag1"],
                "local_faction_ids": ["fac-1"],
                "connected_area_ids": []
            }
        ]
    }
    
    # 5. characters.json
    characters = {
        "schema_version": 1,
        "campaign_id": "minimal-campaign",
        "campaign_version": "1.0.0",
        "protagonist_setup": {
            "backgrounds": [
                {
                    "id": "bg-1",
                    "name": "Bg",
                    "description": "Bg",
                    "stat_bonus_target": "strength",
                    "stat_bonus_value": 2,
                    "starting_item_ids": ["item-1"],
                    "starting_skill_ids": ["skill-1"]
                }
            ],
            "starting_milestone_ids": ["milestone-1"]
        },
        "companions": [
            {
                "id": "comp-1",
                "name": "Comp",
                "description": "Comp",
                "acquisition_milestone_id": "milestone-1",
                "base_stats": {
                    "strength": 8,
                    "dexterity": 8,
                    "intelligence": 8,
                    "charisma": 8,
                    "constitution": 8,
                    "wisdom": 8
                },
                "minimum_usable_actions": 1,
                "starting_loadout": ["skill-1"],
                "innate_tags": ["tag1"],
                "personality_traits": ["trait1"],
                "dialogue_style": "Style",
                "loyalty_drivers": ["Loyalty"],
                "portrait_prompt": "Portrait"
            }
        ]
    }
    
    # 6. skills.json
    skills = {
        "schema_version": 1,
        "campaign_id": "minimal-campaign",
        "campaign_version": "1.0.0",
        "combat_skills": [
            {
                "id": "skill-1",
                "name": "Skill",
                "description": "Skill",
                "acquisition_source_ids": ["fac-1"],
                "allowed_actor_types": ["protagonist", "companion"],
                "levels": [
                    {
                        "mana_cost": 0,
                        "target_rule": "single_enemy",
                        "base_effects": [],
                        "tags": ["tag1"],
                        "upgrade_prerequisites": []
                    },
                    {
                        "mana_cost": 0,
                        "target_rule": "single_enemy",
                        "base_effects": [],
                        "tags": ["tag1"],
                        "upgrade_prerequisites": []
                    },
                    {
                        "mana_cost": 0,
                        "target_rule": "single_enemy",
                        "base_effects": [],
                        "tags": ["tag1"],
                        "upgrade_prerequisites": []
                    },
                    {
                        "mana_cost": 0,
                        "target_rule": "single_enemy",
                        "base_effects": [],
                        "tags": ["tag1"],
                        "upgrade_prerequisites": []
                    },
                    {
                        "mana_cost": 0,
                        "target_rule": "single_enemy",
                        "base_effects": [],
                        "tags": ["tag1"],
                        "upgrade_prerequisites": []
                    }
                ]
            }
        ],
        "non_combat_skills": [
            {
                "id": "eskill-1",
                "name": "E",
                "description": "E",
                "associated_stat": "strength",
                "tags": ["tag1"],
                "discovery_tags": [],
                "capability_tags": []
            }
        ],
        "point_buy": {
            "initial_points": 27
        },
        "skill_trees": [
            {
                "id": "tree-1",
                "nodes": [
                    {"id": "node-1", "skill_id": "skill-1", "cost": 1}
                ],
                "edges": []
            }
        ],
        "fusion_recipes": []
    }
    
    # 7. items.json
    items = {
        "schema_version": 1,
        "campaign_id": "minimal-campaign",
        "campaign_version": "1.0.0",
        "items": [
            {
                "id": "item-1",
                "name": "Item",
                "type": "consumable",
                "rarity": "common",
                "flavour_text": "Flavour",
                "mechanics": "Mech",
                "provenance": "Prov",
                "requirements": [],
                "capability_tags": [],
                "max_stack": 1
            }
        ]
    }
    
    # 8. enemies.json
    enemies = {
        "schema_version": 1,
        "campaign_id": "minimal-campaign",
        "campaign_version": "1.0.0",
        "enemy_archetypes": [
            {
                "id": "enemy-1",
                "name": "Enemy",
                "description": "Enemy",
                "faction_id": "fac-1",
                "portrait_prompt": "Portrait",
                "power_rating": 1,
                "base_hp": 1,
                "base_armour": 0,
                "base_damage": 1,
                "speed": 1,
                "mana_regen": 1,
                "dexterity": 8,
                "escape_policy_id": "milestone-1",
                "combat_skill_ids": ["skill-1"],
                "loot_table": [
                    {
                        "item_id": "item-1", 
                        "minimum_quantity": 1,
                        "maximum_quantity": 1, 
                        "weight": 1
                    }
                ]
            }
        ]
    }
    
    # 9. plot.json
    plot = {
        "schema_version": 1,
        "campaign_id": "minimal-campaign",
        "campaign_version": "1.0.0",
        "clock_definitions": [],
        "milestones": [
            {
                "id": "milestone-1",
                "name": "M1",
                "narrative_purpose": "Narrative",
                "pacing_weight": 1,
                "canonical_truth": "Truth",
                "allowed_approach_tags": ["tag1"],
                "preconditions": [],
                "forbidden_changes": [],
                "required_outcome_ids": [],
                "cycle_allowed": False,
                "valid_next_milestone_ids": ["milestone-2"]
            },
            {
                "id": "milestone-2",
                "name": "M2",
                "narrative_purpose": "Narrative",
                "pacing_weight": 1,
                "canonical_truth": "Truth",
                "allowed_approach_tags": ["tag1"],
                "preconditions": [],
                "forbidden_changes": [],
                "required_outcome_ids": [],
                "cycle_allowed": False,
                "valid_next_milestone_ids": []
            }
        ],
        "start_milestone_ids": ["milestone-1"],
        "ending_milestone_ids": ["milestone-2"],
        "authored_opportunities": [
            {
                "id": "opp-1",
                "parent_milestone_id": "milestone-1",
                "title": "Opp",
                "description": "Opp",
                "balance_rating": 1,
                "preconditions": [],
                "expiry_conditions": [],
                "allowed_outcome_ids": [],
                "referenced_entity_ids": []
            }
        ]
    }
    
    # 10. balance.json
    balance = {
        "schema_version": 1,
        "campaign_id": "minimal-campaign",
        "campaign_version": "1.0.0",
        "difficulty_profiles": {
            "story": {
                "dc_adjustment": -2,
                "enemy_hp_ratio": "7/10",
                "enemy_damage_ratio": "1/2",
                "enemy_armour_ratio": "1/1",
                "luck_capacity": 3
            },
            "normal": {
                "dc_adjustment": 0,
                "enemy_hp_ratio": "1/1",
                "enemy_damage_ratio": "1/1",
                "enemy_armour_ratio": "1/1",
                "luck_capacity": 2
            },
            "hard": {
                "dc_adjustment": 2,
                "enemy_hp_ratio": "5/4",
                "enemy_damage_ratio": "3/2",
                "enemy_armour_ratio": "1/1",
                "luck_capacity": 1
            }
        },
        "level_xp_thresholds": {
            "1": 0,
            "2": 10
        },
        "dc_bands": {
            "easy": 8,
            "standard": 12,
            "difficult": 15,
            "expert": 18,
            "exceptional": 22,
            "near_impossible": 25
        },
        "modifier_limits": {
            "max_companion_stat_cost": 35
        },
        "effect_limits": {},
        "enemy_power_formula": {
            "max_loot_weight_ratio": 1.0
        },
        "encounter_targets": {},
        "fusion_limits": {
            "max_power_budget": 100
        },
        "boss_allowances": {}
    }
    
    files = {
        "campaign.json": campaign,
        "style.json": style,
        "world.json": world,
        "areas.json": areas,
        "characters.json": characters,
        "skills.json": skills,
        "items.json": items,
        "enemies.json": enemies,
        "plot.json": plot,
        "balance.json": balance
    }
    
    for filename, data in files.items():
        with open(base_dir / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

if __name__ == "__main__":
    main()
