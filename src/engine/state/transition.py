"""State transition utilities."""

from collections.abc import Callable

from domain.models.common import EntityId
from domain.models.runtime_state import CommandReceipt, RuntimeState
from engine.state.errors import IdempotentCommandError, StaleRevisionError

type TransitionResult = tuple[RuntimeState, CommandReceipt]
type MutationFn = Callable[[RuntimeState], TransitionResult]


def apply_command(
    state: RuntimeState,
    expected_revision: int,
    command_id: EntityId,
    canonical_request_hash: str,
    mutation_fn: MutationFn,
) -> TransitionResult:
    """Apply a command with expected revision check and idempotency.

    If the command_id matches a recently committed command:
        - If canonical_request_hash matches, return the old receipt and unmodified state.
        - If it differs, raise IdempotentCommandError.

    If expected_revision != state.revision, raise StaleRevisionError.

    Otherwise, run mutation_fn, bump revision, and append the receipt to last_command_receipts
    (keeping max 10 receipts).
    """
    # 1. Idempotency check
    for receipt in state.last_command_receipts:
        if receipt.command_id == command_id:
            if receipt.canonical_request_hash == canonical_request_hash:
                return state, receipt
            raise IdempotentCommandError(
                f"Command {command_id} previously executed with different payload hash"
            )

    # 2. Revision check
    if expected_revision != state.revision:
        raise StaleRevisionError(
            f"Expected revision {expected_revision}, but state is at {state.revision}"
        )

    # 3. Apply mutation
    new_state, receipt = mutation_fn(state)

    # 4. Bump revision and append receipt
    bumped_rev = state.revision + 1
    final_receipt = receipt.model_copy(
        update={
            "committed_revision": bumped_rev,
            "command_id": command_id,
            "canonical_request_hash": canonical_request_hash,
        }
    )

    receipts = list(new_state.last_command_receipts)
    receipts.append(final_receipt)
    if len(receipts) > 10:
        receipts = receipts[-10:]

    # Verify monotonic invariants
    if new_state.play_seconds < state.play_seconds:
        raise ValueError("play_seconds cannot decrease")

    final_state = new_state.model_copy(
        update={
            "revision": bumped_rev,
            "last_command_receipts": receipts,
        }
    )

    return final_state, final_receipt
