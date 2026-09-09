# Playtest 01 — salt-ledger combat on Normal

**Date:** 2026-09-09 · **Slice:** PLAY-07 · **Campaign:** `salt-ledger` 1.0.0 · **Difficulty:** Normal
**Evidence:** `docs/research/playtest-01.jsonl` (270 combats, one JSON object per combat)

This proposes changes. It does not apply any. Per PLAY-07, each balance change needs its own
slice, and an ADR if it changes a formula.

## How this was run, and how it differs from the slice

PLAY-07 asks for a played session. The session could not be driven through the API, because
**combat in `salt-ledger` is unreachable from a new save**:

- A new save starts in `areas[0]` (`engine/state/creation.py:91`), which for this campaign is
  `area-customs-hall`. That area authors **zero encounters**.
- All three encounters live in the other three areas.
- `POST /combat/start` only accepts an encounter in the player's current area
  (`api/routes/combat.py:140`) — asking for one elsewhere returns
  `422 Encounter 'enc-quay-runners' not found in area 'area-customs-hall'`.
- Nothing served changes the player's area. The engine has a `travel` operation and validates
  it (`engine/actions/operations.py:31`), but `_build_candidates`
  (`engine/actions/use_cases.py:219`) offers only the area's **objects and residents** — never
  connected areas — so a travel mention can never resolve, and no code path writes
  `state.location` outside combat consequences.

So this playtest drives `CombatUseCases` directly, placing the protagonist in each encounter's
area, with the **production `SecureRandomSource`** — every roll below is a real roll. That is
faithful for balance numbers and unfaithful for reachability. The reachability gap is the first
finding.

Each of the 3 encounters was run 30 times under 3 player policies (270 combats):

| Policy | Behaviour |
|---|---|
| `strike` | Always Ledger Strike (0 mana) |
| `ward` | Keep Salt Ward up (recast every 2 rounds), else strike |
| `defend` | Defend at or below 50% HP, else strike |

## Observed rolls

1,573 d20 draws, mean **10.47** (uniform expects 10.50), all 20 faces present, per-face counts
60–92. The roller shows no visible bias; nothing below is an RNG artifact.

## Damage per round and encounter length

Protagonist at level 1: **10 HP**, 5 mana, armour **2 of a maximum 5**, knows Ledger Strike and
Salt Ward.

| Policy | Encounter | Enemies (power) | Player deals | Player takes | Rounds (med) | Wins |
|---|---|---|---|---|---|---|
| strike | `enc-quay-runners` | 2× runner (6+6) | 3.0 hp/rd | **5.0 hp/rd** | 2 | **0/30** |
| strike | `enc-cellar-guard` | runner + bruiser (6+12) | 2.8 hp/rd | **5.0 hp/rd** | 2 | **0/30** |
| strike | `enc-drowned` | 1× drowned thing (15) | 3.8 hp/rd | 0.2 hp/rd | 8 | 30/30 |
| ward | `enc-quay-runners` | | 0.5 hp/rd | 5.0 hp/rd | 2 | 0/30 |
| ward | `enc-cellar-guard` | | 1.0 hp/rd | 5.0 hp/rd | 2 | 0/30 |
| ward | `enc-drowned` | | 1.9 hp/rd | 0.2 hp/rd | 16 | 30/30 |
| defend | `enc-quay-runners` | | 3.0 hp/rd | 5.0 hp/rd | 2 | 0/30 |
| defend | `enc-cellar-guard` | | 3.0 hp/rd | 5.0 hp/rd | 2 | 0/30 |
| defend | `enc-drowned` | | 3.8 hp/rd | 0.3 hp/rd | 8 | 30/30 |

**Two of the three encounters are unwinnable at level 1 under every policy tested — 0 wins in
180 attempts, median 2 rounds to death.** The third is won in 90 of 90.

## Where the numbers are wrong

### 1. `power_rating` does not predict lethality; attacker count does

The **highest**-rated encounter is the only winnable one:

| Encounter | Total power | `encounter_targets` band | Attackers | Result |
|---|---|---|---|---|
| `enc-quay-runners` | 12 | `danger_1_3` = [6, 12] — top of the *lowest* band | 2 | 0/90 |
| `enc-cellar-guard` | 18 | `danger_4_6` = [12, 24] | 2 | 0/90 |
| `enc-drowned` | 15 | `danger_4_6` = [12, 24] | 1 | 90/90 |

`balance.json` classifies `enc-quay-runners` as a low-danger encounter. It kills a fresh
protagonist every time. Power rating sums per-enemy strength and ignores that two enemies act
twice per round against a player who acts once.

### 2. Armour is a per-round pool, so the second attacker always lands unmitigated

