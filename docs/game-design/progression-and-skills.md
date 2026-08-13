# Progression and Skills

## Character statistics

The six statistics are Strength, Dexterity, Intelligence, Charisma, Constitution,
and Wisdom. Character creation spends exactly 27 points before a background bonus.

| Score | Cost |
|---:|---:|
| 8 | 0 |
| 9 | 1 |
| 10 | 2 |
| 11 | 3 |
| 12 | 4 |
| 13 | 5 |
| 14 | 7 |
| 15 | 9 |

Each pre-background score must be 8–15. A background defines explicit target stat
and bonus; the resulting score may not exceed the campaign schema maximum of 17.
The stat modifier is `floor((score - 10) / 2)`.

Character-creation validation reports all invalid fields together and never silently
changes allocation. The fixture uses standard readable skill names; world flavor
belongs in descriptions and availability.

## Non-combat skills

Skills have stable IDs, readable labels, associated stat, integer rank, availability
tags, and capability tags. A campaign chooses its skill list at design time. Rank is
0–5; absence and rank 0 are distinct only if a rule explicitly needs discoverability.

An exploration modifier names every component:

```text
stat modifier + skill rank + gear modifier + situational modifier
```

Gear and situational totals are independently bounded by `balance.json`. Duplicate
bonuses with the same stacking key do not stack; highest absolute applicable bonus
wins unless an item explicitly defines a different stacking rule.

## Character levels

Campaign `balance.json` defines a strictly increasing cumulative XP threshold table.
Level starts at 1 and is capped by that table. XP never decreases. Crossing one or
more thresholds in a single transition grants each missed level in order.

Each gained character level grants exactly one combat-skill upgrade token. Tokens
may be saved. Increasing a known combat skill by one level consumes one token and
must satisfy its authored prerequisites. Combat skill level is 1–5.

## Discovery and loadout

Combat skills are gained only from an authored acquisition source ID whose conditions
are satisfied: mentor, faction, boss reward, manual, item, ritual, discovery,
companion event, quest, or milestone. Discovery produces a journal event.

The protagonist may know more skills than are equipped and may equip at most four
distinct known combat skill IDs. Loadout changes occur only outside active combat.
Equipping does not change skill level or restore resources.

## Skill definition

Each combat skill defines level-specific mana cost, target rule, guaranteed base
effects, optional effect die table, tags, upgrade prerequisites, and bounded scaling.
The engine resolves only a definition in the published campaign pack; runtime prose
cannot add an effect.

## Fusion

A fusion transition requires all of the following in the same validated state:

1. two distinct compatible skills known by the same character;
2. both source skills at level 5;
3. an authored fusion recipe referencing both IDs without order dependence;
4. required milestone/faction/relationship conditions;
5. character at the authored fusion location or specialist;
6. required catalyst item and quantity;
7. no active combat.

The atomic transition consumes both source skills and catalyst, removes the sources
from the loadout, grants the evolved skill at authored starting level, and equips it
if at least one source was equipped. Two occupied source slots therefore become one;
other skills are never auto-equipped.

Fusion must change tactical function—such as damage plus armour break, control plus
area effect, or mobility plus support. Its validated power budget comes from
`balance.json`; it cannot merely double damage.

For a companion, the same transaction also grants the recipe's predetermined backup
skill, or records an explicit authored unlock condition if immediate grant is not
allowed. Validation rejects any recipe that could leave the companion with fewer
usable authored actions than the campaign minimum.

## Rejection behavior

Insufficient token, unknown skill, invalid level, occupied/duplicate loadout,
unmet fusion condition, missing catalyst, or active combat produces a typed rejection
and no partial mutation. All successful grants, upgrades, loadout changes, and fusions
record before/after IDs and committed revision in the journal.
