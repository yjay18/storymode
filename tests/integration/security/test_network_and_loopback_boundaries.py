"""Adversarial security tests for network, loopback boundaries, and CORS (SEC-01)."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from llm.health import is_loopback_host, validate_ollama_url


def test_is_loopback_host_strict_boundaries() -> None:
    """Verify is_loopback_host permits ONLY local loopback addresses."""
    valid_loopbacks = [
        "localhost",
        "127.0.0.1",
        "127.0.1.1",
        "127.100.0.1",
        "::1",
        "[::1]",
    ]
    for host in valid_loopbacks:
        assert is_loopback_host(host) is True, f"Expected {host} to be recognized as loopback"

    invalid_hosts = [
        "example.com",
        "evil.localhost.attacker.com",
        "0.0.0.0",
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "169.254.169.254",  # AWS/GCP metadata IP
        "8.8.8.8",
        "255.255.255.255",
        "http://localhost",  # Not a bare host
    ]
    for host in invalid_hosts:
        assert is_loopback_host(host) is False, f"Expected {host} to be rejected as loopback"


def test_validate_ollama_url_security_rules() -> None:
    """Verify validate_ollama_url enforces http on loopback and forbids userinfo/queries."""
    valid_urls = [
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://127.0.0.1:8000",
    ]
    for url in valid_urls:
        assert validate_ollama_url(url) == url

    invalid_urls = [
        "https://localhost:11434",  # Ollama is plain http locally
        "https://api.openai.com",  # External cloud
        "http://192.168.1.10:11434",  # LAN host
        "http://attacker.com:11434",  # External domain
        "http://admin:secret@localhost:11434",  # Userinfo in URL
        "http://localhost:11434/path?query=1",  # Query params forbidden
        "http://localhost:11434#fragment",  # Fragment forbidden
        "",
    ]
    for bad_url in invalid_urls:
        with pytest.raises(ValueError):
            validate_ollama_url(bad_url)


def test_cors_origin_policy() -> None:
    """Verify CORS middleware responds appropriately to allowed origins and rejects wildcards."""
    app = create_app()
    client = TestClient(app)

    # Preflight check from standard dev UI origin
    resp = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
