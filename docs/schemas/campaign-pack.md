# Campaign Pack Contract (Schema Version 1)

## Common conventions

All files are UTF-8 JSON root objects, not bare arrays. Each root has
`schema_version: 1`, `campaign_id`, and its named collection/object. IDs match
`^[a-z][a-z0-9_-]{2,63}$`; display strings are trimmed and 1–120 characters unless a
field states otherwise. Descriptions are capped at 2,000 characters. Lists reject
duplicate IDs. Numeric values are finite integers unless explicitly ratios.

`CampaignPack` is an in-memory aggregate loaded from the following files. It is not
written as an extra monolithic file.

## `meta.json` — `CampaignMeta`

- `schema_version: Literal[1]`
- `campaign_id: EntityId`
- `campaign_version: str` matching `MAJOR.MINOR.PATCH`
- `title: str` (1–120)
- `theme: fantasy | sci_fi | apocalyptic | custom`
- `source_type: prompt | novel | plain_text | comic_transcript | custom`
- `source_summary: str` (1–4,000; no full source text)
- `default_difficulty: story | normal | hard`
- `campaign_length: short | medium | long | custom`
- `art_style_ref: EntityId` referencing the style bible's `style_id`
- `created_at: UTC datetime` (audit only)
- `content_fingerprint: str | null` (null in draft, lowercase SHA-256 on publish)
- `status: draft | published`

The publish fingerprint is SHA-256 of canonical JSON bytes for every design file
except the `content_fingerprint` field itself, ordered by fixed filename then content.
Canonical JSON uses UTF-8, sorted keys, no insignificant whitespace, and no NaN.

## `style_bible.json` — `StyleBibleFile`

- root: version/campaign IDs plus `style_bible: StyleBible`
- `StyleBible`: `style_id`, `tone`, `narrative_voice`, `sensory_palette`,
  `faction_language_notes`, `naming_conventions`, `banned_phrases`,
  `description_requirements`, `examples`, `anti_examples`, `art_direction`
- sensory palette is an object with non-empty lists for `sounds`, `smells`,
  `materials`, `lighting`, and `textures`
- examples/anti-examples: 1–5 original strings each, max 800 characters each
- banned phrases: unique case-folded strings; validation warns, rather than rejects,
  if generated prose contains one

## `world.json` — `WorldFile`

- root fields plus `world: WorldDefinition`
- `WorldDefinition`: `name`, `core_conflict`, `power_system`, `values`, `factions`,
  `major_locations`, `material_conditions`
- `PowerSystem`: `rules`, `costs`, `access_restrictions`, `side_effects`; all non-empty
- `FactionDefinition`: `id`, `name`, `goals`, `resources`, `hypocrisy`,
  `language_style`, `visual_markings`, `relationship_edges`
- `FactionRelationship`: `target_faction_id`, `stance` (-100..100), `summary`
- `MajorLocation`: `id`, `name`, `summary`; it is macro lore and may be referenced by
  one or more area zones

Faction relationships must reference other factions, never self, and have unique
targets. The world file must not contain local resident NPC records.

## `areas.json` — `AreasFile`

- root fields plus `areas: list[AreaDefinition]` (1–500)
- `AreaDefinition`: `id`, `name`, `major_location_id`, `description`, `art_prompt`,
  `danger_level` (1–10), `connected_area_ids`, `local_faction_ids`, `residents`,
  `objects`, `encounters`, `secrets`
- `ResidentNpc`: `id`, `name`, `role`, `faction_id?`, `availability`, `location_anchor`,
  `initial_disposition` (-100..100), `knowledge_tags`, `personal_goal`,
  `interaction_hooks`
- availability: `available | unavailable | hidden | dead`
- `AreaObject`: `id`, `name`, `description`, `location_anchor`, `state`,
  `interactable_tags`, `capability_requirements`, `allowed_effect_ids`
- `EncounterEntry`: `id`, `enemy_archetype_ids`, `condition`, `weight` (1–100),
  `escape_policy_id`, `consequence_ids`
- `AreaSecret`: `id`, `summary`, `lead_fact_ids`, `reveal_conditions`,
  `core_clue: bool`

Connections cannot self-reference, must be unique, and must be reciprocal unless an
edge is represented in the future as explicitly one-way. v1 fixtures use reciprocal
connections. Resident/object IDs are globally unique across the campaign.

## `characters.json` — `CharactersFile`

- root fields plus `protagonist_backgrounds`, `major_npcs`, and `companions`
- `BackgroundDefinition`: `id`, `name`, `description`, `stat_bonus` (one stat, +1 or
  +2), `starting_skill_ids`, `starting_item_ids`, `starting_fact_ids`
- `MajorNpcDefinition`: `id`, `name`, `role`, `faction_id?`, `home_area_id`,
  `knowledge_tags`, `goal`, `interaction_hooks`
- `CompanionDefinition` extends major NPC data with `combat_role`, `base_stats`,
  `skill_tree_id`, `starting_skill_ids`, `starting_loadout`, `relationship_rules`,
  `story_hook_ids`, `availability_rules`, `minimum_usable_actions` (1–4)

Exactly six base stats are present, each within 1–30. Major NPC IDs cannot duplicate
area resident IDs. Companion starting loadout is unique, at most four, and drawn from
starting skills.

## `skills.json` — `SkillsFile`

