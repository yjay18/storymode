# Threat Model: Local-Only Application

## Scope and assets

Local-only is a deployment property, not a trust guarantee. Protect campaign/save
integrity, source documents imported by the player, model prompts/responses, local
filesystem paths, and the guarantee that no data leaves the machine.

Threat inputs include free text, imported text/transcripts, imported campaign JSON,
malformed saves, LLM output, image bytes, HTTP requests from other local pages, and
symlinks inside the data directory. The local OS account and installed Ollama are
trusted to the same degree as other user-installed software; model output is not.

## Required controls

- Bind API and dev UI to `127.0.0.1` by default. Reject non-loopback host settings
  unless a future documented opt-in exists.
- Use an exact development-origin allowlist; do not use wildcard CORS with mutation
  routes. Production same-origin serving needs no permissive CORS.
- Never expose a route that accepts arbitrary filesystem paths. Resolve campaign,
  save, and asset IDs under a configured root; reject `..`, absolute paths, NULs,
  symlink escapes, and invalid ID syntax.
- Apply explicit byte/count/depth limits before parsing text, JSON, JSONL, model
  output, source imports, and image responses.
- Treat imported content as data. Never evaluate Python/JavaScript, execute macros,
  render raw HTML, or interpolate it into shell commands.
- Use `httpx` directly for Ollama with loopback URL validation, timeouts, response
  size limits, and no redirects to non-loopback hosts.
- Never invoke Ollama through `shell=True`. If a setup script calls its CLI, use an
  argument list and show the exact model operation to the user.
- Escape all narrative and imported text in the UI. Do not render unsanitized HTML.
- Generated asset writes use engine-selected filenames and MIME/signature checks;
  ignore filenames supplied by a model.
- Use restrictive create permissions where supported. Do not store cloud secrets;
  redact prompt bodies and source text from normal logs.
- Preserve corrupt files and produce diagnostics; never destructively "repair" an
  only save without a snapshot.

## Prompt injection containment

Source material and campaign prose may contain instructions. Mark them as quoted
data inside prompts and instruct each model role to follow only the surrounding
contract. More importantly, never grant the model tools, filesystem access, or state
mutation. Validate every returned reference and allowed outcome independently, so a
successful injection can at worst yield rejected text.

## Availability and resource controls

Set request timeouts and cancellation. Serialize or bound concurrent model/image
jobs. Cap active opportunity count, context length, generation tokens, campaign file
counts, and image dimensions. An Ollama outage must not corrupt state. A narrator
timeout after commit uses deterministic fallback text.

## Verification cases

Security tests must cover path traversal, absolute paths, symlink escape where the
platform supports it, oversized inputs, unknown JSON fields, malicious HTML, prompt
instructions embedded in source text, non-loopback Ollama URLs, redirects, timeouts,
and malformed/oversized model responses.

## Explicit non-goals

v1 does not defend against a malicious OS administrator, compromised Python/npm
dependency, or an attacker who can freely modify the user's process memory. Supply
chain controls are lockfiles, reviewed dependencies, and documented updates—not a
claim of complete sandboxing.
