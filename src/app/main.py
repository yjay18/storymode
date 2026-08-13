"""Application factory and main entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings, get_settings
from api.routes import health
from api.schemas.common import create_error_response


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
        code = "not_found" if exc.status_code == 404 else "http_error"
        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(code=code, message=str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=create_error_response(code="validation_error", message="Invalid request data"),
        )

    # Register routers
    app.include_router(health.router)

    return app
