"""Generate minimal valid campaign using the actual models."""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from pydantic import __version__

# Add src to path
sys.path.insert(0, str(Path("src").resolve()))

from domain.models.area import AreasFile, AreaDefinition, ResidentNpc, AreaObject, EncounterEntry, AreaSecret, Availability
from domain.models.common import Rational
from domain.models.balance import BalanceFile, DifficultyProfiles, DifficultyProfile, DcBands
from domain.models.campaign_meta import CampaignMeta, Theme, SourceType, DefaultDifficulty, CampaignLength, CampaignStatus
from domain.models.character import CharactersFile, BackgroundDefinition, CompanionDefinition, StatBlock, StatName
from domain.models.enemy import EnemiesFile, EnemyArchetype, LootEntry
from domain.models.item import ItemsFile, ItemDefinition, ItemRarity, ItemType
from domain.models.plot import PlotFile, MilestoneDefinition, OpportunityDefinition
from domain.models.skill import SkillsFile, CombatSkill, CombatSkillLevel, TargetRule, NonCombatSkill, PointBuyDefinition, SkillTree, SkillTreeNode, EffectDefinition, EffectKind
from domain.models.style_bible import StyleBibleFile, StyleBible, SensoryPalette
from domain.models.world import WorldFile, WorldDefinition, FactionDefinition, MajorLocation, PowerSystem


