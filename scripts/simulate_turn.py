"""Simulate one conversational turn end-to-end against a local memory.db snapshot.

Why this script exists
----------------------
Unit tests mock `llm.chat`, which means the suite can be 100% green while
production turns time out because the real prompt — with a user's 84 facts,
50 recent messages, vulnerable overlay, and flow guidance — exceeds the
Anthropic 30s budget. This script closes that blind spot: it rebuilds the
EXACT same context the chat cog would assemble for a given user, counts
the tokens with Anthropic's `count_tokens` endpoint, and optionally does a
live RTT measurement against the API.

Usage
-----
    # Dry run — just measure the prompt for Alex
    uv run python scripts/simulate_turn.py \\
        --user-id 1431300030823927999 \\
        --message "Alex ya esta mas tranqui, pero sigue pensativa"

    # Live call — measure actual RTT (costs a tiny bit of API credit)
    uv run python scripts/simulate_turn.py \\
        --user-id 1431300030823927999 \\
        --message "..." --live

    # Compare two users side-by-side (Alex vs Bernard)
    uv run python scripts/simulate_turn.py \\
        --user-id 1431300030823927999 \\
        --message "hola" \\
        --compare 907264175246569543

Defaults
--------
- DB path: /tmp/memory-live.db (download with `az storage blob download ...`)
- Channel: #general (1489180895264116736)

Limitations
-----------
- Does NOT wire up attachments, reminders, or channel_summary pulse. Those
  add minor tokens; the dominant contributors (persona, facts, recent,
  flow, overlay) ARE covered.
- `--live` uses AsyncAnthropic and the same model/timeout the bot uses,
  so RTT numbers are representative.
"""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

import anthropic
import structlog

# Silence structlog output during the run so the report is clean.
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    wrapper_class=structlog.make_filtering_bound_logger(40),  # WARNING+
)

# Config is loaded at import — must come after env setup. The project's
# .env takes priority thanks to Pydantic Settings custom source ordering.
from personas.insult.config import settings  # noqa: E402
from personas.insult.core.character import build_adaptive_prompt  # noqa: E402
from personas.insult.core.facts import build_facts_prompt  # noqa: E402
from personas.insult.core.flows import (  # noqa: E402
    ExpressionHistory,
    analyze_flows,
    build_flow_prompt,
)
from personas.insult.core.memory import MemoryStore  # noqa: E402

DEFAULT_DB = "/tmp/memory-live.db"
DEFAULT_CHANNEL = "1489180895264116736"  # #general


async def simulate(
    user_id: str,
    message: str,
    channel_id: str,
    db_path: str,
    live: bool,
) -> dict:
    """Rebuild the prompt the bot would send, count tokens, optionally RTT."""
    memory = MemoryStore(Path(db_path))
    await memory.connect()

    try:
        # 1. Context assembly — mirrors chat.ChatCog._respond() step-by-step.
        profile = await memory.get_profile(user_id)
        recent = await memory.get_recent(channel_id, 50, user_id=user_id)
        relevant = await memory.search(channel_id, message, 5, user_id=user_id)
        context = memory.build_context(recent, relevant)

        user_facts = await memory.get_facts(user_id)

        # 2. Layered prompt (Layer 1-4) + flow Layer 3.5.
        system_prompt, preset = build_adaptive_prompt(
            settings.system_prompt,
            profile,
            len(context),
            current_message=message,
            recent_messages=recent,
            user_facts=user_facts,
        )

        flow = analyze_flows(
            message,
            recent,
            preset,
            ExpressionHistory(),
            f"{channel_id}:{user_id}",
        )
        flow_prompt = build_flow_prompt(flow)
        if flow_prompt:
            system_prompt += f"\n\n{flow_prompt}"

        # 3. Facts block (what chat.py does with `build_facts_prompt`).
        user_name = recent[-1]["user_name"] if recent else "user"
        system_prompt += build_facts_prompt(user_name, user_facts)

        # 4. User turn as the final message.
        messages = [*context, {"role": "user", "content": message}]

        # 5. Token accounting — authoritative via Anthropic's count endpoint.
        api_key = settings.anthropic_api_key.get_secret_value()
        client = anthropic.AsyncAnthropic(api_key=api_key, timeout=20, max_retries=0)

        try:
            count = await client.messages.count_tokens(
                model=settings.llm_model,
                system=system_prompt,
                messages=messages,
            )
            total_input = count.input_tokens
        except Exception as e:
            # Fallback: rough char/4 estimate (good to within ~10%).
            total_input = (len(system_prompt) + sum(len(m["content"]) for m in messages)) // 4
            print(f"  (token count endpoint failed: {e!r}; using char/4 estimate)")

        # Per-section breakdown so we know where the bloat lives.
        facts_prompt = build_facts_prompt(user_name, user_facts)
        context_chars = sum(len(m.get("content", "")) for m in context)
        user_msg_chars = len(message)

        report = {
            "user_id": user_id,
            "preset_mode": preset.mode.value,
            "preset_reason": preset.reason,
            "vulnerable_overlay": preset.reason.startswith("vulnerable_user_overlay"),
            "facts_count": len(user_facts),
            "recent_count": len(recent),
            "relevant_count": len(relevant),
            "persona_chars": len(settings.system_prompt),
            "flow_chars": len(flow_prompt),
            "facts_chars": len(facts_prompt),
            "context_chars": context_chars,
            "user_msg_chars": user_msg_chars,
            "system_total_chars": len(system_prompt),
            "total_input_tokens": total_input,
        }

        # 6. Live RTT measurement (optional). Uses the router's primary model
        # and real timeout so the number reflects what the bot actually sees.
        if live:
            print(f"  [live] sending to {settings.llm_model} (timeout=30s)...")
            t0 = time.monotonic()
            try:
                resp = await asyncio.wait_for(
                    client.messages.create(
                        model=settings.llm_model,
                        max_tokens=settings.llm_max_tokens,
                        system=system_prompt,
                        messages=messages,
                    ),
                    timeout=35,
                )
                elapsed = time.monotonic() - t0
                report["live_rtt_seconds"] = round(elapsed, 2)
                report["live_output_tokens"] = resp.usage.output_tokens
                report["live_stop_reason"] = resp.stop_reason
            except TimeoutError:
                report["live_rtt_seconds"] = ">35"
                report["live_status"] = "TIMEOUT"
            except Exception as e:
                report["live_status"] = f"ERROR: {type(e).__name__}: {e!s}"

        await client.close()
        return report
    finally:
        await memory.close()


