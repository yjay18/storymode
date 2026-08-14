from typing import cast

from fastapi import Request

from app.config import Settings
from engine.actions.protocols import ActionInterpreter
from engine.dice.ports import RandomSource


def get_settings(request: Request) -> Settings:
    """Provide application settings from app state."""
    return cast(Settings, request.app.state.settings)


def get_action_interpreter(request: Request) -> ActionInterpreter | None:
    """Provide action interpreter from app state if configured."""
    interpreter = getattr(request.app.state, "action_interpreter", None)
    return cast(ActionInterpreter | None, interpreter)


def get_random_source(request: Request) -> RandomSource:
    """Provide random source from app state or default to SecureRandomSource."""
    from engine.dice.secure import SecureRandomSource

    source = getattr(request.app.state, "random_source", None)
    if source is not None:
        return cast(RandomSource, source)
    return SecureRandomSource()
