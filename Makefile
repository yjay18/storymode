.PHONY: setup check check-backend check-ui play generate live schema

# Install backend and UI dependencies.
setup:
	uv sync --all-groups
	npm --prefix src/ui ci

# Every CI gate, backend then UI.
check: check-backend check-ui

check-backend:
	uv run python scripts/check_scaffold.py
	uv run python scripts/generate_schemas.py --check
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src tests scripts
	uv run pytest tests/ -q
	uv run python scripts/run_smoke_test.py

check-ui:
	npm --prefix src/ui run lint
	npm --prefix src/ui run typecheck
	npm --prefix src/ui run test
	npm --prefix src/ui run build

# Verify Ollama and the configured model, then start the API and the web UI.
play:
	uv run python scripts/first_run.py

# Generate and publish a campaign headlessly: make generate PREMISE="..."
# Resume a stalled draft: make generate DRAFT=<draft-id>
generate:
ifdef DRAFT
	uv run python scripts/generate_campaign.py --draft "$(DRAFT)"
else
	uv run python scripts/generate_campaign.py "$(PREMISE)"
endif

# Opt-in tests against the real local model.
live:
	STORYMODE_LIVE_OLLAMA=1 uv run pytest tests/live -q

schema:
	uv run scripts/generate_schemas.py
