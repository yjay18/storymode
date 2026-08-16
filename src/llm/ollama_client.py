"""Bounded local Ollama HTTP client transport (LLM-02).

Guarantees:
- Enforces strict loopback base URL and loopback-only redirect targets.
- Bounded response byte limits on incoming payloads.
- Strict connect/read/write timeouts and cancellation support.
- Typed error hierarchy for connection, timeout, oversized, and schema errors.
- Never shells out; no game state or save imports.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import Field

from domain.models.common import FrozenModel
from llm.health import is_loopback_host, validate_ollama_url

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OllamaClientError(Exception):
    """Base exception for all Ollama transport and communication errors."""


class OllamaConnectionError(OllamaClientError):
    """Raised when connection to local Ollama fails or is refused."""


class OllamaTimeoutError(OllamaClientError):
    """Raised when an HTTP request to Ollama times out."""


class OllamaOversizedResponseError(OllamaClientError):
    """Raised when response body exceeds max_response_bytes."""


class OllamaInvalidResponseError(OllamaClientError):
    """Raised when response payload is malformed or invalid JSON."""


class OllamaModelNotFoundError(OllamaClientError):
    """Raised when the requested model is not found on the Ollama instance (HTTP 404)."""


class OllamaHttpError(OllamaClientError):
    """Raised when Ollama returns an unexpected HTTP status code."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChatMessage(FrozenModel):
    """A chat message in the Ollama conversation payload."""

    role: str
    content: str


class ChatOptions(FrozenModel):
    """Execution options for Ollama generation."""

    temperature: float = 0.0
    seed: int | None = None
    num_predict: int | None = None


class ChatResponse(FrozenModel):
    """Structured response from /api/chat."""

    model: str
    message: ChatMessage
    done: bool
    total_duration_ns: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    raw_json: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Client Implementation
# ---------------------------------------------------------------------------


class OllamaClient:
    """Bounded, loopback-only client for local Ollama server."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        client: httpx.AsyncClient | None = None,
        default_timeout: float = 30.0,
        max_response_bytes: int = 1024 * 1024,
    ) -> None:
        self.base_url = validate_ollama_url(base_url).rstrip("/")
        self.default_timeout = default_timeout
        self.max_response_bytes = max_response_bytes
        self._injected_client = client

    def _verify_redirect(self, response: httpx.Response) -> None:
        """Ensure any redirect target remains strictly on a loopback host."""
        if response.is_redirect and "location" in response.headers:
            target = response.headers["location"]
            parsed = urlparse(target)
            if parsed.hostname and not is_loopback_host(parsed.hostname):
                raise OllamaConnectionError(
                    f"Forbidden redirect to non-loopback host: '{parsed.hostname}'"
                )

    async def _read_bounded(self, response: httpx.Response) -> bytes:
        """Stream and accumulate response bytes up to max_response_bytes."""
        # Check Content-Length header if present
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > self.max_response_bytes:
            raise OllamaOversizedResponseError(
                f"Content-Length {content_length} exceeds limit of {self.max_response_bytes} bytes"
            )

        buffer = bytearray()
        async for chunk in response.aiter_bytes():
            buffer.extend(chunk)
            if len(buffer) > self.max_response_bytes:
                raise OllamaOversizedResponseError(
                    f"Response exceeded byte limit of {self.max_response_bytes} bytes"
                )
        return bytes(buffer)

    async def list_models(self, timeout: float | None = None) -> list[str]:
        """Fetch list of available model tags from /api/tags."""
        endpoint = f"{self.base_url}/api/tags"
        req_timeout = httpx.Timeout(timeout or self.default_timeout, connect=5.0)

        async def _do(c: httpx.AsyncClient) -> list[str]:
            try:
                resp = await c.get(endpoint, timeout=req_timeout, follow_redirects=False)
                self._verify_redirect(resp)
                if resp.status_code != 200:
                    raise OllamaHttpError(resp.status_code, resp.text)
                body = await self._read_bounded(resp)
                data = httpx.Response(200, content=body).json()
                if not isinstance(data, dict) or "models" not in data:
                    raise OllamaInvalidResponseError("Malformed tags response structure")
                return [
                    str(m["name"])
                    for m in data.get("models", [])
                    if isinstance(m, dict) and "name" in m
                ]
            except httpx.TimeoutException as e:
                raise OllamaTimeoutError(f"Request to {endpoint} timed out") from e
            except httpx.NetworkError as e:
                raise OllamaConnectionError(f"Failed to connect to Ollama at {endpoint}") from e

        if self._injected_client is not None:
            return await _do(self._injected_client)
        async with httpx.AsyncClient() as c:
            return await _do(c)

    async def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        format_json: bool = True,
        options: ChatOptions | None = None,
        timeout: float | None = None,
    ) -> ChatResponse:
        """Send a chat completion request to /api/chat with structured JSON output."""
        if not model or not model.strip():
            raise OllamaClientError("Model name cannot be empty")
        if not messages:
            raise OllamaClientError("Messages list cannot be empty")

        endpoint = f"{self.base_url}/api/chat"
        req_timeout = httpx.Timeout(timeout or self.default_timeout, connect=5.0)

        payload: dict[str, Any] = {
            "model": model.strip(),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }

        if format_json:
            payload["format"] = "json"

        if options is not None:
            opt_dict: dict[str, Any] = {"temperature": options.temperature}
            if options.seed is not None:
                opt_dict["seed"] = options.seed
            if options.num_predict is not None:
                opt_dict["num_predict"] = options.num_predict
            payload["options"] = opt_dict

        async def _do(c: httpx.AsyncClient) -> ChatResponse:
            try:
                resp = await c.post(
                    endpoint,
                    json=payload,
                    timeout=req_timeout,
                    follow_redirects=False,
                )
                self._verify_redirect(resp)

                if resp.status_code == 404:
                    raise OllamaModelNotFoundError(f"Model '{model}' not found on Ollama instance")
                if resp.status_code != 200:
                    raise OllamaHttpError(resp.status_code, resp.text)

                body = await self._read_bounded(resp)

                try:
                    data = httpx.Response(200, content=body).json()
                except Exception as e:
                    raise OllamaInvalidResponseError(
                        f"Failed to parse JSON response from Ollama: {e}"
                    ) from e

                if not isinstance(data, dict):
                    raise OllamaInvalidResponseError("Expected JSON object from /api/chat")

                msg_data = data.get("message")
                if not isinstance(msg_data, dict) or "content" not in msg_data:
                    raise OllamaInvalidResponseError(
                        "Missing or malformed 'message' object in Ollama response"
                    )

                return ChatResponse(
                    model=str(data.get("model", model)),
                    message=ChatMessage(
                        role=str(msg_data.get("role", "assistant")),
                        content=str(msg_data.get("content", "")),
                    ),
                    done=bool(data.get("done", True)),
                    total_duration_ns=data.get("total_duration"),
                    prompt_eval_count=data.get("prompt_eval_count"),
                    eval_count=data.get("eval_count"),
                    raw_json=data,
                )
            except httpx.TimeoutException as e:
                raise OllamaTimeoutError(f"Chat request to {endpoint} timed out") from e
            except httpx.NetworkError as e:
                raise OllamaConnectionError(f"Failed to connect to Ollama at {endpoint}") from e

        if self._injected_client is not None:
            return await _do(self._injected_client)
        async with httpx.AsyncClient() as c:
            return await _do(c)