def generate():
    meta = CampaignMeta(
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        title="Minimal",
        theme=Theme.FANTASY,
        campaign_length=CampaignLength.SHORT,
        default_difficulty=DefaultDifficulty.NORMAL,
        source_type=SourceType.CUSTOM,
        source_summary="Summary",
        status=CampaignStatus.DRAFT,
        created_at=datetime.now(timezone.utc),
        art_style_ref="style-1"
    )

    style = StyleBibleFile(
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        style_bible=StyleBible(
            style_id="style-1",
            tone="Tone",
            narrative_voice="Voice",
            sensory_palette=SensoryPalette(
                sounds=["sound"],
                smells=["smell"],
                materials=["mat"],
                lighting=["light"],
                textures=["tex"]
            ),
            banned_phrases=["Phrase"],
            description_requirements="Desc",
            faction_language_notes="Note",
            naming_conventions="Note",
            art_direction="Art",
            examples=["Example"],
            anti_examples=["Example"]
        )
    )

    world = WorldFile(
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        world=WorldDefinition(
            name="World",
            core_conflict="Conflict",
            power_system=PowerSystem(
                rules=["Rule"],
                costs=["Cost"],
                access_restrictions=["Access"],
                side_effects=["Side Effect"]
            ),
            material_conditions=["Condition"],
            values=["Value"],
            factions=[
                FactionDefinition(
                    id="fac-1",
                    name="Fac",
                    goals=["Goal"],
                    resources=["Resource"],
                    hypocrisy="Hypocrisy",
                    language_style="Style",
                    visual_markings="Markings",
                    relationship_edges=[]
                )
            ],
            major_locations=[
                MajorLocation(
                    id="loc-1",
                    name="Loc",
                    summary="Summary"
                )
            ]
        )
    )

    areas = AreasFile(
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        areas=[
            AreaDefinition(
                id="area-1",
                major_location_id="loc-1",
                name="Area",
                description="Area",
                art_prompt="Art",
                danger_level=1,
                residents=[
                    ResidentNpc(
                        id="resident-1",
                        name="Resident",
                        role="Role",
                        availability=Availability.AVAILABLE,
                        location_anchor="Anchor",
                        initial_disposition=0,
                        knowledge_tags=[],
                        personal_goal="Goal",
                        interaction_hooks=[]
                    )
                ],
                objects=[
                    AreaObject(
                        id="object-1",
                        name="Object",
                        description="Object",
                        location_anchor="Anchor",
                        state="State",
                        interactable_tags=[],
                        capability_requirements=[],
                        allowed_effect_ids=[]
                    )
                ],
                encounters=[
                    EncounterEntry(
                        id="encounter-1",
                        enemy_archetype_ids=["enemy-1"],
                        condition="Condition",
                        weight=1,
                        escape_policy_id="milestone-1",
                        consequence_ids=[]
                    )
                ],
                secrets=[
                    AreaSecret(
                        id="secret-1",
                        summary="Secret",
                        lead_fact_ids=[],
                        reveal_conditions=[],
                        core_clue=False
                    )
                ],
                local_faction_ids=["fac-1"],
                connected_area_ids=[]
            )
        ]
    )

    characters = CharactersFile(
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        protagonist_backgrounds=[
            BackgroundDefinition(
                id="bg-1",
                name="Bg",
                description="Bg",
                stat_bonus=StatName.STRENGTH,
                stat_bonus_value=2,
                starting_item_ids=["item-1"],
                starting_skill_ids=["skill-1"],
                starting_fact_ids=["fact-1"]
            )
        ],
        companions=[
            CompanionDefinition(
                id="comp-1",
                name="Comp",
                role="Role",
                combat_role="Combat Role",
                goal="Goal",
                home_area_id="area-1",
                knowledge_tags=["tag1"],
                interaction_hooks=["Hook"],
                relationship_rules=["Rule"],
                availability_rules=["Rule"],
                story_hook_ids=["milestone-1"],
                skill_tree_id="tree-1",
                base_stats=StatBlock(strength=8, dexterity=8, intelligence=8, charisma=8, constitution=8, wisdom=8),
                minimum_usable_actions=1,
                starting_skill_ids=["skill-1"],
                starting_loadout=["skill-1"]
            )
        ],
        major_npcs=[]
    )

    skills = SkillsFile(
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        combat_skills=[
            CombatSkill(
                id="skill-1",
                name="Skill",
                description="Skill",
                acquisition_source_ids=["fac-1"],
                allowed_actor_types=["protagonist", "companion"],
                tags=["tag1"],
                levels=[
                    CombatSkillLevel(
                        level=i,
                        mana_cost=0,
                        target_rule=TargetRule.SINGLE_ENEMY,
                        base_effects=[]
                    ) for i in range(1, 6)
                ]
            )
        ],
        non_combat_skills=[
            NonCombatSkill(
                id="eskill-1",
                name="E",
                description="E",
                stat=StatName.STRENGTH,
                availability_tags=["tag1"],
                capability_tags=["tag2"]
            )
        ],
        point_buy=PointBuyDefinition(cost_map={8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}),
        skill_trees=[
            SkillTree(
                id="tree-1",
                nodes=[SkillTreeNode(id="node-1", skill_id="skill-1", cost=1)],
                edges=[]
            )
        ],
        fusion_recipes=[]
    )

    items = ItemsFile(
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        items=[
            ItemDefinition(
                id="item-1",
                name="Item",
                type=ItemType.CONSUMABLE,
                rarity=ItemRarity.COMMON,
                flavour_text="Flavour",
                mechanics=[
                    EffectDefinition(
                        effect_id="eff-1",
                        kind=EffectKind.DAMAGE,
                        magnitude=1
                    )
                ],
                provenance="Prov",
                requirements=[],
                capability_tags=[],
                max_stack=1
            )
        ]
    )

    enemies = EnemiesFile(
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        enemy_archetypes=[
            EnemyArchetype(
                id="enemy-1",
                name="Enemy",
                description="Enemy",
                faction_id="fac-1",
                art_style_ref="Art",
                power_rating=1,
                base_hp=1,
                base_mana=0,
                base_armour=0,
                speed=1,
                mana_regen=1,
                dexterity=8,
                escape_policy_id="milestone-1",
                combat_skill_ids=["skill-1"],
                behavior_profile="Behavior",
                portrait_prompt="Portrait",
                loot_table=[
                    LootEntry(
                        item_id="item-1",
                        minimum_quantity=1,
                        maximum_quantity=1,
                        weight=1
                    )
                ]
            )
        ]
    )

    plot = PlotFile(
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        clock_definitions=[],
        milestones=[
            MilestoneDefinition(
                id="milestone-1",
                narrative_purpose="Narrative",
                pacing_weight=1,
                canonical_truth="Truth",
                allowed_approach_tags=["tag1"],
                preconditions=[],
                forbidden_changes=[],
                required_outcome_ids=[],
                difficulty_band="easy",
                cycle_allowed=False,
                valid_next_milestone_ids=["milestone-2"]
            ),
            MilestoneDefinition(
                id="milestone-2",
                narrative_purpose="Narrative",
                pacing_weight=1,
                canonical_truth="Truth",
                allowed_approach_tags=["tag1"],
                preconditions=[],
                forbidden_changes=[],
                required_outcome_ids=[],
                difficulty_band="expert",
                cycle_allowed=False,
                valid_next_milestone_ids=[]
            )
        ],
        start_milestone_ids=["milestone-1"],
        ending_milestone_ids=["milestone-2"],
        authored_opportunities=[
            OpportunityDefinition(
                id="opp-1",
                parent_milestone_id="milestone-1",
                title="Opp",
                description="Opp",
                balance_rating=1,
                preconditions=[],
                expiry_conditions=[],
                allowed_outcome_ids=[],
                referenced_entity_ids=[]
            )
        ]
    )

    balance = BalanceFile(
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        difficulty_profiles=DifficultyProfiles(
            story=DifficultyProfile(
                dc_adjustment=-2,
                enemy_hp_ratio=Rational(numerator=7, denominator=10),
                enemy_damage_ratio=Rational(numerator=1, denominator=2),
                enemy_armour_ratio=Rational(numerator=1, denominator=1),
                luck_capacity=3
            ),
            normal=DifficultyProfile(
                dc_adjustment=0,
                enemy_hp_ratio=Rational(numerator=1, denominator=1),
                enemy_damage_ratio=Rational(numerator=1, denominator=1),
                enemy_armour_ratio=Rational(numerator=1, denominator=1),
                luck_capacity=2
            ),
            hard=DifficultyProfile(
                dc_adjustment=2,
                enemy_hp_ratio=Rational(numerator=5, denominator=4),
                enemy_damage_ratio=Rational(numerator=3, denominator=2),
                enemy_armour_ratio=Rational(numerator=1, denominator=1),
                luck_capacity=1
            )
        ),
        level_xp_thresholds={1: 0, 2: 10},
        dc_bands=DcBands(easy=8, standard=12, difficult=15, expert=18, exceptional=22, near_impossible=25),
        modifier_limits={"max_companion_stat_cost": 35},
        effect_limits={},
        enemy_power_formula={"max_loot_weight_ratio": 1.0},
        encounter_targets={},
        fusion_limits={"max_power_budget": 100},
        boss_allowances={}
    )
    
    base_dir = Path("tests/fixtures/campaigns/valid-minimal")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    files = {
        "campaign.json": meta,
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
    
    for filename, model in files.items():
        with open(base_dir / filename, "w", encoding="utf-8") as f:
            f.write(model.model_dump_json(indent=2))

if __name__ == "__main__":
    generate()
