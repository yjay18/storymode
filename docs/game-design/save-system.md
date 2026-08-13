# Save System

## Layout

```text
campaigns/<campaign_id>/saves/<save_id>/
├── state.json
├── journal.jsonl
├── narrative_memory.json
├── roll_log.jsonl
└── save_meta.json
```

Campaign design and assets are outside saves. A save binds to campaign ID, version,
and content fingerprint. All root JSON documents and JSONL rows have schema versions.

## Authoritative and derived data

`state.json` is the authoritative mutable snapshot: difficulty, playtime counter,
player/party, resources, inventory/equipment, skills/loadout/fusions, location, plot,
opportunities, known facts/flags, NPC and area overrides, clocks, encounter history,
pending check, active combat, command receipts, and revision.

`journal.jsonl` and `roll_log.jsonl` are append-only factual audit records tagged by
transaction and revision. `narrative_memory.json` is bounded derived narrator context.
`save_meta.json` is derived slot-display metadata. Derived files may be rebuilt and
must never override state.

## Slots and autosave

v1 offers five named manual slots per campaign plus one autosave slot. Slot names are
display strings with length/control-character limits; directory names are engine IDs.
Autosave commits after every resolved exploration action/check and combat transition.
A pending visible check is also committed so reopening cannot change its DC/stakes.

Maintain three rolling recovery snapshots of the last committed `state.json` and
derived display metadata. Snapshot rotation happens only after a successful new
commit and never deletes the only valid state.

## Commit and concurrency

Mutation requests include expected revision and unique command ID. Use the transaction
protocol in `docs/architecture/data-flow.md`. A stale expected revision is rejected.
A repeated command ID with identical payload returns its recorded result; the same ID
with different payload is a conflict. This prevents duplicate rolls on network retry.

Only one writer per save is allowed via an in-process lock plus a filesystem lock for
future multiple local workers. Read after commit validates the full root. Temporary
files stay in the same directory to preserve atomic-replace guarantees.

## Load and recovery

Load validates path containment, JSON limits, supported schema/campaign version,
campaign fingerprint, references, invariants, and journal/roll row framing. Unknown
or corrupt state is never coerced. Recovery may:

- restore one of the three validated snapshots after explicit user selection;
- rebuild missing/stale narrative memory or save metadata;
- mark prepared records newer than state revision as abandoned;
- migrate a supported older copy into a new temporary directory, validate it, then
  atomically install it while preserving the original backup.

## Migrations

Migrations are pure sequential functions from version N to N+1. They do no I/O, model
calls, randomness, or campaign editing. The migration runner copies first, applies
each step, validates at every version, writes a migration report, and retains the
original. Downgrades are not supported in v1.

## Narrative memory limits

Store the last 3–5 meaningful committed event summaries, current objective, unresolved
threads, active threats, and bounded relationship summaries. Store factual IDs and
short summaries, not full dialogue. Memory regeneration uses committed facts only.
