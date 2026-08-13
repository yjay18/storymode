"""Save writer implementation."""

import os
from pathlib import Path
from typing import Any

from domain.models.audit import JournalEvent, RollRecord
from domain.models.common import EntityId
from domain.models.narrative_memory import NarrativeMemory
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta
from engine.state.errors import SaveError, UnsafePathError


class SaveWriter:
    """Writes state and audit logs safely to the filesystem."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()
        
    def _resolve_save_dir(self, campaign_id: EntityId, save_id: EntityId) -> Path:
        save_dir = self.root_dir / "campaigns" / campaign_id / "saves" / save_id
        resolved = save_dir.resolve()
        if not resolved.is_relative_to(self.root_dir / "campaigns"):
            raise UnsafePathError(f"Save path escapes root: {save_dir}")
        return resolved

    def _atomic_write_json(self, path: Path, model: Any) -> None:
        """Write a Pydantic model to a JSON file atomically."""
        tmp_path = path.with_suffix(".json.tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                f.write(model.model_dump_json(indent=2))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise SaveError(f"Failed to write {path}: {e}") from e

    def _append_jsonl(self, path: Path, models: list[Any]) -> None:
        """Append Pydantic models to a JSONL file."""
        if not models:
            return
            
        try:
            with path.open("a", encoding="utf-8") as f:
                for model in models:
                    f.write(model.model_dump_json() + "\n")
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            raise SaveError(f"Failed to append to {path}: {e}") from e

    def write_state(self, state: RuntimeState, meta: SaveMeta, memory: NarrativeMemory | None) -> None:
        """Write authoritative state, meta, and optional memory atomically."""
        save_dir = self._resolve_save_dir(state.campaign_id, state.save_id)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        self._atomic_write_json(save_dir / "state.json", state)
        self._atomic_write_json(save_dir / "save_meta.json", meta)
        
        if memory is not None:
            self._atomic_write_json(save_dir / "narrative_memory.json", memory)

    def append_journal(self, campaign_id: EntityId, save_id: EntityId, events: list[JournalEvent]) -> None:
        """Append events to the journal log."""
        save_dir = self._resolve_save_dir(campaign_id, save_id)
        save_dir.mkdir(parents=True, exist_ok=True)
        self._append_jsonl(save_dir / "journal.jsonl", events)

    def append_rolls(self, campaign_id: EntityId, save_id: EntityId, rolls: list[RollRecord]) -> None:
        """Append rolls to the roll log."""
        save_dir = self._resolve_save_dir(campaign_id, save_id)
        save_dir.mkdir(parents=True, exist_ok=True)
        self._append_jsonl(save_dir / "roll_log.jsonl", rolls)

    def flush_prepared_rows(
        self,
        campaign_id: EntityId,
        save_id: EntityId,
        journal_events: list[JournalEvent],
        roll_records: list[RollRecord],
    ) -> None:
        """Flush prepared journal events and roll records to their respective logs."""
        if journal_events:
            self.append_journal(campaign_id, save_id, journal_events)
        if roll_records:
            self.append_rolls(campaign_id, save_id, roll_records)
