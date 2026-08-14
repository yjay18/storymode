"""Party membership engine — recruit, activate, deactivate, leave."""

from __future__ import annotations

from domain.models.common import DisplayString, EntityId
from domain.models.party_state import CompanionRuntimeState, LifeState
from domain.models.runtime_state import RuntimeState


def _companion_or_raise(state: RuntimeState, companion_id: EntityId) -> CompanionRuntimeState:
    comp = state.party.companions.get(companion_id)
    if comp is None:
        raise ValueError(f"companion {companion_id} is not recruited")
    return comp


def _disposition(state: RuntimeState, companion_id: EntityId) -> DisplayString:
    override = state.npc_overrides.get(companion_id)
    if override and override.disposition is not None:
        return override.disposition
    return DisplayString("neutral")


def recruit(
    state: RuntimeState,
    companion_id: EntityId,
    initial_state: CompanionRuntimeState,
) -> RuntimeState:
    """Add a companion to the companions map (not yet active).

    Raises ValueError if:
    - companion is already recruited
    - protagonist is in combat
    - companion is dead or unavailable
    """
    if state.combat is not None:
        raise ValueError("cannot recruit during combat")
    if companion_id in state.party.companions:
        raise ValueError(f"companion {companion_id} is already recruited")
    if initial_state.life_state == LifeState.DEAD:
        raise ValueError("cannot recruit a dead companion")
    if not initial_state.is_available:
        raise ValueError("companion is not available for recruitment")

    new_companions = {**state.party.companions, companion_id: initial_state}
    new_party = state.party.model_copy(update={"companions": new_companions})
    return state.model_copy(update={"party": new_party})


def activate(state: RuntimeState, companion_id: EntityId) -> RuntimeState:
    """Move a recruited companion into the active party (max 3).

    Raises ValueError if any guard fails.
    """
    if state.combat is not None:
        raise ValueError("cannot change party during combat")

    comp = _companion_or_raise(state, companion_id)

    if companion_id in state.party.active_companion_ids:
        raise ValueError(f"companion {companion_id} is already active")
    if len(state.party.active_companion_ids) >= 3:
        raise ValueError("party is already at maximum size (3)")
    if comp.life_state != LifeState.ALIVE:
        raise ValueError(f"companion {companion_id} is not alive ({comp.life_state})")
    if not comp.is_available:
        raise ValueError(f"companion {companion_id} is not available")

    # Co-location: companion must be in the same area or have no override (home area used at
    # recruit time — actual location join is authoring responsibility; we check the NPC override).
    override = state.npc_overrides.get(companion_id)
    if (
        override
        and override.location_area_id is not None
        and override.location_area_id != state.location.area_id
    ):
        raise ValueError(f"companion {companion_id} is not in the current area")

    disp = _disposition(state, companion_id)
    if disp in ("hostile", "enemy"):
        raise ValueError(f"companion {companion_id} is hostile")

    new_active = [*state.party.active_companion_ids, companion_id]
    new_party = state.party.model_copy(update={"active_companion_ids": new_active})
    return state.model_copy(update={"party": new_party})


def deactivate(state: RuntimeState, companion_id: EntityId) -> RuntimeState:
    """Remove a companion from the active list but keep them recruited.

    Raises ValueError if not active or in combat.
    """
    if state.combat is not None:
        raise ValueError("cannot change party during combat")
    if companion_id not in state.party.active_companion_ids:
        raise ValueError(f"companion {companion_id} is not active")

    new_active = [c for c in state.party.active_companion_ids if c != companion_id]
    new_party = state.party.model_copy(update={"active_companion_ids": new_active})
    return state.model_copy(update={"party": new_party})


def leave(
    state: RuntimeState,
    companion_id: EntityId,
    *,
    allow_during_combat: bool = False,
) -> RuntimeState:
    """Remove a companion from the party entirely (recruited + active maps).

    Use allow_during_combat=True only for authored forced-departure consequences.
    Raises ValueError if companion is not recruited.
    """
    if state.combat is not None and not allow_during_combat:
        raise ValueError("cannot remove companion during combat")

    _companion_or_raise(state, companion_id)

    new_active = [c for c in state.party.active_companion_ids if c != companion_id]
    new_companions = {k: v for k, v in state.party.companions.items() if k != companion_id}
    new_party = state.party.model_copy(
        update={"active_companion_ids": new_active, "companions": new_companions}
    )
    return state.model_copy(update={"party": new_party})
