# Combat Rules

## Combat state

An encounter contains stable participant IDs, current/max HP, current/max armour,
current/max mana, mana regeneration, speed, Dexterity, statuses, allowed escape/yield
policies, round number, ordered participant IDs, current index, and phase. Values are
snapshotted from validated definitions when combat starts.

Maximum player party size is four: protagonist plus up to three active companions.
Only living, present participants enter turn order.

## Encounter start and order

Order is Speed descending, then Dexterity descending. Participants still tied receive
one secure d20 tie-break at encounter start; the result and ordering are logged. A
remaining exact tie falls back to stable participant ID ascending. Preserve order
unless a defined status changes Speed; if so, recompute at the next turn boundary
without rerolling prior tie-breaks. No general initiative roll exists.

## Turn start

At the start of a living actor's turn:

1. expire statuses whose `expires_at` is this boundary;
2. apply defined start-turn status effects in stable `(priority, status_id)` order;
3. set `mana = min(mana_max, mana + mana_regen_per_turn)`;
4. if still able to act, expose the engine-calculated allowed commands.

The UI never invents an action that is not in this set.

## Allowed commands

- Use one equipped combat skill on targets satisfying its target rule.
- Defend.
- Flee if encounter policy currently permits it.
- Yield if encounter/enemy policy currently permits it.

Exploration free text is rejected while combat is active. Inventory use is absent in
v1 combat unless represented by an equipped authored combat skill.

## Skill resolution

Validate turn, actor state, loadout, mana, cooldown/status prevention, targets, and
explicit immunity before consuming anything. On success:

1. deduct mana;
2. calculate and apply each guaranteed base effect in definition order;
3. route positive damage through armour first, then HP;
4. if an effect table exists and at least one relevant target remains, roll one d20;
5. apply only the skill-defined band effect;
6. process defeat/encounter consequences;
7. journal one atomic combat transition and every roll;
8. advance to the next valid actor or resolve the encounter.

Skills do not make attack rolls. Explicit immunity may block a tagged effect, but it
must be visible before selection when known and cannot become a generic miss system.

## Damage, armour, and rounding

Apply authored additive modifiers, then rational multipliers in documented order.
Round non-negative final damage to nearest integer with `.5` upward; minimum is 0.
Difficulty damage multiplier applies once after skill/status modifiers.

`absorbed = min(current_armour, damage)`; subtract absorbed from armour and the
remainder from HP, clamped at zero. Armour does not regenerate naturally in combat.
When positive armour reaches zero, an authored `Exposed` status may apply only if the
encounter/skill definition specifies it; there is no global hidden penalty.

## Effect die bands

Default d20 bands, replaceable only by a validated per-skill table:

- natural 1: base effect remains; defined minor drawback only;
- 2–9: base effect only;
- 10–14: standard bonus;
- 15–19: strong bonus;
- natural 20: critical skill-specific bonus.

No bonus definition may revoke the guaranteed base effect. If no effect table exists,
do not roll. The model cannot select or author a bonus.

## Defend

Defend costs 0 mana and applies `Guarded` until the start of the actor's next turn.
The next positive incoming damage instance before expiry is reduced by 25%, rounding
the reduction down with a minimum reduction of 1, then consumes `Guarded`. It does
not stack or restore armour. Normal turn-start mana regeneration still occurs.

## Flee and yield

Flee consumes the turn and uses the encounter's authored escape check: Dexterity
modifier plus an explicitly named skill/gear/situation modifier against engine-owned
DC. Natural/outcome bands follow `difficulty-rules.md`. Success ends combat with the
enemy alive and applies authored world changes; partial/failure/critical failure apply
the encounter's validated consequence and combat continues if specified.

Yield has no die. If permitted, it ends combat and applies the authored capture,
loss, relocation, relationship, or plot consequence. It cannot delete a protected
milestone route.

## Defeat and victory

When HP reaches zero, the combatant becomes defeated and cannot act. Protagonist
defeat selects a validated soft-failure consequence (capture, injury, resource loss,
separation, relocation, heat, or scar). True game-over is allowed only for an
explicitly flagged and telegraphed endgame encounter.

Victory applies authored XP, loot references, flags, and encounter state exactly
once through command idempotency. Loot never comes from narrator text.
