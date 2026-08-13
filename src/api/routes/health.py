"""Health check routes."""

from fastapi import APIRouter
from domain.models.common import StrictModel

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
def get_health() -> HealthResponse:
    """Report application health and capabilities."""
    return HealthResponse()
