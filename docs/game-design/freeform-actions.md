# Freeform Exploration Actions

## Agency boundary

The player supplies intent. Existing campaign design plus committed state supplies
facts. “Use my crowbar on the crate” can be valid if both IDs are available. “My
assassin friend arrives” cannot create that friend. Unsupported assertions may become
a search, question, or attempt only when that reinterpretation preserves the user's
core intent and has valid targets.

## Proposal contract

The interpreter returns a proposal with status (`valid`, `valid_creative`, `partial`,
or `invalid`), operation tag, verb, entity mentions, capability/item mentions,
intended effect, semantic challenge label, uncertainty reason, stakes, and a concise
in-world redirect when needed. Mentions are strings from input, not trusted IDs.

Operation tags such as investigate, alter_environment, use_item, persuade, deceive,
avoid_detection, travel, and attack are internal routing tags. Never show them as a
required player menu.

## Deterministic validation order

1. Reject empty/oversized input or active combat.
2. Parse strict proposal; reject unknown fields/status/tags.
3. Resolve mentions only against the bounded candidate set supplied to the model.
4. Reject unresolved ambiguity; do not guess between equal candidates.
5. Validate entity existence, visibility/knowledge, co-location/reachability, life and
   availability state, ownership/quantity, capabilities, and relationship access.
6. Validate world laws, current milestone protections, opportunity conditions, and
   candidate outcome allowlist.
7. Decide whether no roll, a check, or rejection applies.
8. Build effects from engine rules; ignore any proposed mutation or number.

Creative actions combine capability tags and object state predicates. They do not
receive a special numeric bonus merely for creative wording; applicable environment,
item, preparation, or knowledge modifiers must be defined and visible.

## Status handling

- `valid`: proposal matches existing entities and a standard rule route.
- `valid_creative`: a non-standard combination matches existing capability and object
  predicates and an allowed effect route.
- `partial`: a claimed detail is unsupported, but a bounded search/attempt/question is
  valid. The player is shown the reinterpretation before a consequential roll.
- `invalid`: required facts/entities/capabilities are absent or the intent violates a
  protected rule. Return an in-world redirect plus a stable error code.

The engine may downgrade a proposal status after validation. It may never upgrade an
invalid factual assertion solely because the model labeled it valid.

## Pending checks and consent

A meaningful check is persisted as `pending_check` before randomness. The UI shows
reason, formula components, final DC, stakes, and available luck. The player confirms
or cancels. Cancel clears the pending check in a normal revision and consumes no die.
Exactly one unresolved pending check may exist per save in v1.

## Narration facts

After commit, narration input contains original intent, resolved operation, involved
IDs with display data, roll display, exact state effects, discoveries, and allowed
presentation hints. It excludes hidden facts not revealed by the result. Narration
cannot add dialogue promises, item transfers, deaths, locations, relationships, or
future events unless those are confirmed in the factual outcome.
