# API Agent Rules

- Keep route functions thin: parse DTO, call one use case, map typed result/error.
- Enforce body/string/list limits before expensive work and return consistent safe
  error envelopes/correlation IDs.
- Map status codes exactly as `component-boundaries.md`; never leak traceback, local
  absolute path, prompt, source text, or raw model response.
- Test handlers through dependency overrides; no real disk, RNG, or Ollama in route
  tests. Add OpenAPI/contract snapshots for public endpoints.
- Default bind and CORS stay loopback/same-origin. Any change requires threat-model ADR.
