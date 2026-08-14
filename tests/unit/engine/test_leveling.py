"""Tests for progression leveling and XP grant rules (PROG-01)."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.common import DisplayString, EntityId
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import CommandReceipt, RuntimeState
from domain.models.world_state import LocationState
from engine.progression.leveling import (
    calculate_level_from_xp,
    grant_xp,
    validate_xp_thresholds,
)
from engine.state.transition import apply_command

# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

_STATS = StatBlock(
    strength=10,
    dexterity=10,
    intelligence=10,
    charisma=10,
    constitution=10,
    wisdom=10,
)
_RES = ResourceValue(current=10, maximum=10)
_ZERO = ResourceValue(current=0, maximum=5)

_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 250,
    4: 500,
    5: 1000,
}


def _make_state(xp: int = 0, level: int = 1, tokens: int = 0) -> RuntimeState:
    player = PlayerState(
        id=EntityId("hero"),
        name=DisplayString("Hero"),
        background_id=EntityId("bg-1"),
        stats=_STATS,
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        mana_regen=2,
        speed=30,
        luck_current=0,
        luck_capacity=3,
        level=level,
        xp=xp,
        upgrade_tokens=tokens,
    )
    return RuntimeState(
        campaign_id=EntityId("camp"),
        campaign_version="1.0.0",
        campaign_fingerprint="fp",
        save_id=EntityId("save"),
        revision=0,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(protagonist_id=EntityId("hero")),
        location=LocationState(area_id=EntityId("area-1")),
        plot=PlotState(),
    )


# ---------------------------------------------------------------------------
# Threshold Validation & Defensive Tests
# ---------------------------------------------------------------------------


def test_validate_valid_table() -> None:
    validate_xp_thresholds(_THRESHOLDS)


def test_validate_empty_table_raises() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_xp_thresholds({})


def test_validate_missing_level_1_raises() -> None:
    with pytest.raises(ValueError, match="start at level 1"):
        validate_xp_thresholds({2: 100, 3: 200})


def test_validate_level_1_nonzero_xp_raises() -> None:
    with pytest.raises(ValueError, match="0 XP"):
        validate_xp_thresholds({1: 50, 2: 100})


def test_validate_non_contiguous_levels_raises() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        validate_xp_thresholds({1: 0, 2: 100, 4: 300})


def test_validate_non_increasing_xp_raises() -> None:
    with pytest.raises(ValueError, match="strictly increase"):
        validate_xp_thresholds({1: 0, 2: 100, 3: 100})

    with pytest.raises(ValueError, match="strictly increase"):
        validate_xp_thresholds({1: 0, 2: 100, 3: 50})


# ---------------------------------------------------------------------------
# Calculate Level from XP
# ---------------------------------------------------------------------------


def test_calculate_level_below_first_threshold() -> None:
    assert calculate_level_from_xp(0, _THRESHOLDS) == 1
    assert calculate_level_from_xp(99, _THRESHOLDS) == 1


def test_calculate_level_exact_threshold() -> None:
    assert calculate_level_from_xp(100, _THRESHOLDS) == 2
    assert calculate_level_from_xp(250, _THRESHOLDS) == 3


def test_calculate_level_above_max_threshold() -> None:
    assert calculate_level_from_xp(1000, _THRESHOLDS) == 5
    assert calculate_level_from_xp(5000, _THRESHOLDS) == 5


def test_calculate_level_negative_xp_raises() -> None:
    with pytest.raises(ValueError, match="negative"):
        calculate_level_from_xp(-10, _THRESHOLDS)


# ---------------------------------------------------------------------------
# Grant XP Tests
# ---------------------------------------------------------------------------


def test_grant_xp_below_threshold() -> None:
    state = _make_state(xp=0, level=1, tokens=0)
    new_state, result = grant_xp(state, 50, _THRESHOLDS)

    assert new_state.player.xp == 50
    assert new_state.player.level == 1
    assert new_state.player.upgrade_tokens == 0

    assert result.previous_xp == 0
    assert result.new_xp == 50
    assert result.previous_level == 1
    assert result.new_level == 1
    assert result.levels_gained == 0
    assert result.tokens_gained == 0
    assert result.total_tokens == 0


def test_grant_xp_exact_threshold() -> None:
    state = _make_state(xp=0, level=1, tokens=0)
    new_state, result = grant_xp(state, 100, _THRESHOLDS)

    assert new_state.player.xp == 100
    assert new_state.player.level == 2
    assert new_state.player.upgrade_tokens == 1

    assert result.levels_gained == 1
    assert result.tokens_gained == 1
    assert result.total_tokens == 1


def test_grant_xp_multiple_thresholds() -> None:
    state = _make_state(xp=0, level=1, tokens=0)
    new_state, result = grant_xp(state, 300, _THRESHOLDS)

    assert new_state.player.xp == 300
    assert new_state.player.level == 3
    assert new_state.player.upgrade_tokens == 2

    assert result.previous_level == 1
    assert result.new_level == 3
    assert result.levels_gained == 2
    assert result.tokens_gained == 2
    assert result.total_tokens == 2


def test_grant_xp_capped_at_max_level() -> None:
    state = _make_state(xp=0, level=1, tokens=0)
    new_state, result = grant_xp(state, 2000, _THRESHOLDS)

    assert new_state.player.xp == 2000
    assert new_state.player.level == 5
    assert new_state.player.upgrade_tokens == 4

    assert result.previous_level == 1
    assert result.new_level == 5
    assert result.levels_gained == 4
    assert result.tokens_gained == 4
    assert result.total_tokens == 4

    # Further XP grant while at max level does not grant more levels or tokens
    further_state, further_result = grant_xp(new_state, 500, _THRESHOLDS)
    assert further_state.player.xp == 2500
    assert further_state.player.level == 5
    assert further_state.player.upgrade_tokens == 4
    assert further_result.levels_gained == 0
    assert further_result.tokens_gained == 0


def test_grant_xp_negative_amount_raises() -> None:
    state = _make_state()
    with pytest.raises(ValueError, match="negative"):
        grant_xp(state, -50, _THRESHOLDS)


def test_grant_xp_input_unchanged() -> None:
    state = _make_state(xp=50, level=1, tokens=0)
    grant_xp(state, 100, _THRESHOLDS)

    assert state.player.xp == 50
    assert state.player.level == 1
    assert state.player.upgrade_tokens == 0


# ---------------------------------------------------------------------------
# Command-Layer Idempotency Integration Test
# ---------------------------------------------------------------------------


def test_grant_xp_idempotency_via_apply_command() -> None:
    state = _make_state(xp=0, level=1, tokens=0)

    def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
        updated, result = grant_xp(current_state, 100, _THRESHOLDS)
        receipt = CommandReceipt(
            command_id=EntityId("cmd-1"),
            canonical_request_hash="hash-123",
            committed_revision=0,
            result_kind=DisplayString("xp_grant"),
            safe_result_summary=DisplayString(f"Gained 100 XP, now Level {result.new_level}"),
        )
        return updated, receipt

    # First application
    state_after_1, receipt_1 = apply_command(
        state=state,
        expected_revision=0,
        command_id=EntityId("cmd-1"),
        canonical_request_hash="hash-123",
        mutation_fn=mutation,
    )
    assert receipt_1.committed_revision == 1
    assert state_after_1.revision == 1
    assert state_after_1.player.xp == 100
    assert state_after_1.player.level == 2
    assert state_after_1.player.upgrade_tokens == 1

    # Re-applying identical command_id + hash returns cached receipt and unmodified state
    state_after_2, receipt_2 = apply_command(
        state=state_after_1,
        expected_revision=1,
        command_id=EntityId("cmd-1"),
        canonical_request_hash="hash-123",
        mutation_fn=mutation,
    )
    assert state_after_2.revision == 1
    assert state_after_2.player.xp == 100
    assert state_after_2.player.level == 2
    assert state_after_2.player.upgrade_tokens == 1
    assert receipt_2.committed_revision == 1
