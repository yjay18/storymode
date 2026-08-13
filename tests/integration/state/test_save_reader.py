"""Integration tests for save reader."""

import json
from pathlib import Path

import pytest

from campaign.storage.save_reader import SaveReader
from domain.models.common import EntityId
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta
from engine.state.errors import CampaignMismatchError, CorruptSaveError, UnsafePathError


@pytest.fixture
def valid_save_dir(temp_campaign_root: Path) -> Path:
    """Create a minimal valid save directory."""
    save_dir = temp_campaign_root / "campaigns" / "camp-1" / "saves" / "save-1"
    save_dir.mkdir(parents=True)
    
    # Read the generated minimal valid state
    state_path = Path("tests/fixtures/save_minimal_valid/state.json")
    meta_path = Path("tests/fixtures/save_minimal_valid/save_meta.json")
    journal_path = Path("tests/fixtures/save_minimal_valid/journal.jsonl")
    
    if not state_path.exists():
        pytest.skip("Minimal save fixture not generated yet")
        
    (save_dir / "state.json").write_text(state_path.read_text())
    (save_dir / "save_meta.json").write_text(meta_path.read_text())
    
    # Add one committed and one prepared journal event
    # Revision of fixture is 0, so revision 0 is committed, revision 1 is prepared
    event_0 = json.loads(journal_path.read_text().splitlines()[0])
    event_1 = event_0.copy()
    event_1["revision"] = 11
    
    with (save_dir / "journal.jsonl").open("w") as f:
        f.write(json.dumps(event_0) + "\n")
        f.write(json.dumps(event_1) + "\n")
        
    return save_dir


def test_save_reader_valid_round_trip(valid_save_dir: Path, temp_campaign_root: Path) -> None:
    reader = SaveReader(temp_campaign_root)
    result = reader.load_save(EntityId("camp-1"), EntityId("save-1"))
    
    assert isinstance(result.state, RuntimeState)
    assert isinstance(result.meta, SaveMeta)
    assert result.memory is None
    
    assert len(result.journal_events) == 1
    assert result.journal_events[0].revision == 0
    
    assert len(result.prepared_journal_events) == 1
    assert result.prepared_journal_events[0].revision == 11


def test_save_reader_unsafe_paths(temp_campaign_root: Path) -> None:
    reader = SaveReader(temp_campaign_root)
    with pytest.raises(UnsafePathError):
        reader.load_save(EntityId("../camp-1"), EntityId("save-1"))


def test_save_reader_corrupt_json(valid_save_dir: Path, temp_campaign_root: Path) -> None:
    (valid_save_dir / "state.json").write_text("{corrupt: json")
    reader = SaveReader(temp_campaign_root)
    with pytest.raises(CorruptSaveError, match="Invalid JSON"):
        reader.load_save(EntityId("camp-1"), EntityId("save-1"))


def test_save_reader_duplicate_keys(valid_save_dir: Path, temp_campaign_root: Path) -> None:
    (valid_save_dir / "save_meta.json").write_text('{"campaign_id": "camp-1", "campaign_id": "camp-1"}')
    reader = SaveReader(temp_campaign_root)
    with pytest.raises(CorruptSaveError, match="Duplicate key"):
        reader.load_save(EntityId("camp-1"), EntityId("save-1"))


def test_save_reader_wrong_fingerprint(valid_save_dir: Path, temp_campaign_root: Path) -> None:
    reader = SaveReader(temp_campaign_root)
    with pytest.raises(CampaignMismatchError, match="mismatch"):
        reader.load_save(EntityId("camp-1"), EntityId("save-1"), expected_fingerprint="wrong-fp")


def test_save_reader_missing_derived(valid_save_dir: Path, temp_campaign_root: Path) -> None:
    # Remove save_meta.json
    (valid_save_dir / "save_meta.json").unlink()
    reader = SaveReader(temp_campaign_root)
    result = reader.load_save(EntityId("camp-1"), EntityId("save-1"))
    
    assert result.meta is None
