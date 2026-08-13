# Combat UI

## Entry

Before lock-in, exploration supports negotiation, preparation, inspection, and flee
where the scene allows. When the server starts combat, focus moves to the combat
heading and the exploration composer is removed, not merely disabled off-screen.

## Layout

- Encounter header: round, current actor, objective, flee/yield availability.
- Turn order: ordered participant cards with current/defeated/status states.
- Ally and target panels: HP, armour, mana values and text labels, not bars alone.
- Action grid: up to four equipped skills plus Defend and conditional Flee/Yield.
- Skill detail: mana cost, target rule, guaranteed base effect, possible d20 bonus
  bands, disabled reason, and affected targets.
- Combat log: factual state/roll records first; optional narration secondary.

## Interaction

The server supplies allowed command IDs/targets. Selecting a skill then target creates
one review step listing cost/base effect before Submit. Disable commands after submit
until authoritative response/status query. For multi-target skills, target rules come
from the server result rather than UI recomputation.

Effect die presentation always says the base effect already applied. Show raw d20,
band, and exact extra effect. If base effect ended the encounter and no die was rolled,
do not simulate one.

## Defend, flee, yield, and defeat

Defend describes Guarded duration/reduction. Flee shows current availability and
stakes; a permitted flee check uses the same accessible roll card. Yield requires a
confirmation summarizing known authored consequences. Protagonist defeat transitions
to a consequence screen—capture/injury/etc.—unless the server explicitly reports a
telegraphed game over.

## Mode guards

Loadout editing, party changes, save switching, campaign editing, and free-text input
are unavailable in active combat. Manual save may snapshot current combat if the save
contract permits; loading another slot requires leaving through the server-controlled
flow to avoid ambiguous state.
