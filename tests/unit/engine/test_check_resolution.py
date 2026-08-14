"""Tests for check resolution."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.check_state import CheckOutcomes, PendingCheck
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.skill import EffectDefinition, EffectKind
from domain.models.world_state import LocationState
from engine.actions.resolution import CheckResolver
from engine.dice.testing import ScriptedRandomSource


@pytest.fixture
def base_state() -> RuntimeState:
    player = PlayerState(
        id="player-1",
        name="Hero",
        background_id="bg-1",
        stats=StatBlock(
            strength=10, dexterity=10, intelligence=10, charisma=10, constitution=10, wisdom=10
        ),
        hp=ResourceValue(current=5, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=5, maximum=5),
        mana_regen=1,
        speed=30,
        luck_capacity=3,
        luck_current=2,
    )
    return RuntimeState(
        campaign_id="camp-1",
        campaign_version="1.0.0",
        campaign_fingerprint="abc",
        save_id="save-1",
        revision=1,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(protagonist_id="player-1"),
        location=LocationState(area_id="area-1"),
        plot=PlotState(),
    )


def test_resolve_success_with_roll(base_state: RuntimeState) -> None:
    # final_dc is 12. roll 14 -> standard success
    outcomes = CheckOutcomes(
        natural_1=[],
        low=[],
        strong=[],
        natural_20=[],
        standard=[EffectDefinition(effect_id="eff-heal", kind=EffectKind.HEAL, magnitude=2)],
    )

    check = PendingCheck(
        check_id="chk-1",
        source_command_id="cmd-1",
        source_revision=1,
        original_input="Jump",
        resolved_operation="investigate",
        actor_id="player-1",
        target_ids=["player-1"],
        semantic_difficulty="standard",
        base_dc=12,
        difficulty_adjustment=0,
        final_dc=12,
        stakes="Fall",
        allowed_outcomes=outcomes,
    )
    state = base_state.model_copy(update={"pending_check": check})

    dice = ScriptedRandomSource([14])
    resolver = CheckResolver(dice)

    new_state, roll, band, effects = resolver.resolve_check(state, use_luck=False)

    assert roll == 14
    assert band == "standard"
    assert len(effects) == 1
    assert effects[0].kind == EffectKind.HEAL
    assert new_state.pending_check is None
    assert new_state.player.hp.current == 7  # 5 + 2


def test_resolve_with_luck(base_state: RuntimeState) -> None:
    # Use luck should force 20 and deduct luck
    outcomes = CheckOutcomes(
        natural_1=[],
        low=[],
        standard=[],
        strong=[],
        natural_20=[EffectDefinition(effect_id="eff-heal", kind=EffectKind.HEAL, magnitude=5)],
    )

    check = PendingCheck(
        check_id="chk-1",
        source_command_id="cmd-1",
        source_revision=1,
        original_input="Jump",
        resolved_operation="investigate",
        actor_id="player-1",
        target_ids=["player-1"],
        semantic_difficulty="standard",
        base_dc=12,
        difficulty_adjustment=0,
        final_dc=12,
        stakes="Fall",
        allowed_outcomes=outcomes,
    )
    state = base_state.model_copy(update={"pending_check": check})
    state = state.model_copy(update={"player": state.player.model_copy(update={"luck_current": 1})})

    dice = ScriptedRandomSource([1])  # normally would fail
    resolver = CheckResolver(dice)

    new_state, roll, band, _effects = resolver.resolve_check(state, use_luck=True)

    assert roll == 20
    assert band == "natural_20"
    assert new_state.player.luck_current == 0
    assert new_state.player.hp.current == 10


def test_resolve_not_enough_luck(base_state: RuntimeState) -> None:
    check = PendingCheck(
        check_id="chk-1",
        source_command_id="cmd-1",
        source_revision=1,
        original_input="Jump",
        resolved_operation="investigate",
        actor_id="player-1",
        target_ids=["player-1"],
        semantic_difficulty="standard",
        base_dc=12,
        difficulty_adjustment=0,
        final_dc=12,
        stakes="Fall",
        allowed_outcomes=CheckOutcomes(natural_1=[], low=[], standard=[], strong=[], natural_20=[]),
    )
    state = base_state.model_copy(update={"pending_check": check})
    state = state.model_copy(update={"player": state.player.model_copy(update={"luck_current": 0})})

    dice = ScriptedRandomSource([10])
    resolver = CheckResolver(dice)

    with pytest.raises(ValueError, match="Not enough luck"):
        resolver.resolve_check(state, use_luck=True)


def test_resolve_no_pending_check(base_state: RuntimeState) -> None:
    dice = ScriptedRandomSource([10])
    resolver = CheckResolver(dice)

    with pytest.raises(ValueError, match="No active pending check"):
        resolver.resolve_check(base_state, use_luck=False)
