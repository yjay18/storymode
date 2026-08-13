# Worldbuilding and Style Bible

## Design-time ownership

Each campaign owns its own style bible and macro world. There is no global default
lore. `world.json` contains macro conflict, values/taboos, factions, major locations,
power-system rules/costs, and material/cultural conditions. Local residents, objects,
encounters, and secrets belong to area definitions. Major recurring characters and
companions belong to characters.

## Generation order

Generate small typed artifacts in dependency order:

1. normalized user brief and source summary;
2. meta and style bible;
3. macro world and factions;
4. major characters/companions;
5. areas, connections, residents, and objects;
6. standard/world-available skills, items, and enemies;
7. plot spine and balance;
8. art prompts;
9. cross-reference, graph, and balance validation;
10. human review and immutable publish.

Do not request one monolithic campaign JSON. A stage may repair only its own invalid
artifact with bounded diagnostics; cross-stage changes return to the owning stage.

## Style bible content

It defines tone, narrative voice, sensory palette, cultural/faction language, naming
patterns, concrete materials/industry, banned generic phrases, description rules,
and short original examples/anti-examples. Examples are references for traits, not
text to copy. Core UI skill labels remain readable: Stealth, Lockpicking, Hacking,
Persuasion, Engineering, Medicine, Survival, and similar terms.

Narration uses concrete sensory and indexical details that imply prior use, conflict,
maintenance, scarcity, or culture. It avoids encyclopedic exposition and generic
superlatives. Items and enemies derive flavor from materials, economy, faction marks,
and provenance while mechanics remain separately structured.

## Source handling

Imported novels/text/transcripts are untrusted local inputs. Record source type,
user-provided provenance, and a compact factual summary. Do not reproduce long source
passages in generated campaign data. The builder must distinguish inspiration from
canon chosen by the user and must flag uncertain extraction for review.

## Runtime restriction

Runtime narration may add non-canonical texture that does not imply a new persistent
fact. If a detail could affect future actions—an object, route, person, resource,
promise, clue, law, or relationship—it must already exist or first pass an explicit
validated opportunity/entity creation flow allowed by the campaign. v1 does not
allow runtime creation of major entities.
