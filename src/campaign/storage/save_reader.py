"""Read-only save loading."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from domain.models.audit import JournalEvent, RollRecord
from domain.models.common import EntityId
from domain.models.narrative_memory import NarrativeMemory
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta
from engine.state.errors import CampaignMismatchError, CorruptSaveError, UnsafePathError
from engine.state.ports import SaveLoadResult


def _dict_raise_on_duplicates(ordered_pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    d: dict[str, Any] = {}
    for k, v in ordered_pairs:
        if k in d:
            raise CorruptSaveError(f"Duplicate key: {k}")
        d[k] = v
    return d


class SaveReader:
    """Read-only save loading implementation."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()

    def _resolve_save_dir(self, campaign_id: EntityId, save_id: EntityId) -> Path:
        save_dir = self.root_dir / "campaigns" / campaign_id / "saves" / save_id
        resolved = save_dir.resolve()

        if not resolved.is_relative_to(self.root_dir / "campaigns"):
            raise UnsafePathError(f"Save path escapes root: {save_dir}")

        return resolved

    def load_save(
        self,
        campaign_id: EntityId,
        save_id: EntityId,
        expected_fingerprint: str | None = None,
    ) -> SaveLoadResult:
        """Load a save and verify its campaign identity."""
        save_dir = self._resolve_save_dir(campaign_id, save_id)

        if not save_dir.exists():
            raise CorruptSaveError(f"Save directory not found: {save_dir}")

        state = self._read_json_model(save_dir / "state.json", RuntimeState)

        meta = None
        meta_path = save_dir / "save_meta.json"
        if meta_path.exists():
            meta = self._read_json_model(meta_path, SaveMeta)

        # Verify campaign identity
        if state.campaign_id != campaign_id:
            raise CampaignMismatchError(
                f"State campaign_id {state.campaign_id} != expected {campaign_id}"
            )
        if meta is not None and meta.campaign_id != campaign_id:
            raise CampaignMismatchError(
                f"Meta campaign_id {meta.campaign_id} != expected {campaign_id}"
            )

        if expected_fingerprint is not None and state.campaign_fingerprint != expected_fingerprint:
            raise CampaignMismatchError("State fingerprint mismatch")

        # Memory is optional/derived
        memory = None
        mem_path = save_dir / "narrative_memory.json"
        if mem_path.exists():
            memory = self._read_json_model(mem_path, NarrativeMemory)
            if memory.campaign_id != campaign_id:
                raise CampaignMismatchError("Memory campaign_id mismatch")

        journal_events, prepared_journals = self._read_jsonl(
            save_dir / "journal.jsonl", JournalEvent, state.revision
        )
        roll_records, prepared_rolls = self._read_jsonl(
            save_dir / "roll_log.jsonl", RollRecord, state.revision
        )

        return SaveLoadResult(
            state=state,
            meta=meta,
            memory=memory,
            journal_events=journal_events,
            roll_records=roll_records,
            prepared_journal_events=prepared_journals,
            prepared_roll_records=prepared_rolls,
        )

    def _read_json_model(self, path: Path, model_cls: type[Any]) -> Any:
        if not path.is_file():
            raise CorruptSaveError(f"File missing or not a file: {path}")

        # Byte limit: 10MB
        if path.stat().st_size > 10 * 1024 * 1024:
            raise CorruptSaveError(f"File too large: {path}")

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content, object_pairs_hook=_dict_raise_on_duplicates)
            return model_cls.model_validate_json(json.dumps(data))
        except json.JSONDecodeError as e:
            raise CorruptSaveError(f"Invalid JSON in {path}: {e}") from e
        except ValidationError as e:
            raise CorruptSaveError(f"Validation failed for {path}: {e}") from e

    def _read_jsonl(
        self, path: Path, model_cls: type[Any], state_revision: int
    ) -> tuple[list[Any], list[Any]]:
        if not path.is_file():
            return [], []

        committed = []
        prepared = []

        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if len(line) > 1024 * 1024:
                        raise CorruptSaveError(f"Line too long in {path}")

                    data = json.loads(line, object_pairs_hook=_dict_raise_on_duplicates)
                    record = model_cls.model_validate_json(json.dumps(data))

                    if record.revision <= state_revision:
                        committed.append(record)
                    else:
                        prepared.append(record)
        except json.JSONDecodeError as e:
            raise CorruptSaveError(f"Invalid JSON line in {path}: {e}") from e
        except ValidationError as e:
            raise CorruptSaveError(f"Validation failed for {path}: {e}") from e

        return committed, prepared
