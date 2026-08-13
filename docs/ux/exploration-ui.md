# Exploration UI

## Layout

- Header: campaign, area, difficulty, save slot, save/connection/model status.
- Scene: cached area background/fallback with area title and accessible description.
- Narrative log: factual roll cards and narration, visually distinct but chronologically
  ordered. State facts do not depend on interpreting prose.
- Context rail: party resources, current objective, 3–7 active opportunities, visible
  clocks, and present known entities.
- Composer: multiline free-text input, submit, character count, and model status.
- Utility panels: character, inventory, party, journal, roll history, save/settings.

## Submission states

`idle -> interpreting -> rejected | pending_check | committing -> narrating -> ready`.
Disable duplicate submission while command status is unknown. Preserve the command ID
and text for a transport retry. A deterministic rejection shows concise in-world
redirect plus an expandable stable error reason; it does not append invented narration.

## Visible check

The check panel shows action summary, stat, skill, gear/situational modifiers, raw
formula, base DC label/value, difficulty adjustment, final DC, explicit stakes, luck
options, Roll, and Cancel. It must not animate or draw until the server resolves the
confirmed command. Afterward show raw die, modifiers, total, DC, band, luck spent, and
confirmed effects; animation is cosmetic and cannot choose the number.

If a roll response times out, query command status with the same command ID. Never
send a fresh resolve command until the server confirms no commit.

## Partial and invalid intent

For `partial`, show “I can treat that as…” and the engine-approved reinterpretation;
require confirmation before a consequential check. For invalid, maintain immersion
with the approved redirect while making the missing entity/capability discoverable in
an accessible details element. Do not blame the local model.

## Narrative authority

Committed result cards remain even when narration fails. Fallback copy identifies
exact effects. Model prose is rendered as escaped plain text with speaker labels from
allowed server metadata. The UI never extracts state from prose.
