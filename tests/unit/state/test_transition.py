"""Tests for state transition."""

from pathlib import Path

import pytest

from domain.models.common import DisplayString, EntityId
from domain.models.runtime_state import CommandReceipt, RuntimeState
from engine.state.errors import IdempotentCommandError, StaleRevisionError
from engine.state.transition import apply_command


@pytest.fixture
def mock_state() -> RuntimeState:
    """Load the valid state fixture."""
    path = Path("tests/fixtures/state/valid_state.json")
    if not path.exists():
        pytest.skip("Fixture not generated yet")
    return RuntimeState.model_validate_json(path.read_text())


def mock_mutation(state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
    receipt = CommandReceipt(
        command_id=EntityId("dummy"),
        canonical_request_hash="dummy",
        committed_revision=0,
        result_kind=DisplayString("success"),
        safe_result_summary=DisplayString("did a thing"),
    )
    # just return the state as is, logic will copy it
    return state, receipt


def mock_mutation_decreasing_playtime(state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
    receipt = CommandReceipt(
        command_id=EntityId("dummy"),
        canonical_request_hash="dummy",
        committed_revision=0,
        result_kind=DisplayString("success"),
        safe_result_summary=DisplayString("did a thing"),
    )
    new_state = state.model_copy(update={"play_seconds": -1})
    return new_state, receipt


def test_apply_command_success(mock_state: RuntimeState) -> None:
    original_rev = mock_state.revision
    new_state, receipt = apply_command(
        mock_state,
        expected_revision=original_rev,
        command_id=EntityId("cmd-new"),
        canonical_request_hash="hash-new",
        mutation_fn=mock_mutation,
    )

    assert new_state.revision == original_rev + 1
    assert receipt.committed_revision == original_rev + 1
    assert receipt.command_id == "cmd-new"
    assert receipt.canonical_request_hash == "hash-new"

    # Receipt should be appended
    assert len(new_state.last_command_receipts) == len(mock_state.last_command_receipts) + 1
    assert new_state.last_command_receipts[-1] == receipt


def test_apply_command_stale_revision(mock_state: RuntimeState) -> None:
    with pytest.raises(StaleRevisionError):
        apply_command(
            mock_state,
            expected_revision=mock_state.revision - 1,
            command_id=EntityId("cmd-new"),
            canonical_request_hash="hash-new",
            mutation_fn=mock_mutation,
        )


def test_apply_command_idempotent(mock_state: RuntimeState) -> None:
    # First apply a command
    state1, receipt1 = apply_command(
        mock_state,
        expected_revision=mock_state.revision,
        command_id=EntityId("cmd-1"),
        canonical_request_hash="hash-1",
        mutation_fn=mock_mutation,
    )

    # Now try to apply the exact same command on the new state
    state2, receipt2 = apply_command(
        state1,
        expected_revision=state1.revision,
        command_id=EntityId("cmd-1"),
        canonical_request_hash="hash-1",
        mutation_fn=mock_mutation,
    )

    # Should return original state and receipt
    assert state2 is state1
    assert receipt2 == receipt1


def test_apply_command_conflict(mock_state: RuntimeState) -> None:
    # First apply a command
    state1, _receipt1 = apply_command(
        mock_state,
        expected_revision=mock_state.revision,
        command_id=EntityId("cmd-1"),
        canonical_request_hash="hash-1",
        mutation_fn=mock_mutation,
    )

    # Now try to apply the same command ID but different hash
    with pytest.raises(IdempotentCommandError):
        apply_command(
            state1,
            expected_revision=state1.revision,
            command_id=EntityId("cmd-1"),
            canonical_request_hash="hash-2",
            mutation_fn=mock_mutation,
        )


def test_apply_command_monotonic_playtime(mock_state: RuntimeState) -> None:
    with pytest.raises(ValueError, match="play_seconds cannot decrease"):
        apply_command(
            mock_state,
            expected_revision=mock_state.revision,
            command_id=EntityId("cmd-1"),
            canonical_request_hash="hash-1",
            mutation_fn=mock_mutation_decreasing_playtime,
        )


def test_apply_command_rotates_receipts(mock_state: RuntimeState) -> None:
    # Apply 15 commands
    state = mock_state
    for i in range(15):
        state, _ = apply_command(
            state,
            expected_revision=state.revision,
            command_id=EntityId(f"cmd-{i}"),
            canonical_request_hash="hash",
            mutation_fn=mock_mutation,
        )

    # Should keep exactly 10 receipts
    assert len(state.last_command_receipts) == 10
    # The first receipt should be cmd-5
    assert state.last_command_receipts[0].command_id == "cmd-5"
    assert state.last_command_receipts[-1].command_id == "cmd-14"
