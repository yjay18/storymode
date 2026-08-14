"""Integration tests for save migration script."""

import subprocess
import sys
from pathlib import Path


def test_migrate_save_noop(tmp_path: Path) -> None:
    save_dir = tmp_path / "save_1"
    save_dir.mkdir()
    (save_dir / "state.json").write_text('{"schema_version": 1}')

    result = subprocess.run(
        [sys.executable, "scripts/migrate_save.py", str(save_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert (
        "already at target version 1" in result.stdout
        or "already at target version 1" in result.stderr
    )


def test_migrate_save_newer_fails(tmp_path: Path) -> None:
    save_dir = tmp_path / "save_2"
    save_dir.mkdir()
    (save_dir / "state.json").write_text('{"schema_version": 999}')

    result = subprocess.run(
        [sys.executable, "scripts/migrate_save.py", str(save_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "is newer than target" in result.stderr or "is newer than target" in result.stdout