def print_report(r: dict) -> None:
    print(f"\n=== user_id {r['user_id']} ===")
    print(f"  Preset:            {r['preset_mode']}")
    print(f"  Overlay active:    {r['vulnerable_overlay']}")
    print(f"  Reason:            {r['preset_reason'][:80]}")
    print(f"  Facts count:       {r['facts_count']}")
    print(f"  Recent msgs:       {r['recent_count']}")
    print(f"  Relevant msgs:     {r['relevant_count']}")
    print()
    print(f"  persona prompt:    {r['persona_chars']:>7,} chars")
    print(f"  flow prompt:       {r['flow_chars']:>7,} chars")
    print(f"  facts prompt:      {r['facts_chars']:>7,} chars")
    print(f"  context messages:  {r['context_chars']:>7,} chars")
    print(f"  user message:      {r['user_msg_chars']:>7,} chars")
    print(f"  SYSTEM TOTAL:      {r['system_total_chars']:>7,} chars")
    print()
    print(f"  >> INPUT TOKENS:   {r['total_input_tokens']:>7,}")
    if "live_rtt_seconds" in r:
        print(f"  >> LIVE RTT:       {r['live_rtt_seconds']}s")
        if "live_output_tokens" in r:
            print(f"  >> OUTPUT TOKENS:  {r['live_output_tokens']}")
            print(f"  >> STOP:           {r.get('live_stop_reason')}")
    if "live_status" in r:
        print(f"  >> STATUS:         {r['live_status']}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user-id", required=True, help="Discord user_id to simulate")
    parser.add_argument("--message", required=True, help="Text of the simulated user turn")
    parser.add_argument(
        "--channel-id", default=DEFAULT_CHANNEL, help=f"Channel ID (default {DEFAULT_CHANNEL} = #general)"
    )
    parser.add_argument("--db", default=DEFAULT_DB, help=f"Path to SQLite DB (default {DEFAULT_DB})")
    parser.add_argument("--live", action="store_true", help="Do a real API call and measure RTT (costs credit)")
    parser.add_argument("--compare", help="Second user_id to simulate side-by-side")
    args = parser.parse_args()

    if not Path(args.db).exists():
        raise SystemExit(f"DB not found at {args.db}. Download with: az storage blob download ...")

    print(f"Simulating turn: message={args.message!r}")
    print(f"DB: {args.db}  |  Channel: {args.channel_id}  |  Live: {args.live}")

    r1 = await simulate(args.user_id, args.message, args.channel_id, args.db, args.live)
    print_report(r1)

    if args.compare:
        r2 = await simulate(args.compare, args.message, args.channel_id, args.db, args.live)
        print_report(r2)

        # Side-by-side delta
        print("\n=== DELTA (user1 - user2) ===")
        print(f"  facts count:       {r1['facts_count'] - r2['facts_count']:+d}")
        print(f"  system chars:      {r1['system_total_chars'] - r2['system_total_chars']:+,}")
        print(f"  input tokens:      {r1['total_input_tokens'] - r2['total_input_tokens']:+,}")


if __name__ == "__main__":
    asyncio.run(main())
