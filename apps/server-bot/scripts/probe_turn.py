"""Send ONE tagged probe turn to the persona-runner and print its OutboundTurn.

The sanctioned way to get a wire receipt from production (2026-09-28). A probe
must never speak as a real person: that day a wire check ran under Bernard's
principal and landed in his memory, and his fact store already held facts mined
from months of earlier probes ("ran probe #58 with fact 73 alive").

What this script guarantees, by construction:

- `origin="probe"`: the runner stores both rows tagged, never extracts facts,
  and the reflection loop skips them (`messages.origin = 'probe'`).
- `user_id="probe-<name>"`: an unlinked id is its own principal, so the probe
  has no memory to read and leaves nothing in anyone else's. The runner REJECTS
  (422) a probe whose user_id does not start with `probe-`.
- a `probe-<date>-<slug>` channel, so the rows are greppable by channel too.

Usage:
    PERSONA_RUNNER_URL=https://persona-runner.<env>.azurecontainerapps.io \\
    PERSONA_RUNNER_TOKEN="$(cat ~/.secrets/discord-bot-agent-runner-token.txt)" \\
    python scripts/probe_turn.py --persona insult --slug f5-wire \\
        "Contesta SOLO con una reacción usando tu marcador [REACT:]."

The token is read from the environment and never printed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import httpx

PROBE_PREFIX = "probe-"


def build_probe_payload(
    ask: str,
    *,
    persona: str,
    slug: str,
    probe_id: str = "claude",
    surface: str = "og118",
    pipeline: str = "runner",
    today: str | None = None,
) -> dict:
    """The `/v1/turn` body of a probe — the ONE place a probe's identity is built.

    Other harnesses (`scripts/frugivoro_bench.py`) import this instead of
    re-typing the shape, so a probe can never drift into speaking as a person.
    """
    today = today or dt.datetime.now(dt.UTC).date().isoformat()
    principal = f"{PROBE_PREFIX}{probe_id}"
    return {
        "channel_id": f"{PROBE_PREFIX}{today}-{slug}",
        "user_id": principal,
        "user_name": principal,
        "surface": surface,
        "pipeline": pipeline,
        "origin": "probe",
        "persona_id": persona,
        "user_text": ask,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ask", help="what the probe says to the persona")
    parser.add_argument("--persona", default="insult")
    parser.add_argument("--slug", required=True, help="what this probe verifies, e.g. f5-wire")
    parser.add_argument("--probe-id", default="claude", help="the probe principal becomes probe-<this>")
    parser.add_argument("--surface", default="og118")
    parser.add_argument("--timeout", type=float, default=200.0, help="under the ingress's 240 s ceiling")
    args = parser.parse_args()

    url = os.environ.get("PERSONA_RUNNER_URL", "").rstrip("/")
    token = os.environ.get("PERSONA_RUNNER_TOKEN", "")
    if not url or not token:
        print("PERSONA_RUNNER_URL and PERSONA_RUNNER_TOKEN must be set", file=sys.stderr)
        return 2

    payload = build_probe_payload(
        args.ask, persona=args.persona, slug=args.slug, probe_id=args.probe_id, surface=args.surface
    )
    resp = httpx.post(
        f"{url}/v1/turn",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(args.timeout, connect=10.0),
    )
    print(f"http={resp.status_code} channel={payload['channel_id']} principal={payload['user_id']}")
    if resp.status_code != 200:
        print(resp.text[:500])
        return 1
    data = resp.json()
    fields = ("text", "reactions", "gif_urls", "empty_reason", "model", "output_tokens")
    print(json.dumps({k: data.get(k) for k in fields}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
