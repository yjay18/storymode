# Documentation Context

`docs/` contains canonical cross-cutting specifications. Code comments explain how;
these documents explain contracts, invariants, ownership, and why decisions exist.

Architecture documents govern dependency direction and persistence. Game-design
documents govern player-visible mechanics. Schema documents govern serialized and
LLM-facing shapes. Prompt documents govern model roles. UX documents govern screen
behavior. Research documents record evidence without becoming runtime dependencies.

When a code change contradicts a canonical document, do not quietly update only the
code. Either conform the code or record an ADR and update every affected document.
