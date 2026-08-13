# LLM Orchestration Agent Rules

- Preserve request/version/factual scope across repair and obey exact attempt limit.
- Do not repair timeouts/unavailability by contacting another provider.
- Return typed failures without raw prompt/response leakage.
- Never call a save repository or apply an effect; model results go to the engine.
- Test first-pass, repair, exhaustion, timeout/cancel, logging redaction, and fallback.
