# Difficulty and Check Rules

## Check necessity

Roll only when success is uncertain and failure or partial success would materially
change state. Trivial, impossible, already-resolved, and consequence-free actions do
not roll. Impossibility is rejected; it cannot be overcome by a natural 20.

## Exploration formula

```text
total = d20 + stat_modifier + skill_rank + gear_modifier + situational_modifier
```

Every component is named and displayed. A proposal may suggest semantic difficulty
and reasoning; the engine maps to base DC and applies the chosen save difficulty.

| Label | Base DC |
|---|---:|
| Easy | 8 |
| Standard | 12 |
| Difficult | 15 |
| Expert | 18 |
| Exceptional | 22 |
| Near-impossible | 25 |

Near-impossible may use a campaign-authored DC above 25 within the schema maximum.

## Outcome precedence

For a physically/world-rule possible action:

1. Natural 20 -> critical success.
2. Natural 1 -> critical failure.
3. Total at least DC -> success.
4. Total from `DC-3` through `DC-1` -> near miss/partial success.
5. Lower total -> failure.

Each check specification defines allowed state effects for these bands before the
roll. A critical result may choose only a validated effect; it does not authorize new
facts. Failure must create a coherent cost/route, not “nothing happens.” Core clues
remain obtainable; a failed clue check changes cost, exposure, position, or route.

## Profiles and integer math

| System | Story | Normal | Hard/Tactical |
|---|---:|---:|---:|
| DC adjustment | -2 | 0 | +2 |
| Enemy HP ratio | 7/10 | 1 | 5/4 |
| Enemy damage ratio | 1/2 | 1 | 3/2 |
| Enemy armour | unchanged | unchanged | unchanged |
| Luck capacity | 3 | 2 | 1 |
| Recovery/failure/tactics | authored `story` variant | authored `normal` | authored `hard` |

Scale positive HP/damage by integer rational arithmetic and round to nearest integer,
ties upward; scaled positive HP has minimum 1. Apply each difficulty ratio exactly
once when encounter stats/effects are materialized. Never alter a random draw.

## Luck

Luck is a save resource with profile capacity, not a point-buy stat. One point may:

- reroll a just-failed non-critical exploration/flee check, accepting the new roll;
- add +2 after seeing a non-critical result, then recompute its band; or
- downgrade a natural 1 from critical failure to ordinary failure, never to success.

Both rolls in a reroll are logged and linked. Luck cannot affect tie-break rolls or
combat effect dice in v1. Capacity is restored only by an explicit safe recovery or
milestone effect defined in campaign data, never real-world waiting.

## Threat clocks, not time

Difficulty may select authored recovery and consequence variants. It never advances
world state from elapsed wall time. Clocks advance only from listed committed events,
such as loud combat, failed stealth, betrayal, milestone completion, or a safe rest
whose definition explicitly advances pressure.
