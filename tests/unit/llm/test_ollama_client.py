"""Unit tests for bounded Ollama HTTP client transport (LLM-02)."""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from llm.ollama_client import (
    ChatMessage,
    ChatOptions,
    OllamaClient,
    OllamaClientError,
    OllamaConnectionError,
    OllamaHttpError,
    OllamaInvalidResponseError,
    OllamaModelNotFoundError,
    OllamaOversizedResponseError,
    OllamaTimeoutError,
)

# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------


def _make_mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> OllamaClient:
    transport = httpx.MockTransport(handler)
    mock_http = httpx.AsyncClient(transport=transport)
    return OllamaClient(
        base_url="http://127.0.0.1:11434",
        client=mock_http,
        default_timeout=5.0,
        max_response_bytes=1024,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_chat_success_and_payload_structure() -> None:
    captured_request: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request["url"] = str(request.url)
        captured_request["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            status_code=200,
            json={
                "model": "llama3.1:8b",
                "message": {
                    "role": "assistant",
                    "content": '{"action_proposal": {"schema_version": 1}}',
                },
                "done": True,
                "total_duration": 150000000,
                "prompt_eval_count": 250,
                "eval_count": 45,
            },
        )

    client = _make_mock_client(handler)
    messages = [
        ChatMessage(role="system", content="You are a parser."),
        ChatMessage(role="user", content="Attack the goblin."),
    ]
    options = ChatOptions(temperature=0.0, seed=42, num_predict=128)

    response = await client.chat(
        model="llama3.1:8b",
        messages=messages,
        format_json=True,
        options=options,
    )

    assert response.model == "llama3.1:8b"
    assert response.message.role == "assistant"
    assert "action_proposal" in response.message.content
    assert response.done is True
    assert response.eval_count == 45

    # Verify exact payload sent
    assert captured_request["url"] == "http://127.0.0.1:11434/api/chat"
    body = captured_request["body"]
    assert body["model"] == "llama3.1:8b"
    assert body["format"] == "json"
    assert body["stream"] is False
    assert len(body["messages"]) == 2
    assert body["options"]["seed"] == 42
    assert body["options"]["temperature"] == 0.0


@pytest.mark.anyio
async def test_list_models_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(
            status_code=200,
            json={
                "models": [
                    {"name": "llama3.1:8b"},
                    {"name": "mistral:7b"},
                ]
            },
        )

    client = _make_mock_client(handler)
    models = await client.list_models()
    assert models == ["llama3.1:8b", "mistral:7b"]


@pytest.mark.anyio
async def test_chat_empty_model_or_messages_raises() -> None:
    client = _make_mock_client(lambda r: httpx.Response(200, json={}))

    with pytest.raises(OllamaClientError, match="Model name cannot be empty"):
        await client.chat(model="", messages=[ChatMessage(role="user", content="hi")])

    with pytest.raises(OllamaClientError, match="Messages list cannot be empty"):
        await client.chat(model="llama3.1:8b", messages=[])


@pytest.mark.anyio
async def test_chat_model_not_found_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=404, text="model not found")

    client = _make_mock_client(handler)
    with pytest.raises(OllamaModelNotFoundError, match="Model 'unknown:latest' not found"):
        await client.chat(
            model="unknown:latest",
            messages=[ChatMessage(role="user", content="hi")],
        )


@pytest.mark.anyio
async def test_chat_server_error_500() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=500, text="internal crash")

    client = _make_mock_client(handler)
    with pytest.raises(OllamaHttpError, match="HTTP 500"):
        await client.chat(
            model="llama3.1:8b",
            messages=[ChatMessage(role="user", content="hi")],
        )


@pytest.mark.anyio
async def test_chat_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    client = _make_mock_client(handler)
    with pytest.raises(OllamaTimeoutError, match="timed out"):
        await client.chat(
            model="llama3.1:8b",
            messages=[ChatMessage(role="user", content="hi")],
        )


@pytest.mark.anyio
async def test_chat_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    client = _make_mock_client(handler)
    with pytest.raises(OllamaConnectionError, match="Failed to connect"):
        await client.chat(
            model="llama3.1:8b",
            messages=[ChatMessage(role="user", content="hi")],
        )


@pytest.mark.anyio
async def test_chat_oversized_response_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        huge_payload = {"message": {"role": "assistant", "content": "x" * 5000}}
        return httpx.Response(status_code=200, json=huge_payload)

    # max_response_bytes is 1024
    client = _make_mock_client(handler)
    with pytest.raises(OllamaOversizedResponseError, match=r"exceed.*limit"):
        await client.chat(
            model="llama3.1:8b",
            messages=[ChatMessage(role="user", content="hi")],
        )


@pytest.mark.anyio
async def test_chat_malformed_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, content=b"this is not json {")

    client = _make_mock_client(handler)
    with pytest.raises(OllamaInvalidResponseError, match="Failed to parse JSON"):
        await client.chat(
            model="llama3.1:8b",
            messages=[ChatMessage(role="user", content="hi")],
        )


@pytest.mark.anyio
async def test_chat_missing_message_field() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"done": True})

    client = _make_mock_client(handler)
    with pytest.raises(OllamaInvalidResponseError, match="Missing or malformed 'message'"):
        await client.chat(
            model="llama3.1:8b",
            messages=[ChatMessage(role="user", content="hi")],
        )


@pytest.mark.anyio
async def test_redirect_to_remote_host_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=302,
            headers={"location": "http://evil-attacker.com/steal"},
        )

    client = _make_mock_client(handler)
    with pytest.raises(OllamaConnectionError, match="Forbidden redirect to non-loopback"):
        await client.chat(
            model="llama3.1:8b",
            messages=[ChatMessage(role="user", content="hi")],
        )


def test_no_game_state_or_subprocess_imports() -> None:
    import inspect

    import llm.ollama_client as client_mod

    source = inspect.getsource(client_mod)
    assert "subprocess" not in source
    assert "domain.models.runtime_state" not in source
    assert "domain.models.combat_state" not in source
    assert "domain.models.plot_state" not in source