Damage routes armour-first and writes back the depleted armour
(`engine/combat/effects.py:68`). Observed every round of every 2-enemy fight:

```
enemy-chain-runner_1 ... player-1 took 4 damage (2 absorbed by armour, 2 to HP). HP is now 8/10.
enemy-chain-runner_2 ... player-1 took 4 damage (0 absorbed by armour, 4 to HP). HP is now 4/10.
```

Armour absorbs from the first attacker and nothing thereafter. Nothing observed in 270 combats
restores it — and the protagonist starts at 2 of a maximum 5, so most of the stat is unused. This
is the mechanism behind finding 1: a second attacker is worth far more than its power rating.

### 3. Salt Ward is mechanically inert

`skill-salt-ward` authors `kind: buff, magnitude: 2, status_id: null`. The engine's BUFF branch
returns the target **unmodified** when there is no `status_id`
(`engine/combat/effects.py:184`) — it only emits a log line. Observed absorbed damage is
identical with and without the ward up.

It costs 2 mana and does nothing, so the `ward` policy is strictly worse than `strike`: it cut
player output to 0.5–1.9 hp/round and doubled `enc-drowned` from 8 rounds to 16. The registered
statuses are `guarded, bleed, poison, burn, regen, stun, frozen, exposed, focus`
(`engine/combat/statuses.py:136`). `skill-tide-pull` (the drowned thing's debuff) has the same
null `status_id` and is equally inert.

### 4. Enemies idle once mana runs out, so long fights are free

`enemy-drowned-thing` has 10 mana, +2 regen, and spends 3/round on Tide Pull. It ran dry and
logged `takes no action` for **90 idle rounds across 30 fights** — about 3 of every 8 rounds.
That is why a 30 HP, power-15 enemy deals 0.2 hp/round. Under the `ward` policy the fight
stretches to 16 rounds and the enemy idles 342 rounds across 30 fights.

### 5. XP thresholds are calibrated against encounters the player cannot reach

Thresholds are `{1:0, 2:10, 3:25, 4:45, 5:70}`. The single winnable encounter awards **15 XP**,
which clears level 2 (10) on the first win and lands 60% of the way to level 3 (25). The two
encounters that award nothing are the ones a level-1 character meets first.

## Proposed changes — not applied

Each needs its own slice. Ordered by evidence strength.

| # | Proposal | Evidence |
|---|---|---|
| 1 | Serve area travel (a route, or make connected areas resolvable candidates and apply the `travel` effect). Without it no encounter is reachable and no balance change is observable in play. | `422` from `/combat/start`; `_build_candidates` omits areas |
| 2 | Refresh armour to its maximum at the start of each round (the stat already carries a `maximum`), or make it reduce per hit rather than deplete. Also review why the protagonist starts at 2 of 5. | Finding 2: 2 absorbed then 0, every round of 180 fights |
| 3 | Either give `skill-salt-ward` and `skill-tide-pull` a registered `status_id`, or make pack validation **reject** a buff/debuff with a null `status_id` instead of silently no-oping. Prefer the validation fix — it catches every future authoring slip. | Finding 3; identical absorption with and without the ward |
| 4 | Re-derive `encounter_targets` from attacker count, not summed power — e.g. multiply total power by attackers, or cap attackers per danger band. Concretely: `enc-quay-runners` at 12 power must not sit in the same band as a single 12-power enemy. | Finding 1: power 12 → 0/90; power 15 → 90/90 |
| 5 | Raise protagonist level-1 HP from 10, and/or lower `skill-brine-lash` base damage from 4. Two attackers deal 5.0 hp/round against 10 HP: a 2-round time-to-death. A 3–4 round floor implies roughly 15–20 HP at current damage. | Damage table above |
| 6 | Give enemies a mana floor, a 0-cost basic attack, or higher regen so they do not idle. | Finding 4: 90 idle rounds / 30 fights |
| 7 | Revisit XP only after 1–5 land. 15 XP/win against a 10-XP level-2 threshold is untestable while 2 of 3 encounters are unwinnable. | Finding 5 |

Proposals 2 and 3 are engine changes and would need an ADR; 4, 5, 6 and 7 are campaign/balance
data; 1 is a new feature slice.

## Reproducing

The driver is not committed — it is a scratch harness, and PLAY-07's deliverable is this
document plus the log. To regenerate: build `CombatUseCases` as `api/routes/combat.py:46` does,
with `SecureRandomSource`, place the protagonist in the encounter's area, and loop
`execute_skill` / `execute_defend` until `state.combat is None`. Player HP must be read from the
combat **logs**, not from `state.player.hp` after the fight — HP is restored when combat
resolves, which silently reports 0 damage taken.
