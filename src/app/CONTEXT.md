# Application Context

`app` is the composition root. Planned files are `main.py` (application factory),
`config.py` (validated environment settings), and `dependencies.py` (singleton/scoped
wiring). It may import concrete adapters and engine use cases so other modules do not.

Settings use the `STORYMODE_` prefix, `.env` for local convenience, and safe defaults:
loopback host, port 8000, `./campaigns`, loopback Ollama URL, explicit model names, and
INFO logging. Startup creates no campaign and downloads no model. Lifespan closes
HTTP clients and background asset queues cleanly.
