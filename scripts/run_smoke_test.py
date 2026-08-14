#!/usr/bin/env python3
"""Deterministic vertical-slice smoke test.

Exercises the full exploration pipeline in a temporary directory without any
network access or Ollama dependency, testing both:

  Phase 1: Direct Engine exploration use cases & atomic save persistence.
  Phase 2: FastAPI in-process ASGI transport via TestClient with dependency injection.

Exit codes:
  0 — all steps passed
  1 — any step failed (error message printed to stderr)

Usage:
  uv run python scripts/run_smoke_test.py
  uv run python scripts/run_smoke_test.py --fail  # inject empty RNG to test exit 1
"""

from __future__ import annotations

import argparse
import datetime
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

# Ensure src is in sys.path when script is executed directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_action_interpreter, get_random_source
from app.main import create_app
from campaign.storage.save_reader import SaveReader
from campaign.storage.save_writer import SaveWriter
from domain.models.area import AreaDefinition, AreaObject
from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.common import EntityId
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta
from engine.actions.creative import CreativeValidator
from engine.actions.operations import OperationValidator
from engine.actions.protocols import ActionInterpreter
from engine.actions.resolution import CheckResolver
from engine.actions.resolver import EntityResolver
from engine.actions.use_cases import ExplorationUseCases
from engine.dice.testing import ScriptedRandomSource
from llm.contracts.action import ActionProposal, EntityMention

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
CAMPAIGN_ID: EntityId = "smoke-campaign-1"
SAVE_ID: EntityId = "smoke-save-1"


# ---------------------------------------------------------------------------
# Fake Action Interpreter
# ---------------------------------------------------------------------------


class FakeActionInterpreter(ActionInterpreter):
    """Deterministic fake interpreter for smoke testing."""

    def __init__(self, proposal_map: dict[str, ActionProposal]) -> None:
        self.proposal_map = proposal_map

    def interpret(
        self,
        player_text: str,
        candidates: Any = None,
    ) -> ActionProposal:
        if player_text in self.proposal_map:
            return self.proposal_map[player_text]
        raise ValueError(f"No fake proposal for text: {player_text}")


# ---------------------------------------------------------------------------
# Direct Engine Helpers
# ---------------------------------------------------------------------------


def _make_state() -> RuntimeState:
    """Build a minimal but valid initial player state."""
    player = PlayerState(
        id="player-1",
        name="Smoke Hero",
        background_id="bg-scholar",
        stats=StatBlock(
            strength=10,
            dexterity=10,
            intelligence=10,
            charisma=10,
            constitution=10,
            wisdom=10,
        ),
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=2, maximum=5),
        mana=ResourceValue(current=5, maximum=5),
        mana_regen=1,
        speed=30,
        luck_capacity=3,
        luck_current=2,
    )
    return RuntimeState(
        campaign_id=CAMPAIGN_ID,
        campaign_version="1.0.0",
        campaign_fingerprint="smoke-fp-abc",
        save_id=SAVE_ID,
        revision=1,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(protagonist_id="player-1"),
        location=__import__("domain.models.world_state", fromlist=["LocationState"]).LocationState(
            area_id="area-smoke"
        ),
        plot=PlotState(),
    )


def _make_meta() -> SaveMeta:
    return SaveMeta(
        campaign_id=CAMPAIGN_ID,
        campaign_version="1.0.0",
        save_id=SAVE_ID,
        derived_from_revision=1,
        slot_kind="auto",
        slot_name="Smoke Save",
        player_display_name="Smoke Hero",
        player_level=1,
        campaign_title="Smoke Campaign",
        current_area_display_name="Vault",
        difficulty=DefaultDifficulty.NORMAL,
        created_at=_NOW,
        updated_at=_NOW,
        recovery_status="ok",
    )


