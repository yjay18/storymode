"""Explicit local model setup and capability inspection script (SCRIPT-03).

Guarantees:
- Strictly enforces loopback URL validation.
- Inspects /api/tags without mutating unless --pull is explicitly requested.
- Outputs human-readable status reports.
- Returns exit code 0 when required models are present, 1 otherwise.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

import httpx

from llm.health import (
    ModelCapabilityStatus,
    check_ollama_health,
    validate_ollama_url,
)


def parse_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect and set up local Ollama models for Storymode.",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL (must be loopback, e.g. http://127.0.0.1:11434)",
    )
    parser.add_argument(
        "--model-text",
        default="llama3.1:8b",
        help="Required text model name (default: llama3.1:8b)",
    )
    parser.add_argument(
        "--model-image",
        default="stable-diffusion",
        help="Optional image model name (default: stable-diffusion)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check presence of required and optional models",
    )
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Pull missing models sequentially from local Ollama service",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds (default: 60.0)",
    )
    return parser.parse_args(args)


async def pull_model_async(
    url: str, model_name: str, client: httpx.AsyncClient | None = None, timeout: float = 300.0
) -> bool:
    """Pull a model via Ollama /api/pull endpoint asynchronously."""
    clean_url = validate_ollama_url(url).rstrip("/")
    pull_endpoint = f"{clean_url}/api/pull"

    print(f"[*] Pulling model '{model_name}' from {clean_url}...")
    try:
        if client is not None:
            resp = await client.post(pull_endpoint, json={"name": model_name, "stream": False})
        else:
            async with httpx.AsyncClient(timeout=timeout) as c:
                resp = await c.post(pull_endpoint, json={"name": model_name, "stream": False})

        if resp.status_code == 200:
            print(f"[+] Successfully pulled '{model_name}'.")
            return True
        print(f"[-] Failed to pull '{model_name}': HTTP {resp.status_code} - {resp.text}")
        return False
    except Exception as e:
        print(f"[-] Error pulling model '{model_name}': {e}")
        return False


def pull_model(
    url: str, model_name: str, client: httpx.AsyncClient | None = None, timeout: float = 300.0
) -> bool:
    """Pull a model via Ollama /api/pull endpoint synchronously."""
    return asyncio.run(pull_model_async(url, model_name, client=client, timeout=timeout))


async def run_setup(args: argparse.Namespace, client: httpx.AsyncClient | None = None) -> int:
    # 1. Enforce loopback validation
    try:
        url = validate_ollama_url(args.url)
    except ValueError as e:
        print(f"[!] Invalid Ollama URL: {e}", file=sys.stderr)
        return 1

    print("=== Storymode Local Model Inspection ===")
    print(f"Target URL: {url}")
    print(f"Required Text Model: {args.model_text}")
    print(f"Optional Image Model: {args.model_image}")
    print("-" * 40)

    # 2. Inspect health
    health = await check_ollama_health(
        ollama_url=url,
        text_model=args.model_text,
        image_model=args.model_image,
        client=client,
        timeout=args.timeout,
    )

    if not health.reachable:
        print(f"[!] Ollama is unavailable at {url}: {health.error_message}", file=sys.stderr)
        return 1

    print("[+] Ollama server is running and reachable.")
    print(f"Available local models: {', '.join(health.available_models) or 'None'}")

    text_present = health.text_status == ModelCapabilityStatus.AVAILABLE
    image_present = health.image_status == ModelCapabilityStatus.AVAILABLE

    print(
        f" - [{'+' if text_present else '-'}] Text model '{args.model_text}': "
        f"{'PRESENT' if text_present else 'MISSING'}"
    )
    print(
        f" - [{'+' if image_present else '-'}] Image model '{args.model_image}': "
        f"{'PRESENT' if image_present else 'MISSING'}"
    )

    # 3. Pull if requested
    if args.pull:
        if not text_present:
            await pull_model_async(url, args.model_text, client=client, timeout=args.timeout)
        if not image_present:
            await pull_model_async(url, args.model_image, client=client, timeout=args.timeout)

        # Re-check after pull
        health = await check_ollama_health(
            ollama_url=url,
            text_model=args.model_text,
            image_model=args.model_image,
            client=client,
            timeout=args.timeout,
        )
        text_present = health.text_status == ModelCapabilityStatus.AVAILABLE

    if not text_present:
        print(f"[!] Required model '{args.model_text}' is missing.", file=sys.stderr)
        return 1

    print("[+] All required models are present and ready.")
    return 0


def main(argv: Sequence[str] | None = None, client: httpx.AsyncClient | None = None) -> int:
    args = parse_args(argv)
    return asyncio.run(run_setup(args, client=client))


if __name__ == "__main__":
    sys.exit(main())
