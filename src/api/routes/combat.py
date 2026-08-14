"""Combat API endpoints."""

import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.routes.campaigns import _resolve_campaign_dir
from api.schemas.combat import (
    CombatResponse,
    CombatViewResponse,
    DefendRequest,
    FleeRequest,
    StartCombatRequest,
    UseSkillRequest,
    YieldRequest,
)
from app.config import Settings
from app.dependencies import get_random_source, get_settings
from campaign.storage.save_reader import SaveReader
from campaign.storage.save_writer import SaveWriter
from domain.models.common import EntityId
from domain.models.pack import CampaignPack
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta
from engine.campaign import load_campaign
from engine.combat.use_cases import CombatUseCases
from engine.dice.ports import RandomSource
from engine.dice.service import DiceService
from engine.state.errors import SaveError

router = APIRouter(prefix="/combat", tags=["combat"])


def _build_combat_use_cases(pack: CampaignPack, random_source: RandomSource) -> CombatUseCases:
    dice_service = DiceService(
        rng=random_source,
        clock=lambda: datetime.datetime.now(datetime.UTC),
        id_generator=lambda: EntityId("roll_combat"),
    )
    skills = {s.id: s for s in pack.skills.combat_skills}
    enemies = {e.id: e for e in pack.enemies.enemy_archetypes}
    companions = {c.id: c for c in pack.characters.companions}

    return CombatUseCases(
        skills=skills,
        enemy_archetypes=enemies,
        dice_service=dice_service,
        rng=random_source,
        companions=companions,
    )


def _load_campaign_and_save(
    settings: Settings,
    campaign_id: EntityId,
    save_id: EntityId,
) -> tuple[CampaignPack, RuntimeState, SaveMeta, Path]:
    c_dir = _resolve_campaign_dir(settings, campaign_id)
    pack, _ = load_campaign(c_dir)
    if pack is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign '{campaign_id}' is invalid or cannot be loaded",
        )

    root_dir = Path(settings.campaigns_dir).resolve()
    reader = SaveReader(root_dir)
    try:
        load_result = reader.load_save(campaign_id, save_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Save not found",
        ) from None

    if load_result.meta is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Save metadata missing",
        )

    return pack, load_result.state, load_result.meta, root_dir


def _handle_value_error(e: ValueError) -> HTTPException:
    err_str = str(e).lower()
    if "revision conflict" in err_str:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(e),
    )


@router.get("/view", response_model=CombatViewResponse)
def get_combat_view(
    campaign_id: Annotated[EntityId, Query(...)],
    save_id: Annotated[EntityId, Query(...)],
    settings: Annotated[Settings, Depends(get_settings)],
    random_source: Annotated[RandomSource, Depends(get_random_source)],
) -> CombatViewResponse:
    """Retrieve the authoritative active combat state and allowed actions."""
    pack, state, _meta, _root = _load_campaign_and_save(settings, campaign_id, save_id)
    use_cases = _build_combat_use_cases(pack, random_source)
    allowed = use_cases.get_allowed_actions(state)

    return CombatViewResponse(
        save_id=state.save_id,
        campaign_id=state.campaign_id,
        revision=state.revision,
        combat=state.combat,
        allowed_actions=allowed,
    )


@router.post("/start", response_model=CombatResponse)
def start_combat(
    request: StartCombatRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    random_source: Annotated[RandomSource, Depends(get_random_source)],
) -> CombatResponse:
    """Start an authored combat encounter."""
    pack, state, meta, root_dir = _load_campaign_and_save(
        settings, request.campaign_id, request.save_id
    )

    # Lookup encounter definition in current area
    area = next((a for a in pack.areas.areas if a.id == state.location.area_id), None)
    if area is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Current area '{state.location.area_id}' not found in campaign pack",
        )

    encounter = next((e for e in area.encounters if e.id == request.encounter_id), None)
    if encounter is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Encounter '{request.encounter_id}' not found in area '{area.id}'",
        )

    use_cases = _build_combat_use_cases(pack, random_source)

    try:
        res = use_cases.start_combat(
            state=state,
            encounter_id=request.encounter_id,
            enemy_archetype_ids=encounter.enemy_archetype_ids,
            command_id=request.command_id,
            expected_revision=request.expected_revision,
            escape_policy_id=encounter.escape_policy_id,
        )
    except ValueError as e:
        raise _handle_value_error(e) from e

    # Persist
    writer = SaveWriter(root_dir)
    try:
        writer.write_state(res.state, meta, None)
    except SaveError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist save: {e}",
        ) from e

    return CombatResponse(
        save_id=res.state.save_id,
        campaign_id=res.state.campaign_id,
        revision=res.state.revision,
        combat=res.state.combat,
        allowed_actions=res.allowed_actions,
        is_terminal=res.is_terminal,
        outcome=res.outcome,
        logs=res.logs,
    )


