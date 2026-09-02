"""First run: verify local prerequisites, then start the API server and the web UI.

Checks that Ollama is reachable on its loopback URL and that the configured text model
is installed (pulling it when the ``ollama`` CLI is available), makes sure the campaign
library has at least one published pack, then launches uvicorn and the Vite dev server
until Ctrl-C. Everything stays on this machine.
"""

from __future__ import annotations

import json
import shutil
import signal
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from app.config import Settings
from llm.health import normalize_model_name

_REPO = Path(__file__).resolve().parent.parent
_UI = _REPO / "src" / "ui"
_DEFAULT_PREMISE = (
    "A drowned port city where tide-priests sell forgiveness by the ounce and a disgraced "
    "customs clerk must find who forged the Salt Ledger before the spring flood."
)


def _fail(message: str) -> None:
    print(f"✗ {message}", file=sys.stderr)
    sys.exit(1)


def check_ollama(settings: Settings) -> None:
    """Confirm Ollama answers on loopback and has the configured model."""
    try:
        with urllib.request.urlopen(f"{settings.ollama_url}/api/tags", timeout=5) as resp:
            models = [m["name"] for m in json.load(resp)["models"]]
    except (urllib.error.URLError, OSError, KeyError, ValueError) as e:
        _fail(f"Ollama not reachable at {settings.ollama_url} ({e}). Start it with `ollama serve`.")
    print(f"✓ Ollama reachable at {settings.ollama_url}")

    wanted = normalize_model_name(settings.model_text)
    if wanted in {normalize_model_name(m) for m in models}:
        print(f"✓ model {settings.model_text} installed")
        return
    if shutil.which("ollama") is None:
        _fail(f"model {settings.model_text} missing and no `ollama` CLI; run `ollama pull`.")
    print(f"… pulling {settings.model_text} (one-time download)")
    if subprocess.run(["ollama", "pull", settings.model_text], check=False).returncode != 0:
        _fail(
            f"could not pull {settings.model_text}; set STORYMODE_MODEL_TEXT to an installed model"
        )


def ensure_campaign(settings: Settings) -> None:
    """Generate a campaign with the local model if the library is empty."""
    root = Path(settings.campaigns_dir).resolve()
    if any(p.is_file() for p in root.glob("*/campaign.json")):
        print(f"✓ campaign library at {root}")
        return
    print("… campaign library is empty; generating one with the local model (several minutes)")
    cmd = [sys.executable, str(_REPO / "scripts" / "generate_campaign.py"), _DEFAULT_PREMISE]
    if subprocess.run(cmd, check=False).returncode != 0:
        _fail("campaign generation failed; see output above")


def ensure_ui_deps() -> None:
    if shutil.which("npm") is None:
        _fail("npm not found; install Node.js 22+")
    if not (_UI / "node_modules").is_dir():
        print("… installing UI dependencies")
        subprocess.run(["npm", "ci"], cwd=_UI, check=True)
    print("✓ UI dependencies installed")


def serve(settings: Settings) -> None:
    """Run the API and the Vite dev server until interrupted."""
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            settings.host,
            "--port",
            str(settings.port),
        ],
        cwd=_REPO,
    )
    ui = subprocess.Popen(["npm", "run", "dev"], cwd=_UI)
    print(f"\n→ API  http://{settings.host}:{settings.port}/docs")
    print("→ Play http://localhost:5173  (Ctrl-C stops both)\n")
    try:
        signal.signal(signal.SIGINT, lambda *_: None)
        ui.wait()
    finally:
        for proc in (ui, api):
            proc.terminate()
        for proc in (ui, api):
            proc.wait(timeout=10)


def main() -> None:
    settings = Settings()
    check_ollama(settings)
    ensure_campaign(settings)
    ensure_ui_deps()
    serve(settings)


if __name__ == "__main__":
    main()
