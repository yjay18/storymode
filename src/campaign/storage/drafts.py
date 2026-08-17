"""Filesystem draft repository for campaign creation (BUILD-03).

Guarantees:
- Safe draft directory isolation from playable campaign packs.
- Strict path traversal defenses.
- Atomic writes with fsync and optimistic concurrency revision control.
- Prevents loading drafts through CampaignRepository.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from campaign.builder.models import DraftState
from domain.models.common import EntityId
from engine.state.errors import UnsafePathError


class DraftError(Exception):
    """Base exception for draft repository errors."""


class DraftNotFoundError(DraftError):
    """Raised when a requested draft ID cannot be found."""


class DraftRevisionConflictError(DraftError):
    """Raised when expected draft revision does not match current persisted revision."""


class DraftRepository:
    """Manages filesystem persistence and lifecycle of in-progress campaign drafts."""

    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.drafts_dir = self.root_dir / ".drafts"
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_draft_dir(self, draft_id: EntityId | str) -> Path:
        """Resolve and validate a draft directory, ensuring no directory traversal."""
        draft_str = str(draft_id).strip()
        if not draft_str or ".." in draft_str or "/" in draft_str or "\\" in draft_str:
            raise UnsafePathError(f"Invalid or unsafe draft ID: '{draft_id}'")

        target_dir = (self.drafts_dir / draft_str).resolve()
        if not target_dir.is_relative_to(self.drafts_dir):
            raise UnsafePathError(f"Draft path escapes drafts directory: '{draft_id}'")
        return target_dir

    def _atomic_write_json(self, path: Path, state: DraftState) -> None:
        """Atomically serialize a DraftState to JSON."""
        tmp_path = path.with_suffix(".json.tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                f.write(state.model_dump_json(indent=2))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise DraftError(f"Failed to write draft state to {path}: {e}") from e

    def save_draft(self, draft: DraftState, expected_revision: int | None = None) -> DraftState:
        """Save a draft state atomically with optimistic revision checks."""
        draft_dir = self._resolve_draft_dir(draft.draft_id)
        draft_dir.mkdir(parents=True, exist_ok=True)
        draft_file = draft_dir / "draft.json"

        if draft_file.exists():
            current = self.load_draft(draft.draft_id)
            if expected_revision is not None and current.revision != expected_revision:
                raise DraftRevisionConflictError(
                    f"Draft '{draft.draft_id}' revision conflict: "
                    f"expected {expected_revision}, got {current.revision}"
                )
            new_revision = current.revision + 1
        else:
            if expected_revision is not None and expected_revision != 1:
                raise DraftRevisionConflictError(
                    f"Draft '{draft.draft_id}' is new but expected_revision was {expected_revision}"
                )
            new_revision = 1

        persisted_state = draft.model_copy(update={"revision": new_revision})
        self._atomic_write_json(draft_file, persisted_state)
        return persisted_state

    def load_draft(self, draft_id: EntityId | str) -> DraftState:
        """Load a persisted draft state by ID."""
        draft_dir = self._resolve_draft_dir(draft_id)
        draft_file = draft_dir / "draft.json"

        if not draft_file.exists():
            raise DraftNotFoundError(f"Draft '{draft_id}' does not exist")

        try:
            raw_text = draft_file.read_text(encoding="utf-8")
            data = json.loads(raw_text)
            return DraftState.model_validate(data)
        except Exception as e:
            raise DraftError(f"Failed to load draft '{draft_id}': {e}") from e

    def list_drafts(self) -> list[DraftState]:
        """List all valid persisted campaign drafts."""
        drafts: list[DraftState] = []
        if not self.drafts_dir.exists():
            return drafts

        for entry in sorted(self.drafts_dir.iterdir()):
            if entry.is_dir():
                draft_file = entry / "draft.json"
                if draft_file.exists():
                    try:
                        drafts.append(self.load_draft(entry.name))
                    except Exception:
                        continue
        return drafts

    def cancel_draft(self, draft_id: EntityId | str) -> DraftState:
        """Cancel any running or not_started stages in an active draft."""
        current = self.load_draft(draft_id)
        updated_stages = dict(current.stages)

        for stage_name, stage_state in current.stages.items():
            if stage_state.status in ("running", "not_started"):
                updated_stages[stage_name] = stage_state.model_copy(update={"status": "cancelled"})

        updated_draft = current.model_copy(update={"stages": updated_stages})
        return self.save_draft(updated_draft, expected_revision=current.revision)

    def delete_draft(self, draft_id: EntityId | str) -> bool:
        """Permanently remove a draft directory."""
        draft_dir = self._resolve_draft_dir(draft_id)
        if not draft_dir.exists():
            return False
        shutil.rmtree(draft_dir)
        return True
