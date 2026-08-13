# Screen Map

## Routes

```text
Startup preflight
└── Home / Campaign Library
    ├── Guided Builder
    │   ├── Brief and source
    │   ├── World preferences
    │   ├── Character/mechanics preferences
    │   ├── Generation progress
    │   └── Campaign review and validation
    ├── Quick Prompt
    │   └── Generation progress -> same review and validation
    ├── Campaign Detail
    │   ├── New Character -> Save Slot -> Exploration
    │   ├── Continue Save -> Exploration or Combat
    │   └── Validate/inspect design and assets
    └── Save Recovery

Play shell
├── Exploration
│   ├── Visible check confirmation
│   └── Roll result/history
├── Combat (exclusive mode)
├── Character sheet and progression
├── Inventory/equipment
├── Party/relationships
├── Journal/objectives/opportunities/clocks
└── Save/load/settings
```

## Startup preflight

Show application/data-schema status, writable campaign root, Ollama reachability,
configured text/image model capabilities, and deterministic-core readiness separately.
A missing image model is a warning. A missing text model blocks model-dependent play
but not campaign/save inspection, validation, settings, or deterministic tests. Never
offer a cloud sign-in/fallback.

## Navigation invariants

- Current campaign/save/revision and unsatisfied recovery warning remain visible.
- Combat replaces exploration input and prevents navigation to state-changing loadout,
  party, or load operations; read-only inspection remains available.
- Opening panels does not advance time/clocks, call a narrator, or autosave.
- Returning from a transient transport error re-fetches authoritative state before a
  new mutation.

## Responsive target

Desktop-first at 1280×720, usable down to 360 CSS pixels. On narrow screens, secondary
panels become drawers with focus trapping; primary text/action controls remain first
in DOM order. No critical action exists only on hover.
