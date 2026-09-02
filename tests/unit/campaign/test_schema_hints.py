"""Schema-derived prompt material: constraint hints, JSON skeletons, and the id index."""

import json

from campaign.builder.models import BuilderBrief, DraftStage, DraftStageState, DraftState
from campaign.generation.stages import (
    artifact_id_index,
    schema_constraint_hints,
    schema_skeleton,
)
from domain.models.common import EntityId
from llm.contracts.campaign_generation import (
    ItemsEnemiesStageResponse,
    MetaStyleStageResponse,
    SkillsStageResponse,
    WorldStageResponse,
)


def test_skeleton_matches_contract_nesting_and_constants() -> None:
    doc = json.loads(schema_skeleton(WorldStageResponse))

    assert doc["stage"] == "rules"
    assert doc["contract_version"] == 1
    assert doc["world"]["schema_version"] == 1
    assert doc["world"]["world"]["factions"][0]["relationship_edges"][0]["stance"] == -100
    assert doc["world"]["world"]["name"] == "<name>"


def test_id_index_lists_defined_ids_and_dangling_references() -> None:
    brief = BuilderBrief(title="T", premise="P")
    stage: DraftStage = "areas"
    draft = DraftState(
        draft_id=EntityId("draft-idx"),
        brief=brief,
        stages={
            stage: DraftStageState(
                stage=stage,
                status="valid",
                artifact_data={
                    "areas": {
                        "campaign_id": "camp-x",
                        "areas": [
                            {
                                "id": "area-dock",
                                "name": "Dock",
                                "major_location_id": "loc-quay",
                                "encounters": [
                                    {"id": "enc-1", "enemy_archetype_ids": ["enemy-rat"]}
                                ],
                            }
                        ],
                    }
                },
            )
        },
    )

    index = artifact_id_index(draft)

    assert "area-dock: areas Dock" in index
    assert "enc-1: encounters" in index
    assert "define these exactly): enemy-rat, loc-quay" in index
    assert "camp-x" not in index


def test_meta_style_hints_state_lengths_enums_and_item_bounds() -> None:
    hints = schema_constraint_hints(MetaStyleStageResponse).splitlines()

    assert "style.style_bible.art_direction: string, 1-120 chars" in hints
    assert "meta.default_difficulty: one of story|normal|hard" in hints
    assert "style.style_bible.examples: list, 1-5 items" in hints
    assert len(hints) == len(set(hints))


def test_hints_follow_refs_lists_and_nested_models() -> None:
    skills_hints = schema_constraint_hints(SkillsStageResponse)
    assert "skills.combat_skills[].levels[].mana_cost: integer 0..10" in skills_hints
    assert len(skills_hints) < 6000

    # Stage 6 was split (PLAY-05): enemies now live in the items_enemies contract.
    items_enemies_hints = schema_constraint_hints(ItemsEnemiesStageResponse)
    assert "enemies.enemy_archetypes[].base_hp: integer 1..10000" in items_enemies_hints
