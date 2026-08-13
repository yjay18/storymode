# Engine Context

`engine` is the sole deterministic gameplay transition authority. It coordinates pure
domain rules through injected ports and returns a candidate transition; a repository
commits it before narration.

- `dice/`: random-source protocol, secure adapter boundary, roll arithmetic/records.
- `actions/`: proposal resolution, world validation, checks, outcomes.
- `combat/`: encounter/turn/action state machine.
- `progression/`: XP, upgrade, loadout, fusion transitions.
- `plot/`: milestone/opportunity/clock transitions.
- `state/`: commands, transitions, repository protocol, atomic save orchestration.
- `validation/`: cross-file/reference/graph/balance diagnostics.

Every mutation consumes expected revision and command ID. Invalid transitions consume
no resources or randomness and produce no partial state.
