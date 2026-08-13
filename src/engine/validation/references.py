"""Reference validation for campaign packs."""

from collections.abc import Mapping
from typing import NamedTuple

from domain.models.diagnostics import Diagnostic
from domain.models.pack import CampaignPack


class IndexedEntity(NamedTuple):
    """An indexed entity with its type and source JSON pointer."""

    entity_type: str
    pointer: str
    file: str


def index_campaign_entities(
    pack: CampaignPack,
) -> tuple[dict[str, IndexedEntity], list[Diagnostic]]:
    """Build a global index of all defined EntityIds and return duplicates."""
    index: dict[str, IndexedEntity] = {}
    diagnostics: list[Diagnostic] = []

    def _add(file: str, pointer: str, entity_type: str, entity_id: str | None) -> None:
        if not entity_id:
            return
        if entity_id in index:
            existing = index[entity_id]
            diagnostics.append(
                Diagnostic(
                    file=file,
                    json_pointer=pointer,
                    code="duplicate_id",
                    message=(
                        f"ID '{entity_id}' is already defined as "
                        f"{existing.entity_type} at {existing.pointer}"
                    ),
                    related_ids=[entity_id],
                )
            )
        else:
            index[entity_id] = IndexedEntity(entity_type, pointer, file)

    _add("style.json", "/style_bible/style_id", "style", pack.style.style_bible.style_id)

    for i, fac in enumerate(pack.world.world.factions):
        _add("world.json", f"/factions/{i}/id", "faction", fac.id)

    for i, loc in enumerate(pack.world.world.major_locations):
        _add("world.json", f"/major_locations/{i}/id", "major_location", loc.id)

    for i, area in enumerate(pack.areas.areas):
        _add("areas.json", f"/areas/{i}/id", "area", area.id)

        for j, npc in enumerate(area.residents):
            _add("areas.json", f"/areas/{i}/residents/{j}/id", "resident_npc", npc.id)

        for j, obj in enumerate(area.objects):
            _add("areas.json", f"/areas/{i}/objects/{j}/id", "area_object", obj.id)

        for j, enc in enumerate(area.encounters):
            _add("areas.json", f"/areas/{i}/encounters/{j}/id", "encounter", enc.id)

        for j, sec in enumerate(area.secrets):
            _add("areas.json", f"/areas/{i}/secrets/{j}/id", "area_secret", sec.id)

    for i, bg in enumerate(pack.characters.protagonist_backgrounds):
        _add("characters.json", f"/backgrounds/{i}/id", "background", bg.id)

    for i, mjr_npc in enumerate(pack.characters.major_npcs):
        _add("characters.json", f"/major_npcs/{i}/id", "major_npc", mjr_npc.id)

    for i, comp in enumerate(pack.characters.companions):
        _add("characters.json", f"/companions/{i}/id", "companion", comp.id)

    for i, nc_skill in enumerate(pack.skills.non_combat_skills):
        _add("skills.json", f"/non_combat_skills/{i}/id", "non_combat_skill", nc_skill.id)

    for i, c_skill in enumerate(pack.skills.combat_skills):
        _add("skills.json", f"/combat_skills/{i}/id", "combat_skill", c_skill.id)
        for j, lvl in enumerate(c_skill.levels):
            for k, eff in enumerate(lvl.base_effects):
                _add(
                    "skills.json",
                    f"/combat_skills/{i}/levels/{j}/base_effects/{k}/effect_id",
                    "effect",
                    eff.effect_id,
                )

    for i, tree in enumerate(pack.skills.skill_trees):
        _add("skills.json", f"/skill_trees/{i}/id", "skill_tree", tree.id)

    for i, rec in enumerate(pack.skills.fusion_recipes):
        _add("skills.json", f"/fusion_recipes/{i}/id", "fusion_recipe", rec.id)

    for i, arch in enumerate(pack.enemies.enemy_archetypes):
        _add("enemies.json", f"/enemy_archetypes/{i}/id", "enemy_archetype", arch.id)

    for i, item in enumerate(pack.items.items):
        _add("items.json", f"/items/{i}/id", "item", item.id)

    for i, mile in enumerate(pack.plot.milestones):
        _add("plot.json", f"/milestones/{i}/id", "milestone", mile.id)

    for i, opp in enumerate(pack.plot.authored_opportunities):
        _add("plot.json", f"/authored_opportunities/{i}/id", "opportunity", opp.id)

    for i, clock in enumerate(pack.plot.clock_definitions):
        _add("plot.json", f"/clock_definitions/{i}/id", "clock", clock.id)

    return index, sorted(diagnostics)


