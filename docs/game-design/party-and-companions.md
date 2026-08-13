# Party and Companions

## Membership

A party has exactly one protagonist and zero to three active companions. A companion
must be recruited, alive, available, co-located, and not hostile/captured/injured in a
way that blocks activity. Adding a fourth companion is rejected without modifying the
existing party. Party changes occur outside active combat.

Companion availability is authoritative runtime state driven by authored predicates
and committed events. Narration cannot make a companion join, leave, die, recover,
or change loyalty.

## Authored builds

Each companion defines role, starting resources, fixed skill tree, starting loadout,
upgrade choices, evolution/fusion recipes, backup skill behavior, and story hooks.
Players choose among authored upgrades when a branch exists but cannot freely respec,
transfer protagonist-only skills, or equip arbitrary skills.

The player selects companion actions in combat. Automated companion AI is outside
v1. The engine supplies the same target/mana/status validation as for the protagonist.

## Relationships

Campaign design contains baseline disposition and relationship rules; saves contain
only overrides/current values and revealed relationship facts. Changes come from
typed committed effects with bounded values. A single narration or repeated text may
not alter a relationship twice because command IDs are idempotent.

Personal arcs attach to protected milestones/opportunities and may change availability,
unlock skills, or lead to departure/death only through authored validated outcomes.

## Defeat, separation, and death

Companion defeat in ordinary combat does not imply death. Encounter consequence data
chooses injury, capture, separation, or recovery state. Permanent death must be an
authored, telegraphed allowed outcome and cannot make all protected campaign routes
unreachable without a defined successor.

## Fusion safeguard

Companion fusion follows `progression-and-skills.md`. Validation proves the fused
skill plus immediate/pending backup keeps the companion above the campaign's minimum
usable action count. The fusion transition is atomic; any failed safeguard rejects
source consumption and catalyst removal.
