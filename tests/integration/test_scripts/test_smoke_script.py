"""Integration tests for the run_smoke_test.py script (SCRIPT-02).

Tests:
  - subprocess success: script exits 0 and prints expected PASS lines.
  - injected failure: --fail flag causes the script to exit 1.
  - the script never modifies the repo fixture (only tmp dirs).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Absolute path to the script under test.
# __file__ is tests/integration/scripts/test_smoke_script.py
# .parent x3 = repo root
_SCRIPT = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "run_smoke_test.py"


def test_smoke_script_success() -> None:
    """Smoke script exits 0 and prints PASS for every step."""
    result = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # Verify key step markers are present in output
    assert "[PASS] Write initial save" in result.stdout
    assert "[PASS] Reload save" in result.stdout
    assert "[PASS] Submit direct inspect" in result.stdout
    assert "[PASS] Submit proposal with check" in result.stdout
    assert "[PASS] Resolve check" in result.stdout
    assert "[PASS] Final reload" in result.stdout
    assert "[PASS] FastAPI create save" in result.stdout
    assert "[PASS] FastAPI verify initial save" in result.stdout
    assert "[PASS] FastAPI submit direct action" in result.stdout
    assert "[PASS] FastAPI submit action with check" in result.stdout
    assert "[PASS] FastAPI resolve check" in result.stdout
    assert "[PASS] FastAPI final state reload" in result.stdout
    assert "all steps passed" in result.stdout
    # No failures
    assert "[FAIL]" not in result.stdout


def test_smoke_script_fail_mode() -> None:
    """--fail flag (scripted RNG exhaustion) causes exit 1 with FAIL step."""
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), "--fail"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, (
        f"Expected exit 1 with --fail, got {result.returncode}.\nstdout:\n{result.stdout}"
    )
    assert "[FAIL] Resolve check" in result.stdout


def test_smoke_script_does_not_modify_fixtures(tmp_path: Path) -> None:
    """Smoke script runs in its own temp dir and leaves the repo clean."""
    repo_root = _SCRIPT.parent.parent  # scripts/../ = repo root
    fixtures_dir = repo_root / "tests" / "fixtures"

    # Capture mtime snapshot of fixtures before running
    before = {p: p.stat().st_mtime for p in fixtures_dir.rglob("*") if p.is_file()}

    result = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Verify no fixture files changed
    after = {p: p.stat().st_mtime for p in fixtures_dir.rglob("*") if p.is_file()}
    changed = [str(p) for p in before if before[p] != after.get(p)]
    assert not changed, f"Fixture files modified by smoke script: {changed}"
