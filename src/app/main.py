"""Application factory and main entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routes import (
    actions,
    assets,
    builder,
    campaigns,
    combat,
    health,
    party,
    plot,
    progression,
    saves,
)
from api.schemas.common import create_error_response
from app.config import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle."""
    # Startup: Initialize resources (HTTP clients, etc.)
    # Currently nothing needed for milestone 1E
    yield
    # Shutdown: Clean up resources
    pass


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Storymode API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Dependency injection state
    app.state.settings = settings

    # CORS configuration
    # Only allow explicit loopback origins by default
    origins = [
        "http://127.0.0.1",
        "http://localhost",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers for safe envelopes
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            code = "not_found"
        elif exc.status_code == 422:
            code = "validation_error"
        elif exc.status_code == 409:
            code = "conflict"
        elif exc.status_code == 503:
            code = "interpreter_not_configured"
        else:
            code = "http_error"
        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(code=code, message=str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=create_error_response(code="validation_error", message="Invalid request data"),
        )

    # Register routers
    app.include_router(health.router)
    app.include_router(campaigns.router, prefix="/api/v1")
    app.include_router(assets.router)
    app.include_router(builder.router, prefix="/api/v1")
    app.include_router(saves.router, prefix="/api/v1")
    app.include_router(actions.router, prefix="/api/v1")
    app.include_router(combat.router, prefix="/api/v1")
    app.include_router(party.router, prefix="/api/v1")
    app.include_router(progression.router, prefix="/api/v1")
    app.include_router(plot.router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        """Redirect root to interactive API documentation."""
        return RedirectResponse(url="/docs")

    return app
