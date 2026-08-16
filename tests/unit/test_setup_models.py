"""Unit tests for setup_models script (SCRIPT-03)."""

import httpx
import pytest
from scripts.setup_models import main, parse_args, pull_model


def test_parse_args_defaults() -> None:
    args = parse_args([])
    assert args.url == "http://127.0.0.1:11434"
    assert args.model_text == "llama3.1:8b"
    assert args.model_image == "stable-diffusion"
    assert args.pull is False


def test_main_rejects_non_loopback_url(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--url", "http://evil.com:11434"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Invalid Ollama URL" in captured.err


def test_main_healthy_when_models_present() -> None:
    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                status_code=200,
                json={
                    "models": [
                        {"name": "llama3.1:8b"},
                        {"name": "stable-diffusion"},
                    ]
                },
            )
        return httpx.Response(status_code=404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    code = main(
        ["--url", "http://127.0.0.1:11434", "--model-text", "llama3.1:8b"], client=mock_client
    )
    assert code == 0


def test_main_fails_when_required_model_missing(capsys: pytest.CaptureFixture[str]) -> None:
    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                status_code=200,
                json={"models": []},
            )
        return httpx.Response(status_code=404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    code = main(
        ["--url", "http://127.0.0.1:11434", "--model-text", "llama3.1:8b"], client=mock_client
    )
    assert code == 1
    captured = capsys.readouterr()
    assert "Required model 'llama3.1:8b' is missing" in captured.err


def test_pull_model_success() -> None:
    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/pull":
            return httpx.Response(status_code=200, json={"status": "success"})
        return httpx.Response(status_code=404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    success = pull_model("http://127.0.0.1:11434", "llama3.1:8b", client=mock_client)
    assert success is True
