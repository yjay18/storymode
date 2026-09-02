"""Guard against drift between the UI fetch client and the served API (PLAY-01).

Extracts every ``/api/v1/...`` path the TypeScript client calls and asserts each
one, with the HTTP method it uses, exists in the FastAPI OpenAPI schema. This fails
loudly if a client path is misspelled or a route is renamed/removed.
"""

import re
from pathlib import Path

from app.config import Settings
from app.main import create_app

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CLIENT_TS = _REPO_ROOT / "src" / "ui" / "src" / "api" / "client.ts"

# A quoted (") or backtick-quoted (`) call argument beginning with /api/v1/, captured
# up to the first ", `, or ? (query string). Requiring a preceding "(" skips paths that
# only appear in comments/prose.
_PATH_RE = re.compile(r'\(\s*[`"](/api/v1/[^`"?]*)')
_PARAM_RE = re.compile(r"\$\{[^}]+\}")
_OPENAPI_PARAM_RE = re.compile(r"\{[^}]+\}")


def _normalise(path: str) -> str:
    """Collapse both ``${x}`` (client) and ``{x}`` (openapi) params to ``{}``."""
    path = _PARAM_RE.sub("{}", path)
    return _OPENAPI_PARAM_RE.sub("{}", path)


def _method_for(text: str, path_start: int) -> str:
    """Infer the HTTP method for the client call containing the path at path_start."""
    call_start = text.rfind("this.", 0, path_start)
    head = text[call_start:path_start]
    if "this.post" in head:
        return "POST"
    # this.request(...) defaults to GET unless a method: "X" appears in its options.
    tail = text[path_start : path_start + 200]
    m = re.search(r'method:\s*"(\w+)"', tail)
    return m.group(1).upper() if m else "GET"


def _client_routes() -> set[tuple[str, str]]:
    text = _CLIENT_TS.read_text(encoding="utf-8")
    routes: set[tuple[str, str]] = set()
    for match in _PATH_RE.finditer(text):
        path = _normalise(match.group(1))
        method = _method_for(text, match.start())
        routes.add((path, method))
    return routes


def _served_routes() -> set[tuple[str, str]]:
    app = create_app(Settings(storymode_env="test"))
    paths = app.openapi()["paths"]
    return {(_normalise(path), method.upper()) for path, ops in paths.items() for method in ops}


def test_every_client_path_is_served() -> None:
    client = _client_routes()
    served = _served_routes()

    assert client, "no /api/v1 paths extracted from client.ts"

    missing = sorted(client - served)
    assert not missing, f"client.ts calls unserved routes: {missing}"


def test_matcher_rejects_a_misspelled_path() -> None:
    # Sanity-check the matcher: a deliberately wrong path is not in the served set.
    served = _served_routes()
    assert (_normalise("/api/v1/combat/vieww"), "GET") not in served
