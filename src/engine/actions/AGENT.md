# Exploration Action Agent Rules

- Follow validation order in `docs/game-design/freeform-actions.md` exactly.
- Resolve ordinals/mentions only from supplied candidates; never by invented ID/name.
- Create effects only from authored allowlists and engine rules.
- Rejections consume no RNG or resources. Check DC/stakes exist before a roll.
- Test standard, creative, partial, invalid, ambiguous, protected, stale, and replay paths.
