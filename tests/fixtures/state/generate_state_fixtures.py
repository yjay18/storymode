"""Generate valid and invalid state fixtures."""

import json
from pathlib import Path
from typing import Any

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState


def generate_fixtures() -> None:
    base_dir = Path("tests/fixtures/state")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate valid state
    player = PlayerState(
        id="hero",
        name="Hero",
        background_id="bg-1",
        stats=StatBlock(strength=10, dexterity=10, intelligence=10, charisma=10, constitution=10, wisdom=10),
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        mana_regen=2,
        speed=30,
        luck_capacity=3,
    )
    
    valid_state = RuntimeState(
        campaign_id="camp-1",
        campaign_version="1.0.0",
        campaign_fingerprint="fp",
        save_id="save-1",
        revision=10,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(protagonist_id="hero"),
        location=LocationState(area_id="town"),
        plot=PlotState(),
    )
    
    with open(base_dir / "valid_state.json", "w") as f:
        f.write(valid_state.model_dump_json(indent=2))
        
    # Generate invalid state (missing required fields, bad types, breaking invariants)
    valid_dict: dict[str, Any] = json.loads(valid_state.model_dump_json())
    
    # Break an invariant: revision trailing last command receipt
    valid_dict["revision"] = 0
    valid_dict["last_command_receipts"] = [{
        "command_id": "cmd-1",
        "canonical_request_hash": "hash",
        "committed_revision": 5,
        "result_kind": "success",
        "safe_result_summary": "ok",
        "roll_ids": []
    }]
    
    with open(base_dir / "invalid_state.json", "w") as f:
        json.dump(valid_dict, f, indent=2)


if __name__ == "__main__":
    generate_fixtures()
