"""Ollama loopback health inspection and capability reporting (LLM-01)."""

from __future__ import annotations

import enum
import ipaddress
from urllib.parse import urlparse

import httpx
from pydantic import Field

from domain.models.common import FrozenModel


class ModelCapabilityStatus(enum.StrEnum):
    """The capability status of an LLM model."""

    AVAILABLE = "available"
    ABSENT = "absent"
    NOT_CONFIGURED = "not_configured"
    UNKNOWN = "unknown"
    UNREACHABLE = "unreachable"


class OllamaHealthStatus(FrozenModel):
    """Health and model availability status for local Ollama instance."""

    reachable: bool
    text_model: str | None = None
    text_status: ModelCapabilityStatus = ModelCapabilityStatus.NOT_CONFIGURED
    image_model: str | None = None
    image_status: ModelCapabilityStatus = ModelCapabilityStatus.NOT_CONFIGURED
    available_models: list[str] = Field(default_factory=list)
    error_message: str | None = None


def is_loopback_host(host: str) -> bool:
    """Determine if a hostname or IP string is strictly a local loopback."""
    clean_host = host.strip("[]").lower()
    if clean_host == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(clean_host)
        return ip.is_loopback
    except ValueError:
        return False


def validate_ollama_url(url: str) -> str:
    """Validate that Ollama URL is http on a loopback host with no userinfo, query, or fragment.

    Raises ValueError if invalid.
    """
    if not url:
        raise ValueError("Ollama URL cannot be empty")

    parsed = urlparse(url)

    if parsed.scheme != "http":
        raise ValueError(f"Ollama URL scheme must be 'http', got '{parsed.scheme}'")

    if parsed.username or parsed.password:
        raise ValueError("Ollama URL must not contain userinfo/credentials")

    if parsed.query:
        raise ValueError("Ollama URL must not contain query parameters")

    if parsed.fragment:
        raise ValueError("Ollama URL must not contain fragments")

    if not parsed.hostname or not is_loopback_host(parsed.hostname):
        raise ValueError(
            f"Ollama URL host must be a local loopback (localhost or 127.0.0.1 or ::1), "
            f"got '{parsed.hostname}'"
        )

    return url


def normalize_model_name(name: str) -> str:
    """Normalize model tag for comparison, appending ':latest' if tag omitted."""
    stripped = name.strip()
    if not stripped:
        return ""
    if ":" not in stripped:
        return f"{stripped}:latest"
    return stripped


async def check_ollama_health(
    ollama_url: str,
    text_model: str | None = None,
    image_model: str | None = None,
    client: httpx.AsyncClient | None = None,
    timeout: float = 3.0,
) -> OllamaHealthStatus:
    """Query local Ollama /api/tags endpoint to check reachability and model availability.

    Guarantees:
    - Never mutates state or downloads models.
    - Uses strict loopback URL check.
    - Handles timeouts, connection errors, and malformed responses safely.
    """
    try:
        validated_url = validate_ollama_url(ollama_url)
    except ValueError as e:
        return OllamaHealthStatus(
            reachable=False,
            text_model=text_model,
            text_status=ModelCapabilityStatus.UNREACHABLE,
            image_model=image_model,
            image_status=ModelCapabilityStatus.UNREACHABLE,
            error_message=str(e),
        )

    endpoint = f"{validated_url.rstrip('/')}/api/tags"

    async def _fetch(c: httpx.AsyncClient) -> OllamaHealthStatus:
        try:
            resp = await c.get(endpoint, timeout=timeout)
            if resp.status_code != 200:
                return OllamaHealthStatus(
                    reachable=False,
                    text_model=text_model,
                    text_status=ModelCapabilityStatus.UNREACHABLE,
                    image_model=image_model,
                    image_status=ModelCapabilityStatus.UNREACHABLE,
                    error_message=f"HTTP {resp.status_code} from Ollama tags endpoint",
                )

            data = resp.json()
            if not isinstance(data, dict) or "models" not in data:
                return OllamaHealthStatus(
                    reachable=False,
                    text_model=text_model,
                    text_status=ModelCapabilityStatus.UNREACHABLE,
                    image_model=image_model,
                    image_status=ModelCapabilityStatus.UNREACHABLE,
                    error_message="Malformed response from Ollama tags endpoint",
                )

            raw_models = data.get("models", [])
            available_tags: list[str] = []
            for item in raw_models:
                if isinstance(item, dict) and "name" in item:
                    available_tags.append(str(item["name"]))

            # Normalized tags for comparison
            normalized_available = {normalize_model_name(t) for t in available_tags}

            # Check text model
            t_status = ModelCapabilityStatus.NOT_CONFIGURED
            if text_model and text_model.strip():
                if normalize_model_name(text_model) in normalized_available:
                    t_status = ModelCapabilityStatus.AVAILABLE
                else:
                    t_status = ModelCapabilityStatus.ABSENT

            # Check image model
            i_status = ModelCapabilityStatus.NOT_CONFIGURED
            if image_model and image_model.strip():
                if normalize_model_name(image_model) in normalized_available:
                    i_status = ModelCapabilityStatus.AVAILABLE
                else:
                    i_status = ModelCapabilityStatus.ABSENT

            return OllamaHealthStatus(
                reachable=True,
                text_model=text_model,
                text_status=t_status,
                image_model=image_model,
                image_status=i_status,
                available_models=available_tags,
                error_message=None,
            )

        except (httpx.TimeoutException, httpx.NetworkError, Exception) as e:
            return OllamaHealthStatus(
                reachable=False,
                text_model=text_model,
                text_status=ModelCapabilityStatus.UNREACHABLE,
                image_model=image_model,
                image_status=ModelCapabilityStatus.UNREACHABLE,
                error_message=str(e),
            )

    if client is not None:
        return await _fetch(client)

    async with httpx.AsyncClient() as new_client:
        return await _fetch(new_client)
