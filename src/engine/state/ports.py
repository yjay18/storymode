"""Ports for state operations."""

from typing import Protocol

from domain.models.audit import JournalEvent, RollRecord
from domain.models.common import EntityId, FrozenModel
from domain.models.narrative_memory import NarrativeMemory
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta


class SaveLoadResult(FrozenModel):
    """Result of loading a save."""
    
    state: RuntimeState
    meta: SaveMeta | None
    memory: NarrativeMemory | None
    journal_events: list[JournalEvent]
    roll_records: list[RollRecord]
    
    # Rows loaded but with a revision > state.revision
    prepared_journal_events: list[JournalEvent]
    prepared_roll_records: list[RollRecord]


class SaveRepository(Protocol):
    """Protocol for reading and writing saves."""
    
    def load_save(
        self,
        campaign_id: EntityId,
        save_id: EntityId,
        expected_fingerprint: str | None = None,
    ) -> SaveLoadResult:
        """Load a save and verify its campaign identity."""
        ...
        
    def write_state(self, state: RuntimeState, meta: SaveMeta, memory: NarrativeMemory | None) -> None:
        """Write authoritative state, meta, and optional memory atomically."""
        ...
        
    def append_journal(self, campaign_id: EntityId, save_id: EntityId, events: list[JournalEvent]) -> None:
        """Append events to the journal log."""
        ...
        
    def append_rolls(self, campaign_id: EntityId, save_id: EntityId, rolls: list[RollRecord]) -> None:
        """Append rolls to the roll log."""
        ...
        
    def flush_prepared_rows(
        self,
        campaign_id: EntityId,
        save_id: EntityId,
        journal_events: list[JournalEvent],
        roll_records: list[RollRecord],
    ) -> None:
        """Flush prepared journal events and roll records to their respective logs."""
        ...