@router.post("/skill", response_model=CombatResponse)
def execute_skill(
    request: UseSkillRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    random_source: Annotated[RandomSource, Depends(get_random_source)],
) -> CombatResponse:
    """Execute a combat skill command."""
    pack, state, meta, root_dir = _load_campaign_and_save(
        settings, request.campaign_id, request.save_id
    )

    use_cases = _build_combat_use_cases(pack, random_source)

    try:
        res = use_cases.execute_skill(
            state=state,
            skill_id=request.skill_id,
            target_ids=request.target_ids,
            command_id=request.command_id,
            expected_revision=request.expected_revision,
        )
    except ValueError as e:
        raise _handle_value_error(e) from e

    # Persist
    writer = SaveWriter(root_dir)
    try:
        writer.write_state(res.state, meta, None)
    except SaveError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist save: {e}",
        ) from e

    return CombatResponse(
        save_id=res.state.save_id,
        campaign_id=res.state.campaign_id,
        revision=res.state.revision,
        combat=res.state.combat,
        allowed_actions=res.allowed_actions,
        is_terminal=res.is_terminal,
        outcome=res.outcome,
        logs=res.logs,
    )


@router.post("/defend", response_model=CombatResponse)
def execute_defend(
    request: DefendRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    random_source: Annotated[RandomSource, Depends(get_random_source)],
) -> CombatResponse:
    """Execute the Defend action (0-cost Guarded)."""
    pack, state, meta, root_dir = _load_campaign_and_save(
        settings, request.campaign_id, request.save_id
    )

    use_cases = _build_combat_use_cases(pack, random_source)

    try:
        res = use_cases.execute_defend(
            state=state,
            command_id=request.command_id,
            expected_revision=request.expected_revision,
        )
    except ValueError as e:
        raise _handle_value_error(e) from e

    # Persist
    writer = SaveWriter(root_dir)
    try:
        writer.write_state(res.state, meta, None)
    except SaveError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist save: {e}",
        ) from e

    return CombatResponse(
        save_id=res.state.save_id,
        campaign_id=res.state.campaign_id,
        revision=res.state.revision,
        combat=res.state.combat,
        allowed_actions=res.allowed_actions,
        is_terminal=res.is_terminal,
        outcome=res.outcome,
        logs=res.logs,
    )


@router.post("/flee", response_model=CombatResponse)
def execute_flee(
    request: FleeRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    random_source: Annotated[RandomSource, Depends(get_random_source)],
) -> CombatResponse:
    """Attempt to flee from combat."""
    pack, state, meta, root_dir = _load_campaign_and_save(
        settings, request.campaign_id, request.save_id
    )

    use_cases = _build_combat_use_cases(pack, random_source)

    try:
        res = use_cases.execute_flee(
            state=state,
            command_id=request.command_id,
            expected_revision=request.expected_revision,
        )
    except ValueError as e:
        raise _handle_value_error(e) from e

    # Persist
    writer = SaveWriter(root_dir)
    try:
        writer.write_state(res.state, meta, None)
    except SaveError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist save: {e}",
        ) from e

    return CombatResponse(
        save_id=res.state.save_id,
        campaign_id=res.state.campaign_id,
        revision=res.state.revision,
        combat=res.state.combat,
        allowed_actions=res.allowed_actions,
        is_terminal=res.is_terminal,
        outcome=res.outcome,
        logs=res.logs,
    )


@router.post("/yield", response_model=CombatResponse)
def execute_yield(
    request: YieldRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    random_source: Annotated[RandomSource, Depends(get_random_source)],
) -> CombatResponse:
    """Yield to the enemy."""
    pack, state, meta, root_dir = _load_campaign_and_save(
        settings, request.campaign_id, request.save_id
    )

    use_cases = _build_combat_use_cases(pack, random_source)

    try:
        res = use_cases.execute_yield(
            state=state,
            command_id=request.command_id,
            expected_revision=request.expected_revision,
        )
    except ValueError as e:
        raise _handle_value_error(e) from e

    # Persist
    writer = SaveWriter(root_dir)
    try:
        writer.write_state(res.state, meta, None)
    except SaveError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist save: {e}",
        ) from e

    return CombatResponse(
        save_id=res.state.save_id,
        campaign_id=res.state.campaign_id,
        revision=res.state.revision,
        combat=res.state.combat,
        allowed_actions=res.allowed_actions,
        is_terminal=res.is_terminal,
        outcome=res.outcome,
        logs=res.logs,
    )
