# Prompt Agent Rules

- Read `docs/schemas/llm-contracts.md` before editing a prompt.
- Change one role/prompt version at a time and update contract/golden cases.
- Delimit untrusted player/source/campaign text as data.
- Do not put secret engine rules, state mutation, random selection, final DCs, or
  fallback authority into model instructions.
- Keep context selection code outside templates and enforce byte/token budgets.
- Test malformed, injection, fabricated-reference, and forbidden-fact outputs.
- Never compensate for weak deterministic validation with stronger wording alone.
