# Integration Test Agent Rules

- Never write repository campaign/save fixtures; copy into Pytest temp directories.
- Inject failures at I/O/commit steps and assert old-or-new valid state plus preserved source.
- HTTP tests use ASGI/fake HTTP transports, not bound sockets or installed Ollama.
- Assert persisted reload/audit data, not only response status.
