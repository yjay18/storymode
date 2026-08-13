"""Save recovery and snapshot rotation."""

import datetime
import os
from pathlib import Path

from campaign.storage.save_reader import SaveReader
from campaign.storage.save_writer import SaveWriter
from domain.models.common import DisplayString, EntityId
from domain.models.save_meta import SaveMeta
from engine.state.errors import SaveError


class RecoveryManager:
    """Manages autosave snapshots and derived file recovery."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()
        self._reader = SaveReader(root_dir)
        self._writer = SaveWriter(root_dir)

    def rotate_snapshots(self, campaign_id: EntityId, save_id: EntityId) -> None:
        """Rotate existing state, meta, and memory files into backups before a new commit."""
        save_dir = self._reader._resolve_save_dir(campaign_id, save_id)
        if not save_dir.exists():
            return

        # We keep 3 backups. Move .2 -> .3, .1 -> .2, original -> .1
        for filename in ("state.json", "save_meta.json", "narrative_memory.json"):
            base_path = save_dir / filename
            if not base_path.exists():
                continue

            for i in (2, 1):
                old_path = save_dir / f"{base_path.stem}.{i}.json"
                new_path = save_dir / f"{base_path.stem}.{i+1}.json"
                if old_path.exists():
                    os.replace(old_path, new_path)
                    
            new_path = save_dir / f"{base_path.stem}.1.json"
            # Instead of os.replace, we want to KEEP the original so write_state can overwrite it safely,
            # wait, if we os.replace, we delete the only valid state until write_state completes!
            # The checklist says: "never delete the only valid state (minimum 1 backup before rotation if replacing)".
            # If we copy the file instead of moving it, the original remains as a valid state until atomic replace.
            import shutil
            shutil.copy2(base_path, new_path)

    def list_recoverable_snapshots(self, campaign_id: EntityId, save_id: EntityId) -> list[int]:
        """List available valid snapshot indices (1, 2, 3) that can be recovered."""
        save_dir = self._reader._resolve_save_dir(campaign_id, save_id)
        if not save_dir.exists():
            return []
            
        valid = []
        for i in (1, 2, 3):
            state_path = save_dir / f"state.{i}.json"
            if state_path.exists():
                # We could potentially validate the state here
                valid.append(i)
                
        return valid

    def rebuild_derived_metadata(self, campaign_id: EntityId, save_id: EntityId) -> bool:
        """Extract a minimal fallback SaveMeta from state if save_meta.json is missing or corrupt."""
        save_dir = self._reader._resolve_save_dir(campaign_id, save_id)
        meta_path = save_dir / "save_meta.json"
        
        try:
            # Load state. This might fail if state is corrupt.
            result = self._reader.load_save(campaign_id, save_id)
            state = result.state
            
            meta = SaveMeta(
                campaign_id=state.campaign_id,
                campaign_version=state.campaign_version,
                save_id=state.save_id,
                derived_from_revision=state.revision,
                slot_kind=DisplayString("autosave"),
                slot_name=DisplayString(state.save_id),
                player_display_name=state.player.name,
                player_level=1,
                campaign_title=DisplayString("Unknown"),
                current_area_display_name=DisplayString(state.location.area_id),
                difficulty=state.difficulty,
                play_seconds=state.play_seconds,
                created_at=datetime.datetime.now(datetime.UTC),
                updated_at=datetime.datetime.now(datetime.UTC),
                recovery_status=DisplayString("rebuilt")
            )
            
            self._writer._atomic_write_json(meta_path, meta)
            return True
        except SaveError:
            return False
