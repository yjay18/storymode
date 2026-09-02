"""Versioned prompt templates for campaign generation stages (BUILD-05).

Guarantees:
- Strict JSON output contracts per generation stage.
- Quoted data delimiters for untrusted brief/source inputs.
- Cultural profiles and bottom-up worldbuilding instructions injected into stage context.
- Dedicated repair prompt renderer with diagnostics.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from campaign.builder.models import BuilderBrief, DraftStage
from campaign.importers.compactor import WorldCodex
from llm.prompts.renderer import render_template

META_STYLE_PROMPT_VERSION = "campaign-meta_style/1.0.0"
WORLD_PROMPT_VERSION = "campaign-world/1.0.0"
AREAS_PROMPT_VERSION = "campaign-areas/1.0.0"
PLOT_PROMPT_VERSION = "campaign-plot/1.0.0"
CHARACTERS_PROMPT_VERSION = "campaign-characters/1.0.0"
SKILLS_PROMPT_VERSION = "campaign-skills/1.0.0"
ITEMS_ENEMIES_PROMPT_VERSION = "campaign-items_enemies/1.0.0"
BALANCE_PROMPT_VERSION = "campaign-balance/1.0.0"
STAGE_REPAIR_PROMPT_VERSION = "campaign-repair/1.0.0"


def _extract_codex_context(brief: BuilderBrief, codex: WorldCodex | None) -> dict[str, str]:
    """Helper to extract formatted cultural lore and world context."""
    cultural_context = ""
    if codex and codex.cultural_profiles:
        p = codex.cultural_profiles[0]
        cultural_context = (
            f"Region: {p.region_name}\n"
            f"Taboos & Oaths: {', '.join(p.taboos_and_oaths)}\n"
            f"Superstitions: {', '.join(p.superstitions_and_omens)}\n"
            f"Scarcity/Economy: {', '.join(p.scarcity_and_economy)}\n"
            f"Attire/Status: {', '.join(p.attire_and_status)}\n"
            f"Magic Rules: {', '.join(p.magic_and_supernatural_rules)}\n"
            f"Dialects: {', '.join(p.dialects_and_idioms)}"
        )
    elif brief.protected_facts:
        cultural_context = "\n".join(brief.protected_facts)

    return {
        "title": brief.title,
        "premise": brief.premise,
        "genre": brief.genre,
        "theme": brief.theme,
        "tone": brief.tone,
        "cultural_context": cultural_context,
    }


def render_meta_style_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-1",
) -> str:
    """Render Stage 1 prompt: Campaign metadata and Style Bible."""
    ctx = _extract_codex_context(brief, codex)
    template = (
        "You are the Storymode Campaign Meta & Style Designer.\n"
        "Generate the Stage 1 response (Campaign metadata & Style Bible) matching this contract:\n"
        "{\n"
        '  "contract_version": 1,\n'
        f'  "prompt_version": "{META_STYLE_PROMPT_VERSION}",\n'
        f'  "request_id": "{request_id}",\n'
        '  "stage": "meta_style",\n'
        '  "meta": {\n'
        '    "schema_version": 1,\n'
        '    "campaign_id": "<id>",\n'
        '    "campaign_version": "1.0.0",\n'
        '    "title": "<title>",\n'
        '    "theme": "<fantasy|sci_fi|apocalyptic|custom>",\n'
        '    "source_type": "<prompt|novel|plain_text|comic_transcript|custom>",\n'
        '    "source_summary": "<summary>",\n'
        '    "default_difficulty": "<story|normal|hard>",\n'
        '    "campaign_length": "<short|medium|long|custom>",\n'
        '    "art_style_ref": "<style_id>",\n'
        '    "created_at": "2026-08-17T00:00:00Z",\n'
        '    "status": "draft"\n'
        "  },\n"
        '  "style": {\n'
        '    "schema_version": 1,\n'
        '    "campaign_id": "<campaign_id>",\n'
        '    "campaign_version": "1.0.0",\n'
        '    "style_bible": {\n'
        '      "style_id": "<style_id>",\n'
        '      "tone": "<tone>",\n'
        '      "narrative_voice": "Third-person limited",\n'
        '      "sensory_palette": {\n'
        '        "sounds": ["..."], "smells": ["..."], "materials": ["..."],\n'
        '        "lighting": ["..."], "textures": ["..."]\n'
        "      },\n"
        '      "faction_language_notes": "<dialect notes>",\n'
        '      "naming_conventions": "<naming rules>",\n'
        '      "banned_phrases": ["suddenly", "a sense of dread"],\n'
        '      "description_requirements": "Sensory-first, grounded texture",\n'
        '      "examples": ["..."],\n'
        '      "anti_examples": ["..."],\n'
        '      "art_direction": "<art preferences>"\n'
        "    }\n"
        "  }\n"
        "}\n\n"
        "Rules:\n"
        "- Ground sensory palette in local materials and authentic atmosphere.\n"
        "- Status must be 'draft' with no content_fingerprint.\n\n"
        "Context Brief:\n"
        "<<<DATA\n"
        "{brief_json}\n"
        ">>>\n"
    )
    return render_template(template, {"brief_json": json.dumps(ctx, indent=2)})


def _render_stage_prompt(
    role: str,
    stage_label: str,
    version: str,
    request_id: str,
    rules: Sequence[str],
    brief: BuilderBrief,
    codex: WorldCodex | None,
) -> str:
    """Shared body for stages 2-6.

    The JSON shape, the hard field limits, and the index of IDs defined by earlier stages
    are appended by the stage runner straight from the Pydantic contracts, so this text
    never restates the schema by hand (the hand-written copies drifted from the models).
    """
    ctx = _extract_codex_context(brief, codex)
    rule_lines = "".join(f"- {r}\n" for r in rules)
    template = (
        f"You are the Storymode {role}.\n"
        f"Generate the {stage_label} response as one JSON object. Its exact shape, the hard "
        "field limits, and the IDs already defined by earlier stages follow the brief. Every "
        "ID you reference must appear in that index or be defined in this response. IDs are "
        "lowercase kebab-case, 3-64 chars, starting with a letter.\n"
        f'Set "prompt_version" to "{version}" and "request_id" to "{request_id}". '
        "Use the campaign_id and campaign_version from the meta stage.\n\n"
        f"Rules:\n{rule_lines}\n"
        "Context Brief:\n"
        "<<<DATA\n"
        "{brief_json}\n"
        ">>>\n"
    )
    return render_template(template, {"brief_json": json.dumps(ctx, indent=2)})


def render_world_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-world",
) -> str:
    """Render Stage 2 prompt: world, power system, factions, and major locations."""
    return _render_stage_prompt(
        "World & Rules Architect",
        "Stage 2 (world)",
        WORLD_PROMPT_VERSION,
        request_id,
        [
            "Define 2-4 factions with concrete goals, resources, and a real hypocrisy.",
            "relationship_edges reference other faction ids from this response; no self edges.",
            "Define 3-5 major_locations; later stages attach areas to these ids.",
            "Ground the power system in local materials and costs from the brief.",
        ],
        brief,
        codex,
    )


def render_areas_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-areas",
) -> str:
    """Render Stage 3 prompt: explorable areas with residents, objects, encounters, secrets."""
    return _render_stage_prompt(
        "Area Designer",
        "Stage 3 (areas)",
        AREAS_PROMPT_VERSION,
        request_id,
        [
            "Define 3-6 areas; the first is the safe starting area with no encounters.",
            "major_location_id and local_faction_ids must be ids from the world stage.",
            "connected_area_ids must be symmetric and every area must be reachable.",
            "Each area has 1-3 residents, 1-3 objects, 0-2 encounters, and 1-2 secrets.",
            "Encounters may reference enemy ids of the form enemy-<name>; the skills stage "
            "must define every one of them. escape_policy_id may be escape-default.",
            "At least one secret in the campaign is a core clue with a lead_fact_id that is "
            "an object or resident id.",
        ],
        brief,
        codex,
    )


def render_plot_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-plot",
) -> str:
    """Render Stage 4 prompt: milestones, authored opportunities, and clocks."""
    return _render_stage_prompt(
        "Plot Architect",
        "Stage 4 (plot)",
        PLOT_PROMPT_VERSION,
        request_id,
        [
            "Define 3-6 milestones forming a graph from start_milestone_ids to "
            "ending_milestone_ids; every milestone must reach an ending.",
            "valid_next_milestone_ids, start and ending ids reference milestones in this "
            "response; cycle_allowed is false unless a cycle is intended.",
            "difficulty_band is one of easy, standard, difficult, expert, exceptional.",
            "Each opportunity has a parent_milestone_id from this response and "
            "referenced_entity_ids from the earlier stages' index.",
            "Define 0-2 clocks with maximum between 3 and 12.",
        ],
        brief,
        codex,
    )


def render_characters_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-chars",
) -> str:
    """Render Stage 5 prompt: protagonist backgrounds, major NPCs, and companions."""
    return _render_stage_prompt(
        "Character Designer",
        "Stage 5 (characters)",
        CHARACTERS_PROMPT_VERSION,
        request_id,
        [
            "Define 2-3 protagonist_backgrounds with stat_bonus_value 1 or 2.",
            "starting_skill_ids use skill-<name> ids and starting_item_ids use item-<name> "
            "ids; the skills stage must define every one of them.",
            "starting_fact_ids are secret, object, or resident ids from the areas stage.",
            "home_area_id is an area id; faction_id is a faction id or null.",
            "Define 1-2 companions. base_stats are 8-15 each with total point-buy cost at "
            "most 35 (8=0,9=1,10=2,11=3,12=4,13=5,14=7,15=9).",
            "starting_loadout is a subset of starting_skill_ids with at most 4 entries and "
            "at least minimum_usable_actions entries; skill_tree_id is tree-<name>.",
            "story_hook_ids are milestone or opportunity ids from the plot stage.",
        ],
        brief,
        codex,
    )


def render_skills_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-skills",
) -> str:
    """Render Stage 6 prompt: combat and non-combat skills and skill trees only."""
    return _render_stage_prompt(
        "Mechanics Designer",
        "Stage 6 (skills and skill trees)",
        SKILLS_PROMPT_VERSION,
        request_id,
        [
            "Define every skill- and tree- id that earlier stages reference (see the index) "
            "plus 4-6 combat skills and 3-5 non-combat skills in total.",
            "Each combat skill has exactly five levels numbered 1 to 5 with mana_cost 0-10; "
            "base_effects use kinds damage, heal, buff, debuff, resource_drain, or "
            "resource_restore with integer magnitude; status_id stays null.",
            "acquisition_source_ids are background, faction, companion, or milestone ids.",
            "Each skill_tree has an owner_companion_id from the characters stage and nodes "
            "whose skill_id exist here; edges reference node ids.",
            "fusion_recipes is an empty list.",
        ],
        brief,
        codex,
    )


def render_items_enemies_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-items-enemies",
) -> str:
    """Render Stage 7 prompt: items and enemy archetypes only."""
    return _render_stage_prompt(
        "Mechanics Designer",
        "Stage 7 (items and enemies)",
        ITEMS_ENEMIES_PROMPT_VERSION,
        request_id,
        [
            "Define every item- and enemy- id that earlier stages reference (see the index) "
            "plus 4-8 items and 2-4 enemy archetypes in total.",
            "Each enemy has at least one combat_skill_ids entry defined in the skills stage, "
            "escape_policy_id escape-default, and loot_table weights summing to at most "
            "power_rating.",
        ],
        brief,
        codex,
    )


def render_balance_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-balance",
) -> str:
    """Render Stage 8 prompt: point-buy, DC bands, XP thresholds, difficulty profiles."""
    return _render_stage_prompt(
        "Mechanics Designer",
        "Stage 8 (balance)",
        BALANCE_PROMPT_VERSION,
        request_id,
        [
            "point_buy is fixed: budget 27, minimum 8, maximum_before_bonus 15, "
            "maximum_after_bonus 17, cost_map 8:0,9:1,10:2,11:3,12:4,13:5,14:7,15:9.",
            "dc_bands are fixed: easy 8, standard 12, difficult 15, expert 18, "
            "exceptional 22, near_impossible 25.",
            'level_xp_thresholds start at "1": 0 and strictly increase for 5 levels.',
            "difficulty_profiles story/normal/hard use rational ratios as "
            "numerator/denominator objects; other balance dicts may be empty objects.",
        ],
        brief,
        codex,
    )


def render_stage_repair_prompt(
    stage: DraftStage,
    invalid_json: str,
    diagnostics: Sequence[str],
    context_summary: str,
    request_id: str = "req-repair-1",
) -> str:
    """Render a bounded diagnostic repair prompt for a failed generation stage."""
    diag_str = "\n".join(f"- {d}" for d in diagnostics)
    template = (
        f"You are the Storymode Campaign Stage Repair Assistant for stage '{stage}'.\n"
        f"The previous output failed schema validation with these exact errors:\n"
        "{diagnostics_str}\n\n"
        "Context Summary:\n"
        "<<<DATA\n"
        "{context_summary}\n"
        ">>>\n\n"
        "Invalid Previous JSON (Correct listed errors without changing valid content):\n"
        "<<<DATA\n"
        "{invalid_json}\n"
        ">>>\n\n"
        f"Return the corrected JSON matching the stage contract with request_id '{request_id}'.\n"
    )
    return render_template(
        template,
        {
            "diagnostics_str": diag_str,
            "context_summary": context_summary,
            "invalid_json": invalid_json,
        },
    )
