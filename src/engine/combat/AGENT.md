# Combat Engine Agent Rules

- Read `docs/game-design/combat-rules.md` before every change.
- Validate full command before mana/effects/RNG; a failure returns original state.
- Apply armour before HP and exact integer rounding; base skills never make attack rolls.
- Draw only documented tie/effect/flee/loot dice and audit each.
- Test state after every turn, duplicate command, terminal cleanup, and soft defeat.
