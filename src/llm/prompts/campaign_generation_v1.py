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


def render_world_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-world",
) -> str:
    """Render Stage 2 prompt: World rules, factions, and magic systems."""
    ctx = _extract_codex_context(brief, codex)
    template = (
        "You are the Storymode World & Rules Architect.\n"
        "Generate the Stage 2 response matching this contract:\n"
        "{\n"
        '  "contract_version": 1,\n'
        f'  "prompt_version": "{WORLD_PROMPT_VERSION}",\n'
        f'  "request_id": "{request_id}",\n'
        '  "stage": "rules",\n'
        '  "world": {\n'
        '    "schema_version": 1,\n'
        '    "campaign_id": "<campaign_id>",\n'
        '    "campaign_version": "1.0.0",\n'
        '    "lore": {\n'
        '      "premise": "<premise>",\n'
        '      "magic_system": "<magic rules>",\n'
        '      "technology_level": "<tech level>",\n'
        '      "cosmology": "<cosmology>",\n'
        '      "history": ["<historical event 1>", "<historical event 2>"],\n'
        '      "taboos": ["<taboo 1>", "<taboo 2>"]\n'
        "    },\n"
        '    "factions": [\n'
        "      {\n"
        '        "faction_id": "f_1",\n'
        '        "name": "<name>",\n'
        '        "archetype": "<archetype>",\n'
        '        "description": "<desc>",\n'
        '        "goals": ["<goal>"],\n'
        '        "resources": ["<resource>"],\n'
        '        "allies": [],\n'
        '        "rivals": []\n'
        "      }\n"
        "    ]\n"
        "  }\n"
        "}\n\n"
        "Context Brief:\n"
        "<<<DATA\n"
        "{brief_json}\n"
        ">>>\n"
    )
    return render_template(template, {"brief_json": json.dumps(ctx, indent=2)})


def render_areas_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-areas",
) -> str:
    """Render Stage 3 prompt: Explorable areas, locations, and landmarks."""
    ctx = _extract_codex_context(brief, codex)
    template = (
        "You are the Storymode Environmental Designer.\n"
        "Generate the Stage 3 response matching this contract:\n"
        "{\n"
        '  "contract_version": 1,\n'
        f'  "prompt_version": "{AREAS_PROMPT_VERSION}",\n'
        f'  "request_id": "{request_id}",\n'
        '  "stage": "areas",\n'
        '  "areas": {\n'
        '    "schema_version": 1,\n'
        '    "campaign_id": "<campaign_id>",\n'
        '    "campaign_version": "1.0.0",\n'
        '    "areas": [\n'
        "      {\n"
        '        "area_id": "area_1",\n'
        '        "name": "<name>",\n'
        '        "danger_level": 1,\n'
        '        "summary": "<summary>",\n'
        '        "description": "<sensory description>",\n'
        '        "biome": "<biome>",\n'
        '        "controlling_faction": "<faction_id>",\n'
        '        "connected_areas": [],\n'
        '        "landmarks": ["<landmark 1>"],\n'
        '        "objects": []\n'
        "      }\n"
        "    ]\n"
        "  }\n"
        "}\n\n"
        "Context Brief:\n"
        "<<<DATA\n"
        "{brief_json}\n"
        ">>>\n"
    )
    return render_template(template, {"brief_json": json.dumps(ctx, indent=2)})


def render_plot_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-plot",
) -> str:
    """Render Stage 4 prompt: Plot milestones, opportunities, and clocks."""
    ctx = _extract_codex_context(brief, codex)
    template = (
        "You are the Storymode Narrative Director.\n"
        "Generate the Stage 4 response matching this contract:\n"
        "{\n"
        '  "contract_version": 1,\n'
        f'  "prompt_version": "{PLOT_PROMPT_VERSION}",\n'
        f'  "request_id": "{request_id}",\n'
        '  "stage": "plot",\n'
        '  "plot": {\n'
        '    "schema_version": 1,\n'
        '    "campaign_id": "<campaign_id>",\n'
        '    "campaign_version": "1.0.0",\n'
        '    "milestones": [\n'
        "      {\n"
        '        "milestone_id": "ms_1",\n'
        '        "title": "<title>",\n'
        '        "summary": "<summary>",\n'
        '        "required_conditions": [],\n'
        '        "completion_outcomes": ["<outcome>"],\n'
        '        "is_major": true\n'
        "      }\n"
        "    ],\n"
        '    "clocks": []\n'
        "  }\n"
        "}\n\n"
        "Context Brief:\n"
        "<<<DATA\n"
        "{brief_json}\n"
        ">>>\n"
    )
    return render_template(template, {"brief_json": json.dumps(ctx, indent=2)})


