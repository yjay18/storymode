"""Export JSON schemas for runtime state models."""

import json
from pathlib import Path

from pydantic import BaseModel

from domain.models.audit import JournalEvent, RollRecord
from domain.models.narrative_memory import NarrativeMemory
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta


def export_schemas(output_dir: Path) -> None:
    """Export all runtime state JSON schemas to the given directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    models: dict[str, type[BaseModel]] = {
        "runtime_state.json": RuntimeState,
        "journal_event.json": JournalEvent,
        "roll_record.json": RollRecord,
        "narrative_memory.json": NarrativeMemory,
        "save_meta.json": SaveMeta,
    }
    
    for filename, model_cls in models.items():
        schema = model_cls.model_json_schema()
        with open(output_dir / filename, "w") as f:
            json.dump(schema, f, indent=2)


if __name__ == "__main__":
    export_schemas(Path("data/schemas/runtime"))