- root fields plus `point_buy`, `non_combat_skills`, `combat_skills`, `skill_trees`,
  and `fusion_recipes`
- `PointBuyDefinition`: `budget=27`, `minimum=8`, `maximum_before_bonus=15`,
  `maximum_after_bonus=17`, and exact cost map from the design document
- `NonCombatSkill`: `id`, `name`, `description`, `stat`, `rank_min=0`, `rank_max=5`,
  `availability_tags`, `capability_tags`
- `CombatSkill`: `id`, `name`, `description`, `tags`, `acquisition_source_ids`,
  `levels` (exactly levels 1..5), `allowed_actor_types`
- `CombatSkillLevel`: `level`, `mana_cost` (0–10), `target_rule`, `base_effects`,
  `effect_die?`, `prerequisite`
- `EffectDefinition`: `effect_id`, `kind`, `magnitude`, `duration?`, `status_id?`,
  `stacking_key?`; kinds are a closed engine enum
- `EffectDieTable`: exactly one definition for `natural_1`, `low`, `standard`,
  `strong`, and `natural_20`; bands use the combat document
- `SkillTree`: `id`, `owner_companion_id?`, `nodes`, `edges`
- `FusionRecipe`: `id`, two unique sorted `source_skill_ids`, `result_skill_id`,
  `catalyst_item_id`, `catalyst_quantity`, `unlock_conditions`, `location_or_specialist_ids`,
  `companion_backup_skill_id?`, `power_budget`

Fusion result and backup cannot equal a source. References must exist and recipes are
unique by unordered source pair plus actor scope.

## `enemies.json` — `EnemiesFile`

- root fields plus `enemy_archetypes`
- `EnemyArchetype`: `id`, `name`, `description`, `faction_id?`, `base_hp` (1–10,000),
  `base_armour` (0–10,000), `speed` (0–100), `dexterity` (1–30), `base_mana`
  (0–1,000), `mana_regen` (0–100), `combat_skill_ids`, `behavior_profile`,
  `escape_policy_id`, `power_rating` (1–10,000), `loot_table`, `portrait_prompt`,
  `art_style_ref`
- `LootEntry`: `item_id`, `minimum_quantity`, `maximum_quantity`, `weight`

Every enemy has at least one usable zero-cost or sustainable combat action. Power
rating is recomputed/checked by balance validation; it is not trusted merely because
the file provides it.

## `items.json` — `ItemsFile`

- root fields plus `items`
- `ItemDefinition`: `id`, `name`, `type`, `rarity`, `mechanics`, `requirements`,
  `capability_tags`, `stacking_key?`, `flavour_text`, `provenance`, `max_stack`
- type: `weapon | armour | consumable | tool | catalyst | quest | accessory`
- rarity: `common | uncommon | rare | exceptional | unique`
- mechanics are typed closed-union effects; arbitrary formula strings are forbidden
- flavour text is 1–2 sentences and max 400 characters

Unique items have `max_stack=1`. Catalyst references in recipes must point to item
type `catalyst`. Quest items cannot be consumed by a generic use action.

## `plot.json` — `PlotFile`

- root fields plus `start_milestone_ids`, `milestones`, `authored_opportunities`,
  `ending_milestone_ids`, `clock_definitions`
- `MilestoneDefinition`: fields listed in the plot design document, including
  `id`, `canonical_truth`, `narrative_purpose`, `required_outcome_ids`,
  `allowed_approach_tags`, `forbidden_changes`, `preconditions`,
  `valid_next_milestone_ids`, `difficulty_band`, `pacing_weight`, `cycle_allowed`
- `OpportunityDefinition`: `id`, `parent_milestone_id`, `title`, `description`,
  `referenced_entity_ids`, `allowed_outcome_ids`, `preconditions`,
  `expiry_conditions`, `balance_rating`
- `ClockDefinition`: `id`, `name`, `maximum`, `visibility`, `trigger_event_types`,
  `completion_effect_ids`

Every ending is reachable from a start under at least one satisfiable structural path.
Core clues and required outcomes must have a fail-forward route.

## `balance.json` — `BalanceFile`

- root fields plus `difficulty_profiles`, `level_xp_thresholds`, `dc_bands`,
  `modifier_limits`, `effect_limits`, `enemy_power_formula`, `encounter_targets`,
  `fusion_limits`, `boss_allowances`
- ratios are `{numerator: positive int, denominator: positive int}`; never floats
- all three profiles (`story`, `normal`, `hard`) are required with exact DC/HP/damage/
  luck values from `difficulty-rules.md`
- XP keys begin at level 1 threshold 0 and rise strictly
- modifier/effect bounds are explicit by level and tag
- formulas are structured coefficient fields interpreted by engine code, never `eval`

## Cross-file validation order

1. Parse every root independently.
2. Confirm identical schema/campaign IDs and draft/published rules.
3. Build a global ID index and reject duplicate IDs across entity namespaces where
   references could be ambiguous.
4. Resolve all references with expected entity type.
5. Validate area connectivity, skill trees, milestone graph, and opportunity parents.
6. Validate point-buy constants, effect/mana bounds, enemy power, encounter targets,
   fusions, companion safeguards, and difficulty profiles.
7. On publish, compute/verify fingerprint and asset prompt references.

Return all deterministic diagnostics as `{code, file, json_pointer, message, related_ids}`
in stable file/pointer/code order.
