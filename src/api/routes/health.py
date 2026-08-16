"""Health check routes (LLM-01)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.config import Settings
from app.dependencies import get_settings
from domain.models.common import StrictModel
from llm.health import check_ollama_health

router = APIRouter(tags=["health"])


class ModelCapabilities(StrictModel):
    """Model capabilities status."""

    text: str = "not_configured"
    image: str = "not_configured"


class HealthResponse(StrictModel):
    """Health check response schema."""

    status: str = "ok"
    core: str = "ok"
    storage: str = "ok"
    models: ModelCapabilities = ModelCapabilities()


@router.get("/health", response_model=HealthResponse)
async def get_health(
    settings: Annotated[Settings, Depends(get_settings)],
    check_models: Annotated[bool, Query()] = False,
) -> HealthResponse:
    """Report application health and capabilities."""
    if not check_models:
        return HealthResponse(
            status="ok",
            core="ok",
            storage="ok",
            models=ModelCapabilities(),
        )

    # Perform live loopback inspection
    ollama_health = await check_ollama_health(
        ollama_url=settings.ollama_url,
        text_model=settings.model_text,
        image_model=settings.model_image,
        timeout=2.0,
    )

    return HealthResponse(
        status="ok",
        core="ok",
        storage="ok",
        models=ModelCapabilities(
            text=ollama_health.text_status.value,
            image=ollama_health.image_status.value,
        ),
    )