def _make_area() -> AreaDefinition:
    return AreaDefinition(
        id="area-smoke",
        name="Vault",
        description="A sealed vault.",
        major_location_id="loc-vault",
        art_prompt="stone vault with a locked chest",
        danger_level=2,
        local_faction_ids=[],
        secrets=[],
        connected_area_ids=[],
        residents=[],
        objects=[
            AreaObject(
                id="obj-lockbox",
                name="Lockbox",
                description="A heavy iron lockbox",
                location_anchor="center",
                state="locked",
                interactable_tags=["container"],
                capability_requirements=[],
                allowed_effect_ids=[],
            )
        ],
        encounters=[],
    )


def _make_use_cases(scripted_rolls: list[int]) -> ExplorationUseCases:
    return ExplorationUseCases(
        entity_resolver=EntityResolver(),
        op_validator=OperationValidator(),
        creative_validator=CreativeValidator(),
        check_resolver=CheckResolver(ScriptedRandomSource(scripted_rolls)),
        campaign_areas={"area-smoke": _make_area()},
    )


def _step(label: str, *, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    line = f"  [{status}] {label}"
    if detail:
        line += f": {detail}"
    print(line)
    if not ok:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Phase 1: Direct Engine Smoke
# ---------------------------------------------------------------------------


def run_direct_smoke(tmp_path: Path, scripted_rolls: list[int]) -> None:
    """Execute direct engine smoke steps under tmp_path."""
    print("smoke: Phase 1 — Direct Engine exploration test")

    # --- Step 1: Write initial save ---
    state = _make_state()
    meta = _make_meta()
    writer = SaveWriter(tmp_path)
    writer.write_state(state, meta, None)
    _step("Write initial save", ok=True)

    # --- Step 2: Reload save ---
    reader = SaveReader(tmp_path)
    loaded = reader.load_save(CAMPAIGN_ID, SAVE_ID)
    _step(
        "Reload save",
        ok=loaded.state.revision == 1 and loaded.state.pending_check is None,
        detail=f"revision={loaded.state.revision}",
    )

    uc = _make_use_cases(scripted_rolls)

    # --- Step 3: Direct inspect (no check) ---
    proposal_inspect = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="smoke-req-inspect",
        status="valid",
        operation="inspect",
        verb="look at",
        intended_effect="examine the lockbox closely",
        challenge_label="none",
        stakes=[],
        entity_mentions=[EntityMention(text="Lockbox", role="target")],
        capability_mentions=[],
    )
    inspect_result = uc.submit_action(loaded.state, proposal_inspect, "cmd-inspect-1")
    _step(
        "Submit direct inspect",
        ok=inspect_result.rejection_reason is None and not inspect_result.has_pending_check,
        detail=f"revision={inspect_result.state.revision}",
    )

    # Persist inspect result
    writer.write_state(inspect_result.state, meta, None)

    # --- Step 4: Submit proposal requiring a check ---
    reloaded = reader.load_save(CAMPAIGN_ID, SAVE_ID).state
    proposal_check = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="smoke-req-check",
        status="valid",
        operation="inspect",
        verb="pick",
        intended_effect="pick the lock on the lockbox",
        challenge_label="standard",
        stakes=["discover treasure", "fail with noise"],
        entity_mentions=[EntityMention(text="Lockbox", role="target")],
        capability_mentions=[],
    )
    check_result = uc.submit_action(reloaded, proposal_check, "cmd-check-1")
    p_check = check_result.state.pending_check
    check_detail = f"check={p_check.semantic_difficulty if p_check else None}"
    _step(
        "Submit proposal with check",
        ok=check_result.rejection_reason is None and check_result.has_pending_check,
        detail=check_detail,
    )

    # Persist pending-check state
    writer.write_state(check_result.state, meta, None)

    # --- Step 5: Resolve check ---
    pre_resolve = reader.load_save(CAMPAIGN_ID, SAVE_ID).state
    try:
        resolve_result = uc.resolve_check(pre_resolve, use_luck=False)
        resolve_ok = resolve_result.state.pending_check is None
        resolve_detail = (
            f"roll={resolve_result.roll} band={resolve_result.band} "
            f"revision={resolve_result.state.revision}"
        )
    except Exception as exc:
        _step("Resolve check", ok=False, detail=str(exc))
        return
    _step("Resolve check", ok=resolve_ok, detail=resolve_detail)

    # Persist resolved state
    writer.write_state(resolve_result.state, meta, None)

    # --- Step 6: Final reload and validate ---
    final = reader.load_save(CAMPAIGN_ID, SAVE_ID).state
    _step(
        "Final reload",
        ok=final.pending_check is None and final.revision == 4,
        detail=f"revision={final.revision}",
    )