def validate_references(pack: CampaignPack, index: Mapping[str, IndexedEntity]) -> list[Diagnostic]:
    """Validate all references in the campaign pack against the global index."""
    diagnostics: list[Diagnostic] = []

    def _check(
        file: str,
        pointer: str,
        ref_id: str | None,
        expected_types: tuple[str, ...] | str | None,
    ) -> None:
        if not ref_id:
            return
        if ref_id not in index:
            diagnostics.append(
                Diagnostic(
                    file=file,
                    json_pointer=pointer,
                    code="unknown_reference",
                    message=f"Reference to unknown ID '{ref_id}'",
                    related_ids=[ref_id],
                )
            )
            return

        target = index[ref_id]
        if expected_types:
            if isinstance(expected_types, str):
                expected_types = (expected_types,)
            if target.entity_type not in expected_types:
                exp = expected_types[0] if len(expected_types) == 1 else " or ".join(expected_types)
                diagnostics.append(
                    Diagnostic(
                        file=file,
                        json_pointer=pointer,
                        code="type_mismatch",
                        message=f"Reference '{ref_id}' is a {target.entity_type}, expected {exp}",
                        related_ids=[ref_id],
                    )
                )

    def _check_list(
        file: str,
        pointer: str,
        ref_ids: list[str] | None,
        expected_types: tuple[str, ...] | str | None,
    ) -> None:
        if not ref_ids:
            return
        for i, ref_id in enumerate(ref_ids):
            _check(file, f"{pointer}/{i}", ref_id, expected_types)

    # Meta
    _check("campaign.json", "/art_style_ref", pack.meta.art_style_ref, "style")

    # Areas
    for i, area in enumerate(pack.areas.areas):
        prefix = f"/areas/{i}"
        _check(
            "areas.json",
            f"{prefix}/major_location_id",
            area.major_location_id,
            "major_location",
        )
        _check_list(
            "areas.json",
            f"{prefix}/connected_area_ids",
            area.connected_area_ids,
            "area",
        )
        _check_list("areas.json", f"{prefix}/local_faction_ids", area.local_faction_ids, "faction")

        for j, npc in enumerate(area.residents):
            prefix_res = f"/areas/{i}/residents/{j}"
            _check("areas.json", f"{prefix_res}/faction_id", npc.faction_id, "faction")
            # Residents don't have home_area_id in areas.json, they belong to the area naturally

        for j, obj in enumerate(area.objects):
            _check_list(
                "areas.json",
                f"/areas/{i}/objects/{j}/allowed_effect_ids",
                obj.allowed_effect_ids,
                "effect",
            )

    # Characters
    for i, bg in enumerate(pack.characters.protagonist_backgrounds):
        prefix = f"/backgrounds/{i}"
        _check_list(
            "characters.json",
            f"{prefix}/starting_skill_ids",
            bg.starting_skill_ids,
            ("combat_skill", "non_combat_skill"),
        )
        _check_list("characters.json", f"{prefix}/starting_item_ids", bg.starting_item_ids, "item")

    for i, mjr_npc in enumerate(pack.characters.major_npcs):
        prefix = f"/major_npcs/{i}"
        _check("characters.json", f"{prefix}/faction_id", mjr_npc.faction_id, "faction")
        _check("characters.json", f"{prefix}/home_area_id", mjr_npc.home_area_id, "area")

    for i, comp in enumerate(pack.characters.companions):
        prefix = f"/companions/{i}"
        _check("characters.json", f"{prefix}/faction_id", comp.faction_id, "faction")
        _check("characters.json", f"{prefix}/home_area_id", comp.home_area_id, "area")
        _check("characters.json", f"{prefix}/skill_tree_id", comp.skill_tree_id, "skill_tree")
        _check_list(
            "characters.json",
            f"{prefix}/starting_skill_ids",
            comp.starting_skill_ids,
            ("combat_skill", "non_combat_skill"),
        )
        _check_list(
            "characters.json",
            f"{prefix}/starting_loadout",
            comp.starting_loadout,
            "combat_skill",
        )
        _check_list(
            "characters.json",
            f"{prefix}/story_hook_ids",
            comp.story_hook_ids,
            ("opportunity", "milestone"),
        )

    # Skills
    for i, c_skill in enumerate(pack.skills.combat_skills):
        _check_list(
            "skills.json",
            f"/combat_skills/{i}/acquisition_source_ids",
            c_skill.acquisition_source_ids,
            None,
        )

    for i, tree in enumerate(pack.skills.skill_trees):
        _check(
            "skills.json",
            f"/skill_trees/{i}/owner_companion_id",
            tree.owner_companion_id,
            "companion",
        )

    for i, rec in enumerate(pack.skills.fusion_recipes):
        prefix = f"/fusion_recipes/{i}"
        _check_list(
            "skills.json", f"{prefix}/source_skill_ids", rec.source_skill_ids, "combat_skill"
        )
        _check("skills.json", f"{prefix}/result_skill_id", rec.result_skill_id, "combat_skill")
        _check("skills.json", f"{prefix}/catalyst_item_id", rec.catalyst_item_id, "item")
        _check(
            "skills.json",
            f"{prefix}/companion_backup_skill_id",
            rec.companion_backup_skill_id,
            "combat_skill",
        )
        _check_list(
            "skills.json",
            f"{prefix}/location_or_specialist_ids",
            rec.location_or_specialist_ids,
            ("area", "major_location", "major_npc", "resident_npc"),
        )

    # Enemies
    for i, arch in enumerate(pack.enemies.enemy_archetypes):
        prefix = f"/enemy_archetypes/{i}"
        _check("enemies.json", f"{prefix}/faction_id", arch.faction_id, "faction")
        _check_list(
            "enemies.json", f"{prefix}/combat_skill_ids", arch.combat_skill_ids, "combat_skill"
        )
        for j, loot in enumerate(arch.loot_table):
            _check("enemies.json", f"{prefix}/loot_table/{j}/item_id", loot.item_id, "item")

    # Plot
    _check_list("plot.json", "/start_milestone_ids", pack.plot.start_milestone_ids, "milestone")
    _check_list("plot.json", "/ending_milestone_ids", pack.plot.ending_milestone_ids, "milestone")

    for i, mile in enumerate(pack.plot.milestones):
        _check_list(
            "plot.json",
            f"/milestones/{i}/valid_next_milestone_ids",
            mile.valid_next_milestone_ids,
            "milestone",
        )

    for i, opp in enumerate(pack.plot.authored_opportunities):
        prefix = f"/authored_opportunities/{i}"
        _check("plot.json", f"{prefix}/parent_milestone_id", opp.parent_milestone_id, "milestone")
        _check_list("plot.json", f"{prefix}/referenced_entity_ids", opp.referenced_entity_ids, None)

    return sorted(diagnostics)
