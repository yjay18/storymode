# LLM Context

`llm` is an optional, untrusted local adapter boundary. `ollama_client.py` will own
loopback HTTP transport. `contracts/` maps strict Pydantic responses, `prompts/` stores
versioned templates/few-shot data, `retrieval/` builds bounded context packets, and
`orchestration/` coordinates role request/parse/repair/fallback.

This module proposes interpretations/opportunities and produces display prose. It has
no save repository or mutation access and does not own dice, DCs, effects, IDs, or
canonical truth.