def render_characters_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-chars",
) -> str:
    """Render Stage 5 prompt: Major NPCs and recruitable companions."""
    ctx = _extract_codex_context(brief, codex)
    template = (
        "You are the Storymode Character & NPC Designer.\n"
        "Generate the Stage 5 response matching this contract:\n"
        "{\n"
        '  "contract_version": 1,\n'
        f'  "prompt_version": "{CHARACTERS_PROMPT_VERSION}",\n'
        f'  "request_id": "{request_id}",\n'
        '  "stage": "characters",\n'
        '  "characters": {\n'
        '    "schema_version": 1,\n'
        '    "campaign_id": "<campaign_id>",\n'
        '    "campaign_version": "1.0.0",\n'
        '    "characters": [\n'
        "      {\n"
        '        "character_id": "char_1",\n'
        '        "name": "<name>",\n'
        '        "archetype": "<archetype>",\n'
        '        "cultural_origin": "<region>",\n'
        '        "appearance": "<attire and physical appearance>",\n'
        '        "personality": "<personality shaped by cultural values>",\n'
        '        "dialogue_quirks": ["<idiom or speech pattern>"],\n'
        '        "faction_id": "f_1",\n'
        '        "home_area_id": "area_1"\n'
        "      }\n"
        "    ]\n"
        "  }\n"
        "}\n\n"
        "Context Brief:\n"
        "<<<DATA\n"
        "{brief_json}\n"
        ">>>\n"
    )
    return render_template(template, {"brief_json": json.dumps(ctx, indent=2)})


def render_skills_prompt(
    brief: BuilderBrief,
    codex: WorldCodex | None = None,
    request_id: str = "req-gen-skills",
) -> str:
    """Render Stage 6 prompt: Combat skills, items, enemies, and balance."""
    ctx = _extract_codex_context(brief, codex)
    template = (
        "You are the Storymode Systems & Combat Balance Designer.\n"
        "Generate the Stage 6 response (Skills, Items, Enemies, Balance) matching this contract:\n"
        "{\n"
        '  "contract_version": 1,\n'
        f'  "prompt_version": "{SKILLS_PROMPT_VERSION}",\n'
        f'  "request_id": "{request_id}",\n'
        '  "stage": "skills",\n'
        '  "skills": {\n'
        '    "schema_version": 1,\n'
        '    "campaign_id": "<campaign_id>",\n'
        '    "campaign_version": "1.0.0",\n'
        '    "skills": []\n'
        "  },\n"
        '  "items": {\n'
        '    "schema_version": 1,\n'
        '    "campaign_id": "<campaign_id>",\n'
        '    "campaign_version": "1.0.0",\n'
        '    "items": []\n'
        "  },\n"
        '  "enemies": {\n'
        '    "schema_version": 1,\n'
        '    "campaign_id": "<campaign_id>",\n'
        '    "campaign_version": "1.0.0",\n'
        '    "enemies": []\n'
        "  },\n"
        '  "balance": {\n'
        '    "schema_version": 1,\n'
        '    "campaign_id": "<campaign_id>",\n'
        '    "campaign_version": "1.0.0",\n'
        '    "difficulty_scalers": {\n'
        '      "story": 0.8,\n'
        '      "normal": 1.0,\n'
        '      "hardcore": 1.3\n'
        "    }\n"
        "  }\n"
        "}\n\n"
        "Context Brief:\n"
        "<<<DATA\n"
        "{brief_json}\n"
        ">>>\n"
    )
    return render_template(template, {"brief_json": json.dumps(ctx, indent=2)})


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
