# Runtime and Save Contracts (Schema Version 1)

## `state.json` — `RuntimeState`

Required root fields:

- `schema_version: Literal[1]`
- `campaign_id`, `campaign_version`, `campaign_fingerprint`, `save_id`
- `revision: int >= 0`
- `last_command_receipts: list[CommandReceipt]` bounded to the latest 100
- `difficulty: story | normal | hard`
- `play_seconds: int >= 0` (explicit active play accumulation only)
- `player: PlayerState`
- `party: PartyState`
- `location: LocationState`
- `plot: PlotState`
- `known_fact_ids: set[EntityId]`
- `world_flags: dict[EntityId, bool | int | str]` with schema-defined keys/types
- `npc_overrides`, `area_object_overrides`, `clocks`
- `encounter_history: list[EncounterSummary]` bounded by configured retention
- `pending_check: PendingCheck | null`
- `combat: CombatState | null`

No timestamp determines game mechanics. `revision` increments once per committed
mutation, including create/cancel pending check.

## Player and party

`PlayerState`: `id`, `name`, `background_id`, `stats` (all six), `level`, `xp`,
`hp/max_hp`, `armour/max_armour`, `mana/max_mana`, `mana_regen`, `speed`, `luck/current`
and `capacity`, `inventory`, `equipment`, `non_combat_skill_ranks`,
`known_combat_skills`, `combat_loadout`, `upgrade_tokens`, `fusion_history`, statuses.

`KnownCombatSkill`: `skill_id`, `level` 1–5, `acquisition_source_id`.
Inventory entries are item ID plus positive quantity and instance data only for unique
items. Equipment references owned entries. Loadout has at most four distinct known IDs.

`PartyState`: `protagonist_id`, ordered `active_companion_ids` (max three), and
`companions: dict[id, CompanionRuntimeState]`. Companion runtime includes resources,
known authored skills/loadout, relationship value/state, availability, story flags,
injury/capture/hostility/life state, and fusion history.

## Location, objects, NPCs, and plot

`LocationState`: `area_id`, `zone_anchor`, `discovered_area_ids`.
NPC overrides include location/anchor, availability/life state, disposition,
relationship, and revealed knowledge only when different from design baseline.
Object overrides include finite state enum, discovered flag, quantities, and allowed
effect-specific data. Unknown override fields are forbidden.

`PlotState`: milestone states, opportunity instances, current milestone IDs, and
ending state. Milestone state is `locked | available | active | resolved | failed`
where `failed` is allowed only when protected campaign reachability remains.
Opportunity shape/state follows the plot document and records origin/parent/predecessor.

`ClockState`: `clock_id`, `current`, `maximum`, `completed`, and last advancement
revision. Current is clamped by validation only at effect construction; persisted
out-of-range values are corruption, not silently clamped.

## Pending check

`PendingCheck`: `check_id`, `source_command_id`, `source_revision`, `original_input`,
`resolved_operation`, `actor_id`, `target_ids`, `stat`, `skill_id?`, named modifier
components, semantic difficulty, `base_dc`, difficulty adjustment, `final_dc`, stakes,
and `allowed_outcomes` for all five bands. It contains no die result.

Exactly one may exist, only outside combat, and `source_revision < state.revision` is
valid because creating it commits the next revision. Resolution verifies all referenced
preconditions still hold in the current snapshot.

## Combat state

`CombatState`: `encounter_id`, `phase`, `round`, `order`, `current_index`, participant
map, tie-break records, escape/yield policies, encounter modifiers, and origin IDs.
Participants contain snapshotted numeric resources, statuses, skills/loadout, faction,
and side. Phase is `active | resolving | victory | defeat | escaped | yielded`; only
`active` is stored across normal command boundaries in v1, with terminal state reduced
to encounter history during the same transition.

## Command receipt

`CommandReceipt`: `command_id`, canonical request hash, committed revision, result
kind, safe result summary, and roll IDs. If a command ID repeats, matching hash returns
this result and non-matching hash is a conflict. Receipt eviction must never occur
while a client retry can be in flight; v1's 100 receipt bound is also covered by the
autosave snapshot history.

## `journal.jsonl` — `JournalEvent`

Each line independently validates with: `schema_version`, `event_id`, `transaction_id`,
`revision`, `event_index`, UTC `recorded_at`, `command_id`, `event_type`, `actor_ids`,
`entity_ids`, `resolved_intent?`, `roll_ids`, `effects`, and `discovered_fact_ids`.
Effects are typed discriminated unions, not arbitrary patches. Ordering is revision
then event index. Multiple prepared rows may share a transaction.

## `roll_log.jsonl` — `RollRecord`

Fields: `schema_version`, `roll_id`, `transaction_id`, `revision`, UTC `recorded_at`,
`command_id`, `reason`, `die_sides`, `raw_rolls`, `selected_roll_index`, named integer
modifiers, `total`, `dc?`, `difficulty`, `outcome`, `confirmed_effect_ids`, and
`supersedes_roll_id?` for luck rerolls. A d20 record has `die_sides=20` and every raw
value 1–20. Tie-break rolls omit DC. Prepared rows above state revision are not facts.

## `narrative_memory.json` — `NarrativeMemory`

Fields: root identity/version, `derived_from_revision`, 3–5 `recent_events`, current
objective, bounded relationship summaries, unresolved thread IDs/summaries, and active
threat IDs/summaries. Max serialized size is 32 KiB. It contains no whole journal,
hidden canonical facts, or prompt instructions from imported content.

## `save_meta.json` — `SaveMeta`

Fields: root identity/version, `derived_from_revision`, slot kind/name, player display
name/level, campaign title, current area display name, difficulty, active play seconds,
UTC created/updated timestamps, and recovery status. This file is display-only.

## Invariants

- All current resources are between zero and maximum.
- Luck capacity equals selected profile unless a versioned authored effect explicitly
  permits a bounded override; current never exceeds capacity.
- References resolve against the bound campaign or runtime instances of allowed type.
- Active party, location, pending check, and combat mode constraints are consistent.
- Current milestone/opportunity graph preserves protected reachability.
- State revision never trails a committed command receipt or considered log row.
