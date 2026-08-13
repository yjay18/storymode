"""Common API schemas and error envelopes."""

import uuid
from typing import Any
from domain.models.common import StrictModel


class ErrorDetail(StrictModel):
    """Detailed error information."""
    code: str
    message: str
    correlation_id: str


class ErrorResponse(StrictModel):
    """Safe error envelope."""
    error: ErrorDetail


def create_error_response(code: str, message: str) -> dict[str, Any]:
    """Helper to create a safe error response dictionary."""
    return ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            correlation_id=str(uuid.uuid4())
        )
    ).model_dump()
