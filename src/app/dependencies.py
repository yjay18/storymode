"""Application dependency providers (LLM-09)."""

from typing import Any, cast

from fastapi import Request

from app.config import Settings
from engine.dice.ports import RandomSource
from llm.ollama_client import OllamaClient
from llm.orchestration.narrator import NarratorOrchestrator
from llm.orchestration.opportunity_planner import OpportunityPlannerAdapter


def get_settings(request: Request) -> Settings:
    """Provide application settings from app state."""
    return cast(Settings, request.app.state.settings)


def get_ollama_client(request: Request) -> OllamaClient:
    """Provide Ollama HTTP client from app state or construct from settings."""
    client = getattr(request.app.state, "ollama_client", None)
    if client is not None:
        return cast(OllamaClient, client)
    settings = get_settings(request)
    return OllamaClient(
        base_url=settings.ollama_url,
        default_timeout=settings.ollama_timeout_seconds,
        max_response_bytes=settings.ollama_max_response_bytes,
    )


def get_action_interpreter(request: Request) -> Any | None:
    """Provide action interpreter from app state if configured."""
    return getattr(request.app.state, "action_interpreter", None)


def get_narrator_orchestrator(request: Request) -> NarratorOrchestrator | None:
    """Provide narrator orchestrator from app state if configured."""
    return getattr(request.app.state, "narrator_orchestrator", None)


def get_opportunity_planner(request: Request) -> OpportunityPlannerAdapter | None:
    """Provide opportunity planner adapter from app state if configured."""
    return getattr(request.app.state, "opportunity_planner", None)


def get_random_source(request: Request) -> RandomSource:
    """Provide random source from app state or default to SecureRandomSource."""
    from engine.dice.secure import SecureRandomSource

    source = getattr(request.app.state, "random_source", None)
    if source is not None:
        return cast(RandomSource, source)
    return SecureRandomSource()
