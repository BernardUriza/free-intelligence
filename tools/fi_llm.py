#!/usr/bin/env python3
"""
Free Intelligence - LLM CLI

Command-line interface for LLM generation via HTTP endpoint or direct adapter.

File: tools/fi_llm.py
Created: 2025-10-29
Card: FI-CORE-FEAT-001

Usage:
  fi-llm --provider ollama --model qwen2:7b --prompt prompt.txt [--system sys.txt] [--json]
  fi-llm --provider claude --model claude-3-5-sonnet-20241022 --prompt "Hello" --json
  fi-llm --provider ollama --model qwen2:7b --prompt prompt.txt --direct

Options:
  --provider    Provider: ollama or claude
  --model       Model identifier
  --prompt      Prompt text or file path
  --system      System prompt text or file path (optional)
  --json        Output as JSON
  --direct      Use adapter directly (bypass HTTP endpoint)
  --endpoint    HTTP endpoint URL (default: http://127.0.0.1:9001)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests


def read_input(value: str) -> str:
    """Read input from file or use as literal string."""
    path = Path(value)
    if path.exists() and path.is_file():
        return path.read_text().strip()
    return value


def call_http_endpoint(
    provider: str,
    model: str,
    prompt: str,
    system: str | None = None,
    endpoint: str = "http://127.0.0.1:9001",
) -> dict[str, Any]:
    """Call HTTP endpoint /llm/generate."""
    url = f"{endpoint}/llm/generate"

    payload = {
        "provider": provider,
        "model": model,
        "prompt": prompt,
        "system": system or "",
        "params": {"temperature": 0.2, "max_tokens": 512},
        "stream": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": str(e)}


def call_direct_adapter(
    provider: str,
    model: str,
    prompt: str,
    system: str | None = None,
) -> dict[str, Any]:
    """Call llm_router directly (unified LLM interface)."""
    # Import here to avoid loading heavy dependencies if not needed
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from backend.providers.llm import llm_generate

    try:
        # Use llm_router unified interface (supports both Claude and Ollama)
        response = llm_generate(
            prompt=prompt,
            provider=provider,
            provider_config={"model": model},
            temperature=0.2,
            max_tokens=512,
        )

        return {
            "ok": True,
            "text": response.content,
            "usage": {
                "in": response.metadata.get("input_tokens", 0) if response.metadata else 0,
                "out": response.metadata.get("output_tokens", 0) if response.metadata else 0,
            },
            "latency_ms": response.latency_ms,
            "provider": response.provider,
            "model": response.model,
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Free Intelligence - LLM CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--provider",
        required=True,
        choices=["ollama", "claude"],
        help="Provider: ollama or claude",
    )

    parser.add_argument(
        "--model",
        required=True,
        help="Model identifier (e.g., qwen2:7b, claude-3-5-sonnet-20241022)",
    )

    parser.add_argument(
        "--prompt",
        required=True,
        help="Prompt text or file path",
    )

    parser.add_argument(
        "--system",
        default=None,
        help="System prompt text or file path (optional)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use adapter directly (bypass HTTP endpoint)",
    )

    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:9001",
        help="HTTP endpoint URL (default: http://127.0.0.1:9001)",
    )

    args = parser.parse_args()

    # Read inputs
    prompt = read_input(args.prompt)
    system = read_input(args.system) if args.system else None

    # Call LLM
    if args.direct:
        result = call_direct_adapter(args.provider, args.model, prompt, system)
    else:
        result = call_http_endpoint(args.provider, args.model, prompt, system, args.endpoint)

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("ok"):
            print(result["text"])
        else:
            print(f"ERROR: {result.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
