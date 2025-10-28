#!/usr/bin/env python3
"""
Free Intelligence - CLI Tool

Interactive CLI for LLM chat using policy-driven routing.

Usage:
    python3 cli/fi.py chat
    python3 cli/fi.py chat --provider ollama
"""

import sys
import argparse
from typing import Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.llm_router import llm_generate
from backend.policy_loader import get_policy_loader
from backend.logger import get_logger

logger = get_logger(__name__)


def chat_mode(provider: Optional[str] = None, model: Optional[str] = None):
    """
    Interactive chat mode with LLM.

    Args:
        provider: Optional provider override (uses policy default if None)
        model: Optional model override (uses policy default if None)
    """
    # Load policy to show config
    policy_loader = get_policy_loader()

    # Determine effective provider and model
    if provider is None:
        provider = policy_loader.get_primary_provider()

    if model is None:
        provider_config = policy_loader.get_provider_config(provider)
        model = provider_config.get('model', 'unknown')

    # Welcome banner
    print("╔════════════════════════════════════════════════════════════╗")
    print("║          🧠 Free Intelligence - Interactive Chat          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    print(f"📋 Provider: {provider}")
    print(f"🤖 Model:    {model}")
    print(f"💡 Tip:      Type 'exit', 'quit', or Ctrl+C to end session")
    print()
    print("─" * 60)
    print()

    # Chat loop
    while True:
        try:
            # Get user input
            prompt = input("You: ").strip()

            # Check for exit commands
            if prompt.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break

            # Skip empty prompts
            if not prompt:
                continue

            # Generate response
            print("\n🤖 Thinking...\n")

            kwargs = {}
            if provider:
                kwargs['provider'] = provider
            if model:
                # Pass model via provider_config
                kwargs['provider_config'] = {'model': model}

            response = llm_generate(prompt, **kwargs)

            # Display response
            print(f"Assistant: {response.content}\n")

            # Display metadata
            print(f"┌─ Metadata ─────────────────────────────────────────────┐")
            print(f"│ Provider: {response.provider:20s}                    │")
            print(f"│ Model:    {response.model:20s}                    │")
            print(f"│ Tokens:   {response.tokens_used:5d}                                    │")
            if response.cost_usd:
                print(f"│ Cost:     ${response.cost_usd:.6f}                                 │")
            if response.latency_ms:
                print(f"│ Latency:  {response.latency_ms:.2f}ms                                 │")
            print(f"└────────────────────────────────────────────────────────┘")
            print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            logger.error("CLI_CHAT_ERROR", error=str(e))


def show_config():
    """Show current policy configuration"""
    try:
        policy_loader = get_policy_loader()

        print("╔════════════════════════════════════════════════════════════╗")
        print("║           🔐 Free Intelligence - Configuration            ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print()

        # LLM Config
        print("📋 LLM Configuration:")
        print(f"   Primary Provider:  {policy_loader.get_primary_provider()}")
        print(f"   Fallback Provider: {policy_loader.get_fallback_provider()}")
        print(f"   Offline Mode:      {'✅ Enabled' if policy_loader.is_offline_enabled() else '❌ Disabled'}")
        print()

        # Claude Config
        print("🤖 Claude Configuration:")
        try:
            claude_config = policy_loader.get_provider_config('claude')
            print(f"   Model:        {claude_config.get('model')}")
            print(f"   Timeout:      {claude_config.get('timeout_seconds')}s")
            print(f"   Max Tokens:   {claude_config.get('max_tokens')}")
            print(f"   Temperature:  {claude_config.get('temperature')}")
        except KeyError:
            print("   (Not configured)")
        print()

        # Budgets
        print("💰 Budget Configuration:")
        budgets = policy_loader.get_budgets()
        print(f"   Max Cost/Day:       ${budgets.get('max_cost_per_day', 0)}")
        print(f"   Max Requests/Hour:  {budgets.get('max_requests_per_hour', 0)}")
        print(f"   Alert Threshold:    {int(budgets.get('alert_threshold', 0) * 100)}%")
        print()

        # Fallback Rules
        print("🔄 Fallback Rules:")
        rules = policy_loader.get_fallback_rules()
        for i, rule in enumerate(rules, 1):
            print(f"   {i}. {rule['condition']:15s} → {rule['action']}")
        print()

    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        logger.error("CLI_CONFIG_ERROR", error=str(e))


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Free Intelligence - Interactive LLM CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start chat with policy defaults
  python3 cli/fi.py chat

  # Override provider
  python3 cli/fi.py chat --provider ollama

  # Override model
  python3 cli/fi.py chat --model claude-3-5-haiku-20241022

  # Show configuration
  python3 cli/fi.py config
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Start interactive chat')
    chat_parser.add_argument('--provider', type=str, help='Override provider (claude, ollama)')
    chat_parser.add_argument('--model', type=str, help='Override model')

    # Config command
    subparsers.add_parser('config', help='Show current configuration')

    args = parser.parse_args()

    # Handle commands
    if args.command == 'chat':
        chat_mode(provider=args.provider, model=args.model)
    elif args.command == 'config':
        show_config()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
