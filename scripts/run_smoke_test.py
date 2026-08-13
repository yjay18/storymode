#!/usr/bin/env python3
"""Deterministic vertical-slice smoke test.

Exercises the full exploration pipeline in a temporary directory without any
network access, Ollama, or FastAPI dependency:

  1. Create a minimal campaign folder (one area, one interactable object).
  2. Create a character state with a valid stat allocation.
  3. Write an initial save to disk.
  4. Submit a fixed inspection proposal (challenge_label='none') — no check.
  5. Submit a proposal that requires a check (challenge_label='standard').
  6. Resolve the check using a scripted die roll via dependency injection.
  7. Reload state from disk and verify revision / pending-check cleared.

Exit codes:
  0 — all steps passed
  1 — any step failed (error message printed to stderr)

Usage:
  uv run python scripts/run_smoke_test.py
  uv run python scripts/run_smoke_test.py --fail  # inject bad roll to test exit 1
"""

from __future__ import annotations

import argparse
import datetime
import sys
import tempfile
from pathlib import Path

# Ensure src/ is on the path when invoked from project root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

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
from engine.actions.resolution import CheckResolver
from engine.actions.resolver import EntityResolver
from engine.actions.use_cases import ExplorationUseCases
from engine.dice.testing import ScriptedRandomSource
from llm.contracts.action import ActionProposal, EntityMention

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
CAMPAIGN_ID: EntityId = "smoke-campaign-1"
SAVE_ID: EntityId = "smoke-save-1"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _make_state() -> RuntimeState:
    """Build a minimal but valid initial player state.

    Stat allocation uses 10 in all six stats (27-point buy equivalent;
    point-buy validation is a CHAR-01 concern not yet in scope).
    """
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
        location=__import__(
            "domain.models.world_state", fromlist=["LocationState"]
        ).LocationState(area_id="area-smoke"),
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


# ---------------------------------------------------------------------------
# Smoke steps
# ---------------------------------------------------------------------------

def _step(label: str, *, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    line = f"  [{status}] {label}"
    if detail:
        line += f": {detail}"
    print(line)
    if not ok:
        sys.exit(1)


def run_smoke(tmp_path: Path, scripted_rolls: list[int]) -> None:
    """Execute all smoke steps under tmp_path."""
    print("smoke: Storymode vertical-slice smoke test")

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
    _step(
        "Submit proposal with check",
        ok=check_result.rejection_reason is None and check_result.has_pending_check,
        detail=f"check={check_result.state.pending_check and check_result.state.pending_check.semantic_difficulty}",
    )

    # Persist pending-check state
    writer.write_state(check_result.state, meta, None)

    # --- Step 5: Resolve check ---
    pre_resolve = reader.load_save(CAMPAIGN_ID, SAVE_ID).state
    try:
        resolve_result = uc.resolve_check(pre_resolve, use_luck=False)
        resolve_ok = resolve_result.state.pending_check is None
        resolve_detail = f"roll={resolve_result.roll} band={resolve_result.band} revision={resolve_result.state.revision}"
    except Exception as exc:
        _step("Resolve check", ok=False, detail=str(exc))
        return  # unreachable — _step calls sys.exit(1) on failure
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

    print("smoke: all steps passed")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Inject an invalid (out-of-range) die value to trigger exit 1",
    )
    args = parser.parse_args()

    # Scripted rolls: with --fail supply an empty list so the resolver will
    # raise ScriptedRandomSource exhaustion → failure.
    scripted_rolls: list[int] = [] if args.fail else [15]

    with tempfile.TemporaryDirectory(prefix="storymode_smoke_") as tmp:
        tmp_path = Path(tmp)
        run_smoke(tmp_path, scripted_rolls)


if __name__ == "__main__":
    main()
