#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Manual Inference CLI

CLI tool for testing LLM inference without UI.

File: backend/cli/fi_test.py
Card: FI-CLI-FEAT-002
Created: 2025-10-29

Usage:
    python3 -m backend.cli.fi_test prompt "What is FI?"
    python3 -m backend.cli.fi_test prompt "Test" --dry-run
    python3 -m backend.cli.fi_test prompt "Debug" --verbose --model ollama

Features:
- Manual prompt submission
- Dry-run mode (no corpus save)
- Verbose output (debug)
- Model selection (claude/ollama)
- JSON output
"""

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.corpus_ops import append_interaction
from backend.llm_adapter import LLMRequest, create_adapter
from backend.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# CLI COMMAND: prompt
# ============================================================================


def cmd_prompt(args: argparse.Namespace) -> dict[str, Any]:
    """
    Execute manual prompt inference.

    Args:
        args: CLI arguments with prompt, model, flags

    Returns:
        Result dictionary with response and metadata

    Process:
    1. Create LLM adapter (claude or ollama)
    2. Generate response
    3. Optionally save to corpus (if not --dry-run)
    4. Return JSON output
    """
    session_id = f"cli_test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    interaction_id = str(uuid.uuid4())

    if args.verbose:
        logger.info(f"CLI Test — Session: {session_id}")
        logger.info(f"Prompt: {args.prompt[:100]}...")
        logger.info(f"Model: {args.model}")
        logger.info(f"Dry-run: {args.dry_run}")

    # Create adapter
    try:
        adapter = create_adapter(
            provider=args.model,
            model=None,  # Use default model for provider
        )
    except Exception as e:
        return {
            "error": "adapter_creation_failed",
            "message": str(e),
            "interaction_id": interaction_id,
        }

    # Build request
    request = LLMRequest(
        prompt=args.prompt,
        max_tokens=args.max_tokens,
        temperature=0.7,
        timeout_seconds=30,
        metadata={
            "session_id": session_id,
            "interaction_id": interaction_id,
            "source": "cli_test",
        },
    )

    # Generate response
    try:
        if args.verbose:
            logger.info("Calling LLM adapter...")

        response = adapter.generate(request)

        if args.verbose:
            logger.info(f"Response received: {len(response.content)} chars")
            logger.info(f"Tokens used: {response.tokens_used}")
            logger.info(f"Latency: {response.latency_ms}ms")

    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return {
            "error": "llm_generation_failed",
            "message": str(e),
            "interaction_id": interaction_id,
        }

    # Save to corpus (unless dry-run)
    if not args.dry_run:
        try:
            corpus_path = "storage/corpus.h5"
            saved_id = append_interaction(
                corpus_path=corpus_path,
                session_id=session_id,
                prompt=args.prompt,
                response=response.content,
                model=response.model,
                tokens=response.tokens_used,
                timestamp=datetime.now(UTC).isoformat() + "Z",
            )
            if args.verbose:
                logger.info(f"Saved to corpus: {saved_id}")
        except Exception as e:
            logger.warning(f"Failed to save to corpus: {e}")
            # Non-blocking: continue even if save fails

    # Build result
    result = {
        "interaction_id": interaction_id,
        "session_id": session_id,
        "prompt": args.prompt,
        "response": response.content,
        "model": response.model,
        "provider": response.provider,
        "tokens_used": response.tokens_used,
        "latency_ms": response.latency_ms,
        "timestamp": response.timestamp,
        "dry_run": args.dry_run,
    }

    return result


# ============================================================================
# MAIN CLI
# ============================================================================


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Free Intelligence - Manual Inference CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fi_test prompt "What is Free Intelligence?"
  fi_test prompt "Test query" --dry-run
  fi_test prompt "Debug issue" --verbose --model ollama
  fi_test prompt "Check response" --max-tokens 200
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Subcommand: prompt
    prompt_parser = subparsers.add_parser(
        "prompt",
        help="Execute manual prompt",
    )
    prompt_parser.add_argument(
        "prompt",
        type=str,
        help="Prompt text to send to LLM",
    )
    prompt_parser.add_argument(
        "--model",
        type=str,
        default="ollama",
        choices=["claude", "ollama"],
        help="LLM provider (default: ollama)",
    )
    prompt_parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Max tokens for response (default: 4096)",
    )
    prompt_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not save to corpus (test only)",
    )
    prompt_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show debug output",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "prompt":
        result = cmd_prompt(args)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
