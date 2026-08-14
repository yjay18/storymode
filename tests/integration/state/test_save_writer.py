"""Integration tests for save writer."""

from pathlib import Path
from unittest.mock import patch

import pytest

from campaign.storage.save_writer import SaveWriter
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta
from engine.state.errors import SaveError


@pytest.fixture
def mock_state() -> RuntimeState:
    path = Path("tests/fixtures/save_minimal_valid/state.json")
    if not path.exists():
        pytest.skip("Fixture not generated yet")
    return RuntimeState.model_validate_json(path.read_text())


@pytest.fixture
def mock_meta() -> SaveMeta:
    path = Path("tests/fixtures/save_minimal_valid/save_meta.json")
    if not path.exists():
        pytest.skip("Fixture not generated yet")
    return SaveMeta.model_validate_json(path.read_text())


def test_save_writer_write_state(
    temp_campaign_root: Path, mock_state: RuntimeState, mock_meta: SaveMeta
) -> None:
    writer = SaveWriter(temp_campaign_root)
    writer.write_state(mock_state, mock_meta, None)

    save_dir = (
        temp_campaign_root / "campaigns" / mock_state.campaign_id / "saves" / mock_state.save_id
    )
    assert (save_dir / "state.json").exists()
    assert (save_dir / "save_meta.json").exists()
    assert not (save_dir / "narrative_memory.json").exists()

    # Verify content
    state = RuntimeState.model_validate_json((save_dir / "state.json").read_text())
    assert state.revision == mock_state.revision


def test_save_writer_atomic_replace_failure(
    temp_campaign_root: Path, mock_state: RuntimeState, mock_meta: SaveMeta
) -> None:
    writer = SaveWriter(temp_campaign_root)
    save_dir = (
        temp_campaign_root / "campaigns" / mock_state.campaign_id / "saves" / mock_state.save_id
    )
    save_dir.mkdir(parents=True)

    state_file = save_dir / "state.json"
    state_file.write_text("old content")

    with (
        patch("os.replace", side_effect=OSError("Disk full")),
        pytest.raises(SaveError, match="Failed to write"),
    ):
        writer.write_state(mock_state, mock_meta, None)

    # The original file should be unmodified
    assert state_file.read_text() == "old content"
    # The temp file should be cleaned up
    assert not (save_dir / "state.json.tmp").exists()


def test_save_writer_flush_prepared_rows(
    temp_campaign_root: Path, mock_state: RuntimeState
) -> None:
    writer = SaveWriter(temp_campaign_root)

    # Just need some events and rolls
    journal_path = Path("tests/fixtures/save_minimal_valid/journal.jsonl")
    if not journal_path.exists():
        pytest.skip("Fixture not generated yet")

    from domain.models.audit import JournalEvent

    event = JournalEvent.model_validate_json(journal_path.read_text().splitlines()[0])

    writer.flush_prepared_rows(mock_state.campaign_id, mock_state.save_id, [event], [])

    save_dir = (
        temp_campaign_root / "campaigns" / mock_state.campaign_id / "saves" / mock_state.save_id
    )
    assert (save_dir / "journal.jsonl").exists()
    assert len((save_dir / "journal.jsonl").read_text().splitlines()) == 1