# ---------------------------------------------------------------------------
# Phase 2: FastAPI In-Process ASGI Smoke
# ---------------------------------------------------------------------------


def run_asgi_smoke(tmp_path: Path, scripted_rolls: list[int]) -> None:
    """Execute FastAPI smoke steps via in-process TestClient."""
    print("smoke: Phase 2 — FastAPI in-process ASGI test")

    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir(parents=True, exist_ok=True)

    # Copy valid-minimal campaign fixture
    fixture_src = _REPO_ROOT / "tests" / "fixtures" / "campaigns" / "valid-minimal"
    target_camp = campaigns_dir / "minimal-campaign"
    if not target_camp.exists():
        shutil.copytree(fixture_src, target_camp)

    settings = Settings(
        campaigns_dir=str(campaigns_dir),
        storymode_env="test",
    )
    app = create_app(settings)
    client = TestClient(app)

    # Configure fake interpreter and scripted RNG
    proposal_inspect = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="asgi-req-inspect",
        status="valid",
        operation="inspect",
        verb="look",
        intended_effect="examine object",
        challenge_label="none",
        stakes=[],
        entity_mentions=[EntityMention(text="Object", role="target")],
        capability_mentions=[],
    )
    proposal_check = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="asgi-req-check",
        status="valid",
        operation="inspect",
        verb="force",
        intended_effect="force object open",
        challenge_label="standard",
        stakes=["succeed", "fail"],
        entity_mentions=[EntityMention(text="Object", role="target")],
        capability_mentions=[],
    )

    fake_interpreter = FakeActionInterpreter(
        {
            "examine object": proposal_inspect,
            "force object open": proposal_check,
        }
    )
    app.dependency_overrides[get_action_interpreter] = lambda: fake_interpreter
    app.dependency_overrides[get_random_source] = lambda: ScriptedRandomSource(scripted_rolls)

    # 1. POST /api/v1/saves -> Create save
    create_resp = client.post(
        "/api/v1/saves",
        json={
            "campaign_id": "minimal-campaign",
            "command_id": "cmd-asgi-create",
            "slot_name": "ASGI Save",
            "slot_kind": "manual",
            "player_name": "ASGI Hero",
            "background_id": "bg-1",
            "difficulty": "normal",
            "stats": {
                "strength": 10,
                "dexterity": 12,
                "constitution": 13,
                "intelligence": 15,
                "wisdom": 14,
                "charisma": 8,
            },
        },
    )
    _step(
        "FastAPI create save",
        ok=create_resp.status_code == 201,
        detail=f"status={create_resp.status_code}",
    )
    save_id = create_resp.json()["save_id"]

    # 2. GET /api/v1/saves/{campaign_id}/{save_id} -> Verify save
    get_resp = client.get(f"/api/v1/saves/minimal-campaign/{save_id}")
    _step(
        "FastAPI verify initial save",
        ok=get_resp.status_code == 200 and get_resp.json()["revision"] == 1,
        detail=f"revision={get_resp.json().get('revision')}",
    )

    # 3. POST /api/v1/actions/submit -> Inspect action (no check)
    inspect_resp = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "command_id": "cmd-asgi-inspect",
            "expected_revision": 1,
            "player_text": "examine object",
        },
    )
    _step(
        "FastAPI submit direct action",
        ok=inspect_resp.status_code == 200 and inspect_resp.json()["revision"] == 2,
        detail=f"revision={inspect_resp.json().get('revision')}",
    )

    # 4. POST /api/v1/actions/submit -> Force object (pending check)
    check_resp = client.post(
        "/api/v1/actions/submit",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "command_id": "cmd-asgi-check",
            "expected_revision": 2,
            "player_text": "force object open",
        },
    )
    _step(
        "FastAPI submit action with check",
        ok=(
            check_resp.status_code == 200
            and check_resp.json()["has_pending_check"] is True
            and check_resp.json()["revision"] == 3
        ),
        detail=f"revision={check_resp.json().get('revision')}",
    )

    # 5. POST /api/v1/actions/resolve-check -> Resolve check
    resolve_resp = client.post(
        "/api/v1/actions/resolve-check",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "command_id": "cmd-asgi-resolve",
            "expected_revision": 3,
            "use_luck": False,
        },
    )
    _step(
        "FastAPI resolve check",
        ok=(
            resolve_resp.status_code == 200
            and resolve_resp.json()["revision"] == 4
            and resolve_resp.json()["band"] == "strong"
        ),
        detail=f"status={resolve_resp.status_code} band={resolve_resp.json().get('band')}",
    )

    # 6. GET /api/v1/saves/{campaign_id}/{save_id} -> State reload before combat
    mid_resp = client.get(f"/api/v1/saves/minimal-campaign/{save_id}")
    _step(
        "FastAPI exploration state reload",
        ok=mid_resp.status_code == 200 and mid_resp.json()["revision"] == 4,
        detail=f"revision={mid_resp.json().get('revision')}",
    )

    # 7. POST /api/v1/combat/start -> Start combat encounter
    start_resp = client.post(
        "/api/v1/combat/start",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "encounter_id": "encounter-1",
            "command_id": "cmd-asgi-start-combat",
            "expected_revision": 4,
        },
    )
    _step(
        "FastAPI start combat encounter",
        ok=(
            start_resp.status_code == 200
            and start_resp.json()["revision"] == 5
            and start_resp.json()["combat"] is not None
            and len(start_resp.json()["allowed_actions"]) > 0
        ),
        detail=f"revision={start_resp.json().get('revision')}",
    )

    # 8. GET /api/v1/combat/view -> View combat state
    view_resp = client.get(f"/api/v1/combat/view?campaign_id=minimal-campaign&save_id={save_id}")
    _step(
        "FastAPI get combat view",
        ok=(
            view_resp.status_code == 200
            and view_resp.json()["revision"] == 5
            and view_resp.json()["combat"] is not None
        ),
        detail=f"revision={view_resp.json().get('revision')}",
    )

    # 9. POST /api/v1/combat/yield -> Resolve combat
    yield_resp = client.post(
        "/api/v1/combat/yield",
        json={
            "campaign_id": "minimal-campaign",
            "save_id": save_id,
            "command_id": "cmd-asgi-yield",
            "expected_revision": 5,
        },
    )
    _step(
        "FastAPI yield and resolve combat",
        ok=(
            yield_resp.status_code == 200
            and yield_resp.json()["revision"] == 6
            and yield_resp.json()["is_terminal"] is True
            and yield_resp.json()["outcome"] == "Yielded"
            and yield_resp.json()["combat"] is None
        ),
        detail=f"rev={yield_resp.json().get('revision')} out={yield_resp.json().get('outcome')}",
    )

    # 10. GET /api/v1/saves/{campaign_id}/{save_id} -> Final verification
    final_resp = client.get(f"/api/v1/saves/minimal-campaign/{save_id}")
    _step(
        "FastAPI final state reload after combat",
        ok=final_resp.status_code == 200 and final_resp.json()["revision"] == 6,
        detail=f"revision={final_resp.json().get('revision')}",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Inject empty RNG to trigger exit 1",
    )
    args = parser.parse_args()

    # Scripted rolls: with --fail supply an empty list so the resolver will
    # raise ScriptedRandomSource exhaustion -> failure.
    scripted_rolls: list[int] = [] if args.fail else [15, 15, 15, 15, 15, 15, 15, 15]

    with tempfile.TemporaryDirectory(prefix="storymode_smoke_") as tmp:
        tmp_path = Path(tmp)
        run_direct_smoke(tmp_path, scripted_rolls)
        run_asgi_smoke(tmp_path, scripted_rolls)

    print("smoke: all steps passed")


if __name__ == "__main__":
    main()
