"""Integration tests for save recovery."""

import json
from pathlib import Path

import pytest

from campaign.storage.recovery import RecoveryManager
from domain.models.common import EntityId


@pytest.fixture
def valid_save_dir(temp_campaign_root: Path) -> Path:
    """Create a minimal valid save directory."""
    save_dir = temp_campaign_root / "campaigns" / "camp-1" / "saves" / "save-1"
    save_dir.mkdir(parents=True)

    state_path = Path("tests/fixtures/save_minimal_valid/state.json")
    meta_path = Path("tests/fixtures/save_minimal_valid/save_meta.json")
    journal_path = Path("tests/fixtures/save_minimal_valid/journal.jsonl")

    if not state_path.exists():
        pytest.skip("Minimal save fixture not generated yet")

    (save_dir / "state.json").write_text(state_path.read_text())
    (save_dir / "save_meta.json").write_text(meta_path.read_text())
    (save_dir / "journal.jsonl").write_text(journal_path.read_text())

    return save_dir


def test_rotate_snapshots(valid_save_dir: Path, temp_campaign_root: Path) -> None:
    recovery = RecoveryManager(temp_campaign_root)

    # Initial rotation
    recovery.rotate_snapshots(EntityId("camp-1"), EntityId("save-1"))
    assert (valid_save_dir / "state.1.json").exists()
    assert (valid_save_dir / "save_meta.1.json").exists()
    assert (valid_save_dir / "state.json").exists()  # Original still exists

    # Change original to verify rotation pushes it
    (valid_save_dir / "state.json").write_text("new content")
    recovery.rotate_snapshots(EntityId("camp-1"), EntityId("save-1"))

    assert (valid_save_dir / "state.2.json").exists()
    assert (valid_save_dir / "state.1.json").read_text() == "new content"


def test_list_recoverable_snapshots(valid_save_dir: Path, temp_campaign_root: Path) -> None:
    recovery = RecoveryManager(temp_campaign_root)
    recovery.rotate_snapshots(EntityId("camp-1"), EntityId("save-1"))

    snapshots = recovery.list_recoverable_snapshots(EntityId("camp-1"), EntityId("save-1"))
    assert snapshots == [1]


def test_rebuild_derived_metadata(valid_save_dir: Path, temp_campaign_root: Path) -> None:
    recovery = RecoveryManager(temp_campaign_root)

    # Delete meta and verify rebuild
    (valid_save_dir / "save_meta.json").unlink()
    success = recovery.rebuild_derived_metadata(EntityId("camp-1"), EntityId("save-1"))

    assert success
    assert (valid_save_dir / "save_meta.json").exists()

    # Check rebuilt content
    meta = json.loads((valid_save_dir / "save_meta.json").read_text())
    assert meta["recovery_status"] == "rebuilt"
    assert meta["slot_kind"] == "autosave"
