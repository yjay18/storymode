"""Tests for global reference validation."""

# Mocking CampaignPack would be extremely verbose because it has many required fields.
# We will use MagicMock to simulate the pack for specific tests.
from unittest.mock import MagicMock

from engine.validation.references import index_campaign_entities, validate_references


def test_index_build_success() -> None:
    pack = MagicMock()
    pack.style.style_bible.style_id = "style-1"

    fac = MagicMock()
    fac.id = "fac-1"
    pack.world.world.factions = [fac]
    pack.world.world.major_locations = []

    area = MagicMock()
    area.id = "area-1"
    pack.areas.areas = [area]
    pack.areas.resident_npcs = []
    pack.areas.objects = []
    pack.areas.encounters = []
    pack.areas.secrets = []

    pack.characters.protagonist_backgrounds = []
    pack.characters.major_npcs = []
    pack.characters.companions = []

    pack.skills.non_combat_skills = []
    pack.skills.combat_skills = []
    pack.skills.skill_trees = []
    pack.skills.fusion_recipes = []

    pack.enemies.enemy_archetypes = []
    pack.items.items = []
    pack.plot.milestones = []
    pack.plot.authored_opportunities = []
    pack.plot.clock_definitions = []

    index, diagnostics = index_campaign_entities(pack)

    assert len(diagnostics) == 0
    assert "style-1" in index
    assert index["style-1"].entity_type == "style"
    assert "fac-1" in index
    assert index["fac-1"].entity_type == "faction"
    assert "area-1" in index
    assert index["area-1"].entity_type == "area"


def test_index_duplicate_ids() -> None:
    pack = MagicMock()
    pack.style.style_bible.style_id = "dup-1"

    fac = MagicMock()
    fac.id = "dup-1"
    pack.world.world.factions = [fac]
    pack.world.world.major_locations = []

    pack.areas.areas = []
    pack.areas.resident_npcs = []
    pack.areas.objects = []
    pack.areas.encounters = []
    pack.areas.secrets = []
    pack.characters.protagonist_backgrounds = []
    pack.characters.major_npcs = []
    pack.characters.companions = []
    pack.skills.non_combat_skills = []
    pack.skills.combat_skills = []
    pack.skills.skill_trees = []
    pack.skills.fusion_recipes = []
    pack.enemies.enemy_archetypes = []
    pack.items.items = []
    pack.plot.milestones = []
    pack.plot.authored_opportunities = []
    pack.plot.clock_definitions = []

    _index, diagnostics = index_campaign_entities(pack)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "duplicate_id"
    assert diagnostics[0].file == "world.json"
    assert "style" in diagnostics[0].message
    assert "dup-1" in diagnostics[0].related_ids


def test_validate_references_success() -> None:
    pack = MagicMock()
    pack.meta.art_style_ref = "style-1"

    area = MagicMock()
    area.major_location_id = None
    area.connected_area_ids = []
    area.local_faction_ids = ["fac-1"]
    area.residents = []
    area.objects = []
    area.encounters = []
    area.secrets = []
    pack.areas.areas = [area]
    pack.characters.protagonist_backgrounds = []
    pack.characters.major_npcs = []
    pack.characters.companions = []
    pack.skills.skill_trees = []
    pack.skills.fusion_recipes = []
    pack.enemies.enemy_archetypes = []
    pack.plot.start_milestone_ids = []
    pack.plot.ending_milestone_ids = []
    pack.plot.milestones = []
    pack.plot.authored_opportunities = []

    from engine.validation.references import IndexedEntity

    index = {
        "style-1": IndexedEntity("style", "/style_bible/style_id", "style.json"),
        "fac-1": IndexedEntity("faction", "/factions/0/id", "world.json"),
    }

    diagnostics = validate_references(pack, index)
    assert len(diagnostics) == 0


def test_validate_references_unknown_and_type_mismatch() -> None:
    pack = MagicMock()
    pack.meta.art_style_ref = "unknown-style"

    area = MagicMock()
    area.major_location_id = None
    area.connected_area_ids = []
    area.local_faction_ids = ["fac-1"]
    area.residents = []
    area.objects = []
    area.encounters = []
    area.secrets = []
    pack.areas.areas = [area]
    pack.characters.protagonist_backgrounds = []
    pack.characters.major_npcs = []
    pack.characters.companions = []
    pack.skills.skill_trees = []
    pack.skills.fusion_recipes = []
    pack.enemies.enemy_archetypes = []
    pack.plot.start_milestone_ids = []
    pack.plot.ending_milestone_ids = []
    pack.plot.milestones = []
    pack.plot.authored_opportunities = []

    from engine.validation.references import IndexedEntity

    index = {
        # fac-1 exists but is wrong type!
        "fac-1": IndexedEntity("major_location", "/major_locations/0/id", "world.json"),
    }

    diagnostics = validate_references(pack, index)
    assert len(diagnostics) == 2

    assert diagnostics[0].file == "areas.json"
    assert diagnostics[0].code == "type_mismatch"
    assert "major_location" in diagnostics[0].message
    assert "faction" in diagnostics[0].message

    assert diagnostics[1].file == "campaign.json"
    assert diagnostics[1].code == "unknown_reference"
