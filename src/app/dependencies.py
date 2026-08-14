"""Dependency injection setup."""

from typing import cast
from fastapi import Request

from app.config import Settings


def get_settings(request: Request) -> Settings:
    """Provide application settings from app state."""
    return cast(Settings, request.app.state.settings)
