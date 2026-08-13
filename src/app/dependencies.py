"""Dependency injection setup."""

from fastapi import Request
from app.config import Settings

def get_settings(request: Request) -> Settings:
    """Provide application settings from app state."""
    return request.app.state.settings
