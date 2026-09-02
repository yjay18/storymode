# LLM Agent Rules

- Read prompt policy and exact LLM contract before edits.
- Validate Ollama base URL as loopback; configure explicit connect/read/total timeouts,
  response limits, no non-loopback redirects, and cancellation.
- Parse exactly one JSON object with duplicate-key detection and `extra="forbid"`.
- Bound context before transport; never silently drop required facts.
- Retry formatting at most as documented and never expand factual scope.
- Do not log raw prompts, source text, player text, or full responses by default.
- Tests use a fake HTTP transport/model; normal tests never require Ollama or network.
