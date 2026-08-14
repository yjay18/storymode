"""Tests for party membership rules (PARTY-01)."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.combat_state import CombatPhase, CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.models.party_state import CompanionRuntimeState, LifeState, PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState, NpcOverride
from engine.progression.party import activate, deactivate, leave, recruit

# ---------------------------------------------------------------------------
# Minimal state factory
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


def _base_state() -> RuntimeState:
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


def _comp(
    cid: str = "comp-1", *, alive: bool = True, available: bool = True
) -> CompanionRuntimeState:
    return CompanionRuntimeState(
        id=EntityId(cid),
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        life_state=LifeState.ALIVE if alive else LifeState.DEAD,
        is_available=available if alive else False,
    )


def _with_comp(comp: CompanionRuntimeState, *, active: bool = False) -> RuntimeState:
    state = _base_state()
    new_party = state.party.model_copy(
        update={
            "companions": {comp.id: comp},
            "active_companion_ids": [comp.id] if active else [],
        }
    )
    return state.model_copy(update={"party": new_party})


def _with_combat(state: RuntimeState) -> RuntimeState:
    from domain.models.combat_state import CombatParticipant

    combat = CombatState(
        encounter_id=EntityId("enc"),
        phase=CombatPhase.ACTIVE,
        round=1,
        order=[EntityId("hero")],
        current_index=0,
        participants={
            EntityId("hero"): CombatParticipant(
                hp=_RES,
                armour=_ZERO,
                mana=_RES,
                side=ParticipantSide.PARTY,
            )
        },
    )
    return state.model_copy(update={"combat": combat})


# ---------------------------------------------------------------------------
# recruit
# ---------------------------------------------------------------------------


def test_recruit_adds_companion() -> None:
    state = _base_state()
    comp = _comp()
    new_state = recruit(state, comp.id, comp)
    assert comp.id in new_state.party.companions
    assert comp.id not in new_state.party.active_companion_ids


def test_recruit_already_recruited_raises() -> None:
    comp = _comp()
    with pytest.raises(ValueError, match="already recruited"):
        recruit(_with_comp(comp), comp.id, comp)


def test_recruit_dead_raises() -> None:
    dead = _comp(alive=False)
    with pytest.raises(ValueError, match="dead"):
        recruit(_base_state(), dead.id, dead)


def test_recruit_unavailable_raises() -> None:
    unavail = _comp(available=False)
    with pytest.raises(ValueError, match="not available"):
        recruit(_base_state(), unavail.id, unavail)


def test_recruit_during_combat_raises() -> None:
    comp = _comp()
    with pytest.raises(ValueError, match="combat"):
        recruit(_with_combat(_base_state()), comp.id, comp)


# ---------------------------------------------------------------------------
# activate
# ---------------------------------------------------------------------------


def test_activate_moves_to_active() -> None:
    comp = _comp()
    new_state = activate(_with_comp(comp), comp.id)
    assert comp.id in new_state.party.active_companion_ids


def test_activate_already_active_raises() -> None:
    comp = _comp()
    with pytest.raises(ValueError, match="already active"):
        activate(_with_comp(comp, active=True), comp.id)


def test_activate_fourth_raises() -> None:
    state = _base_state()
    comps = [_comp(f"cmp-{i}") for i in range(4)]
    new_party = state.party.model_copy(
        update={
            "companions": {c.id: c for c in comps},
            "active_companion_ids": [c.id for c in comps[:3]],
        }
    )
    state = state.model_copy(update={"party": new_party})
    with pytest.raises(ValueError, match="maximum size"):
        activate(state, comps[3].id)


def test_activate_not_recruited_raises() -> None:
    with pytest.raises(ValueError, match="not recruited"):
        activate(_base_state(), EntityId("ghost"))


def test_activate_dead_raises() -> None:
    dead = _comp(alive=False)
    state = _base_state()
    new_party = state.party.model_copy(update={"companions": {dead.id: dead}})
    state = state.model_copy(update={"party": new_party})
    with pytest.raises(ValueError, match="not alive"):
        activate(state, dead.id)


def test_activate_remote_companion_raises() -> None:
    comp = _comp()
    state = _with_comp(comp)
    override = NpcOverride(location_area_id=EntityId("other-area"))
    state = state.model_copy(update={"npc_overrides": {comp.id: override}})
    with pytest.raises(ValueError, match="not in the current area"):
        activate(state, comp.id)


def test_activate_hostile_raises() -> None:
    comp = _comp()
    state = _with_comp(comp)
    state = state.model_copy(
        update={"npc_overrides": {comp.id: NpcOverride(disposition="hostile")}}
    )
    with pytest.raises(ValueError, match="hostile"):
        activate(state, comp.id)


def test_activate_during_combat_raises() -> None:
    comp = _comp()
    with pytest.raises(ValueError, match="combat"):
        activate(_with_combat(_with_comp(comp)), comp.id)


# ---------------------------------------------------------------------------
# deactivate
# ---------------------------------------------------------------------------


def test_deactivate_removes_from_active_keeps_recruited() -> None:
    comp = _comp()
    new_state = deactivate(_with_comp(comp, active=True), comp.id)
    assert comp.id not in new_state.party.active_companion_ids
    assert comp.id in new_state.party.companions


def test_deactivate_not_active_raises() -> None:
    comp = _comp()
    with pytest.raises(ValueError, match="not active"):
        deactivate(_with_comp(comp), comp.id)


def test_deactivate_during_combat_raises() -> None:
    comp = _comp()
    with pytest.raises(ValueError, match="combat"):
        deactivate(_with_combat(_with_comp(comp, active=True)), comp.id)


# ---------------------------------------------------------------------------
# leave
# ---------------------------------------------------------------------------


def test_leave_removes_from_both_maps() -> None:
    comp = _comp()
    new_state = leave(_with_comp(comp, active=True), comp.id)
    assert comp.id not in new_state.party.companions
    assert comp.id not in new_state.party.active_companion_ids


def test_leave_not_recruited_raises() -> None:
    with pytest.raises(ValueError, match="not recruited"):
        leave(_base_state(), EntityId("ghost"))


def test_leave_during_combat_raises_by_default() -> None:
    comp = _comp()
    with pytest.raises(ValueError, match="combat"):
        leave(_with_combat(_with_comp(comp, active=True)), comp.id)


def test_leave_during_combat_allowed_with_flag() -> None:
    comp = _comp()
    new_state = leave(
        _with_combat(_with_comp(comp, active=True)), comp.id, allow_during_combat=True
    )
    assert comp.id not in new_state.party.companions


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


def test_no_input_mutation() -> None:
    state = _base_state()
    original = dict(state.party.companions)
    recruit(state, EntityId("comp-2"), _comp("comp-2"))
    assert state.party.companions == original
