"""Action API endpoints."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.routes.campaigns import _resolve_campaign_dir
from api.schemas.actions import (
    CancelCheckRequest,
    CancelCheckResponse,
    ResolveCheckRequest,
    ResolveCheckResponse,
    SubmitActionRequest,
    SubmitActionResponse,
)
from app.config import Settings
from app.dependencies import get_action_interpreter, get_random_source, get_settings
from campaign.storage.save_reader import SaveReader
from campaign.storage.save_writer import SaveWriter
from domain.models.common import DisplayString, EntityId
from domain.models.runtime_state import CommandReceipt
from engine.actions.creative import CreativeValidator
from engine.actions.operations import OperationValidator
from engine.actions.protocols import ActionInterpreter
from engine.actions.resolution import CheckResolver
from engine.actions.resolver import EntityResolver
from engine.actions.use_cases import ExplorationUseCases
from engine.campaign import load_campaign
from engine.dice.ports import RandomSource
from engine.state.errors import SaveError

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("/submit", response_model=SubmitActionResponse)
def submit_action(
    request: SubmitActionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    interpreter: Annotated[ActionInterpreter | None, Depends(get_action_interpreter)],
    random_source: Annotated[RandomSource, Depends(get_random_source)],
) -> SubmitActionResponse:
    """Submit a player exploration action."""
    if interpreter is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="interpreter_not_configured",
        )

    # 1. Load campaign
    c_dir = _resolve_campaign_dir(settings, request.campaign_id)
    pack, _ = load_campaign(c_dir)
    if pack is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campaign '{request.campaign_id}' is invalid or cannot be loaded",
        )

    root_dir = Path(settings.campaigns_dir).resolve()
    reader = SaveReader(root_dir)
    try:
        load_result = reader.load_save(request.campaign_id, request.save_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Save not found"
        ) from None

    state = load_result.state
    meta = load_result.meta
    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Save metadata missing",
        )

    # 2. Check revision conflict
    if state.revision != request.expected_revision:
        msg = (
            f"State revision conflict: expected {request.expected_revision}, "
            f"current is {state.revision}"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)

    # 3. Idempotency check: if command_id already in receipts
    for receipt in state.last_command_receipts:
        if receipt.command_id == request.command_id:
            return SubmitActionResponse(
                save_id=state.save_id,
                campaign_id=state.campaign_id,
                revision=state.revision,
                has_pending_check=state.pending_check is not None,
                rejection_reason=None,
                pending_check=state.pending_check,
            )

    # 4. Interpret action proposal
    try:
        proposal = interpreter.interpret(request.player_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to interpret action: {e}",
        ) from e

    # 5. Evaluate action with deterministic use case
    use_cases = ExplorationUseCases(
        entity_resolver=EntityResolver(),
        op_validator=OperationValidator(),
        creative_validator=CreativeValidator(),
        check_resolver=CheckResolver(random_source),
        campaign_areas={a.id: a for a in pack.areas.areas},
    )
    submit_result = use_cases.submit_action(state, proposal, request.command_id)

    if submit_result.rejection_reason is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=submit_result.rejection_reason,
        )

    # Record receipt
    receipt = CommandReceipt(
        command_id=EntityId(request.command_id),
        canonical_request_hash=f"hash-{request.command_id}",
        committed_revision=submit_result.state.revision,
        result_kind=DisplayString("submit_action"),
        safe_result_summary=DisplayString("Action submitted"),
        roll_ids=[],
    )
    receipts = [*submit_result.state.last_command_receipts[-99:], receipt]
    committed_state = submit_result.state.model_copy(update={"last_command_receipts": receipts})

    # 6. Save atomically
    writer = SaveWriter(root_dir)
    try:
        writer.write_state(committed_state, meta, None)
    except SaveError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist save: {e}",
        ) from e

    return SubmitActionResponse(
        save_id=committed_state.save_id,
        campaign_id=committed_state.campaign_id,
        revision=committed_state.revision,
        has_pending_check=submit_result.has_pending_check,
        rejection_reason=None,
        pending_check=committed_state.pending_check,
    )


@router.post("/resolve-check", response_model=ResolveCheckResponse)
def resolve_check(
    request: ResolveCheckRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    random_source: Annotated[RandomSource, Depends(get_random_source)],
) -> ResolveCheckResponse:
    """Resolve an active pending check."""
    # 1. Load campaign
    c_dir = _resolve_campaign_dir(settings, request.campaign_id)
    pack, _ = load_campaign(c_dir)
    if pack is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campaign '{request.campaign_id}' is invalid or cannot be loaded",
        )

    root_dir = Path(settings.campaigns_dir).resolve()
    reader = SaveReader(root_dir)
    try:
        load_result = reader.load_save(request.campaign_id, request.save_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Save not found"
        ) from None

    state = load_result.state
    meta = load_result.meta
    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Save metadata missing",
        )

    # 2. Check revision
    if state.revision != request.expected_revision:
        msg = (
            f"State revision conflict: expected {request.expected_revision}, "
            f"current is {state.revision}"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)

    # 3. Guard: must have pending check
    if state.pending_check is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No active pending check to resolve",
        )

    # 4. Resolve check
    use_cases = ExplorationUseCases(
        entity_resolver=EntityResolver(),
        op_validator=OperationValidator(),
        creative_validator=CreativeValidator(),
        check_resolver=CheckResolver(random_source),
        campaign_areas={a.id: a for a in pack.areas.areas},
    )
    resolve_result = use_cases.resolve_check(state, use_luck=request.use_luck)

    # Record receipt
    receipt = CommandReceipt(
        command_id=EntityId(request.command_id),
        canonical_request_hash=f"hash-{request.command_id}",
        committed_revision=resolve_result.state.revision,
        result_kind=DisplayString("resolve_check"),
        safe_result_summary=DisplayString("Check resolved"),
        roll_ids=[],
    )
    receipts = [*resolve_result.state.last_command_receipts[-99:], receipt]
    committed_state = resolve_result.state.model_copy(update={"last_command_receipts": receipts})

    # 5. Save atomically
    writer = SaveWriter(root_dir)
    try:
        writer.write_state(committed_state, meta, None)
    except SaveError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist save: {e}",
        ) from e

    return ResolveCheckResponse(
        save_id=committed_state.save_id,
        campaign_id=committed_state.campaign_id,
        revision=committed_state.revision,
        roll=resolve_result.roll,
        band=resolve_result.band,
    )


@router.post("/cancel-check", response_model=CancelCheckResponse)
def cancel_check(
    request: CancelCheckRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    random_source: Annotated[RandomSource, Depends(get_random_source)],
) -> CancelCheckResponse:
    """Cancel an active pending check."""
    # 1. Load campaign
    c_dir = _resolve_campaign_dir(settings, request.campaign_id)
    pack, _ = load_campaign(c_dir)
    if pack is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campaign '{request.campaign_id}' is invalid or cannot be loaded",
        )

    root_dir = Path(settings.campaigns_dir).resolve()
    reader = SaveReader(root_dir)
    try:
        load_result = reader.load_save(request.campaign_id, request.save_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Save not found"
        ) from None

    state = load_result.state
    meta = load_result.meta
    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Save metadata missing",
        )

    # 2. Check revision
    if state.revision != request.expected_revision:
        msg = (
            f"State revision conflict: expected {request.expected_revision}, "
            f"current is {state.revision}"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)

    # 3. Guard: must have pending check
    if state.pending_check is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No active pending check to cancel",
        )

    # 4. Cancel check
    use_cases = ExplorationUseCases(
        entity_resolver=EntityResolver(),
        op_validator=OperationValidator(),
        creative_validator=CreativeValidator(),
        check_resolver=CheckResolver(random_source),
        campaign_areas={a.id: a for a in pack.areas.areas},
    )
    cancel_result = use_cases.cancel_check(state)

    # Record receipt
    receipt = CommandReceipt(
        command_id=EntityId(request.command_id),
        canonical_request_hash=f"hash-{request.command_id}",
        committed_revision=cancel_result.state.revision,
        result_kind=DisplayString("cancel_check"),
        safe_result_summary=DisplayString("Check cancelled"),
        roll_ids=[],
    )
    receipts = [*cancel_result.state.last_command_receipts[-99:], receipt]
    committed_state = cancel_result.state.model_copy(update={"last_command_receipts": receipts})

    # 5. Save atomically
    writer = SaveWriter(root_dir)
    try:
        writer.write_state(committed_state, meta, None)
    except SaveError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist save: {e}",
        ) from e

    return CancelCheckResponse(
        save_id=committed_state.save_id,
        campaign_id=committed_state.campaign_id,
        revision=committed_state.revision,
    )
