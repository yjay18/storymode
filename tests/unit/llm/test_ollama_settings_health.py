"""Tests for Ollama settings validation and loopback capability health (LLM-01)."""

import httpx
import pytest

from app.config import Settings
from llm.health import (
    ModelCapabilityStatus,
    check_ollama_health,
    is_loopback_host,
    normalize_model_name,
    validate_ollama_url,
)

# ---------------------------------------------------------------------------
# Loopback Host & URL Validation Tests
# ---------------------------------------------------------------------------


def test_is_loopback_host() -> None:
    assert is_loopback_host("localhost")
    assert is_loopback_host("127.0.0.1")
    assert is_loopback_host("127.0.1.1")
    assert is_loopback_host("::1")
    assert is_loopback_host("[::1]")

    assert not is_loopback_host("example.com")
    assert not is_loopback_host("192.168.1.50")
    assert not is_loopback_host("10.0.0.1")
    assert not is_loopback_host("8.8.8.8")
    assert not is_loopback_host("0.0.0.0")


def test_validate_ollama_url_valid() -> None:
    assert validate_ollama_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434"
    assert validate_ollama_url("http://localhost:11434") == "http://localhost:11434"
    assert validate_ollama_url("http://[::1]:11434") == "http://[::1]:11434"


def test_validate_ollama_url_invalid_scheme() -> None:
    with pytest.raises(ValueError, match="scheme must be 'http'"):
        validate_ollama_url("https://localhost:11434")


def test_validate_ollama_url_remote_host() -> None:
    with pytest.raises(ValueError, match="host must be a local loopback"):
        validate_ollama_url("http://api.openai.com/v1")

    with pytest.raises(ValueError, match="host must be a local loopback"):
        validate_ollama_url("http://192.168.1.10:11434")


def test_validate_ollama_url_userinfo_and_query() -> None:
    with pytest.raises(ValueError, match="userinfo"):
        validate_ollama_url("http://user:pass@localhost:11434")

    with pytest.raises(ValueError, match="query"):
        validate_ollama_url("http://localhost:11434?param=value")

    with pytest.raises(ValueError, match="fragments"):
        validate_ollama_url("http://localhost:11434#hash")


def test_settings_validation() -> None:
    s = Settings(
        host="127.0.0.1",
        ollama_url="http://127.0.0.1:11434",
        model_text="llama3.1:8b",
        model_image="",
    )
    assert s.host == "127.0.0.1"
    assert s.ollama_url == "http://127.0.0.1:11434"

    with pytest.raises(ValueError):
        Settings(host="192.168.1.1")

    with pytest.raises(ValueError):
        Settings(ollama_url="https://cloud.ollama.ai")


def test_normalize_model_name() -> None:
    assert normalize_model_name("llama3.1:8b") == "llama3.1:8b"
    assert normalize_model_name("llama3.1") == "llama3.1:latest"
    assert normalize_model_name("") == ""


# ---------------------------------------------------------------------------
# Health Capability Inspection with Fake Transport
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_check_ollama_health_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(
            status_code=200,
            json={
                "models": [
                    {"name": "llama3.1:8b", "size": 4000000},
                    {"name": "sd-turbo:latest", "size": 2000000},
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        health = await check_ollama_health(
            ollama_url="http://127.0.0.1:11434",
            text_model="llama3.1:8b",
            image_model="sd-turbo",
            client=client,
        )

    assert health.reachable
    assert health.text_status == ModelCapabilityStatus.AVAILABLE
    assert health.image_status == ModelCapabilityStatus.AVAILABLE
    assert "llama3.1:8b" in health.available_models
    assert health.error_message is None


@pytest.mark.anyio
async def test_check_ollama_health_model_absent() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={"models": [{"name": "other-model:latest"}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        health = await check_ollama_health(
            ollama_url="http://127.0.0.1:11434",
            text_model="llama3.1:8b",
            image_model=None,
            client=client,
        )

    assert health.reachable
    assert health.text_status == ModelCapabilityStatus.ABSENT
    assert health.image_status == ModelCapabilityStatus.NOT_CONFIGURED


@pytest.mark.anyio
async def test_check_ollama_health_server_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=500, text="Internal server error")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        health = await check_ollama_health(
            ollama_url="http://127.0.0.1:11434",
            text_model="llama3.1:8b",
            client=client,
        )

    assert not health.reachable
    assert health.text_status == ModelCapabilityStatus.UNREACHABLE
    assert health.error_message is not None
    assert "500" in health.error_message


@pytest.mark.anyio
async def test_check_ollama_health_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        health = await check_ollama_health(
            ollama_url="http://127.0.0.1:11434",
            text_model="llama3.1:8b",
            client=client,
        )

    assert not health.reachable
    assert health.text_status == ModelCapabilityStatus.UNREACHABLE
    assert health.error_message is not None


@pytest.mark.anyio
async def test_check_ollama_health_remote_url_rejected_without_network() -> None:
    health = await check_ollama_health(
        ollama_url="http://remote.server.com",
        text_model="llama3.1:8b",
    )
    assert not health.reachable
    assert "host must be a local loopback" in (health.error_message or "")
