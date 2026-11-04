"""Send ONE tagged probe to the persona-runner and print what really answered.

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

The model (2026-11-04): `/v1/turn` has no model field, the router picks by tier.
To pin one, pass `--tier`: the id comes from the runner's own `GET /health`, the
persona's DNA from `shared/personas/`, and the call goes to `/v1/judge`, which has
no memory and no markers. Either way the exit code is 1 unless a model answered,
so a 200 alone never counts.

Usage:
    PERSONA_RUNNER_URL=https://persona-runner.<env>.azurecontainerapps.io \\
    PERSONA_RUNNER_TOKEN="$(cat ~/.secrets/discord-bot-agent-runner-token.txt)" \\
    python scripts/probe_turn.py --persona insult --slug f5-wire \\
        "Contesta SOLO con una reacción usando tu marcador [REACT:]."

    ... python scripts/probe_turn.py --persona frugivoro --tier crisis --slug kefir "¿Se puede?"

The token is read from the environment and never printed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

import httpx

PROBE_PREFIX = "probe-"
NO_MODEL_ANSWERED = "<synthetic>"
PERSONAS_DIR = pathlib.Path(__file__).resolve().parent.parent / "shared" / "personas"


def pin_payload(args: argparse.Namespace, served: dict[str, str]) -> dict:
    """The `/v1/judge` body of a pinned probe, or SystemExit when the tier or the DNA is not there."""
    if args.tier not in served:
        raise SystemExit(f"tier {args.tier!r} is not served; the runner lists {sorted(served)}")
    dna = PERSONAS_DIR / f"{args.persona}.md"
    if not dna.exists():
        raise SystemExit(f"no DNA at {dna}")
    return {
        "system_prompt": dna.read_text(encoding="utf-8"),
        "user_text": args.ask,
        "model": served[args.tier],
        "persona_id": args.persona,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ask", help="what the probe says to the persona")
    parser.add_argument("--persona", default="insult")
    parser.add_argument("--slug", required=True, help="what this probe verifies, e.g. f5-wire")
    parser.add_argument("--probe-id", default="claude", help="the probe principal becomes probe-<this>")
    parser.add_argument("--surface", default="og118")
    parser.add_argument("--tier", help="pin the model by the tier name /health lists, e.g. crisis")
    parser.add_argument("--timeout", type=float, default=200.0, help="under the ingress's 240 s ceiling")
    args = parser.parse_args()

    url = os.environ.get("PERSONA_RUNNER_URL", "").rstrip("/")
    token = os.environ.get("PERSONA_RUNNER_TOKEN", "")
    if not url or not token:
        print("PERSONA_RUNNER_URL and PERSONA_RUNNER_TOKEN must be set", file=sys.stderr)
        return 2

    timeout = httpx.Timeout(args.timeout, connect=10.0)
    if args.tier:
        served = httpx.get(f"{url}/health", timeout=timeout).raise_for_status().json()["models"]
        path, payload = "/v1/judge", pin_payload(args, served)
        print(f"pinned tier={args.tier} model={payload['model']}")
    else:
        today = dt.datetime.now(dt.UTC).date().isoformat()
        path = "/v1/turn"
        payload = {
            "channel_id": f"{PROBE_PREFIX}{today}-{args.slug}",
            "user_id": f"{PROBE_PREFIX}{args.probe_id}",
            "user_name": f"{PROBE_PREFIX}{args.probe_id}",
            "surface": args.surface,
            "pipeline": "runner",
            "origin": "probe",
            "persona_id": args.persona,
            "user_text": args.ask,
        }
        print(f"channel={payload['channel_id']} principal={payload['user_id']}")

    resp = httpx.post(f"{url}{path}", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=timeout)
    print(f"http={resp.status_code} path={path}")
    if resp.status_code != 200:
        print(resp.text[:500])
        return 1
    data = resp.json()
    fields = ("text", "reactions", "gif_urls", "empty_reason", "model", "output_tokens")
    print(json.dumps({k: data[k] for k in fields if k in data}, ensure_ascii=False, indent=2))
    if data.get("model") == NO_MODEL_ANSWERED or not data.get("output_tokens"):
        print(f"NO MODEL ANSWERED: model={data.get('model')!r} output_tokens={data.get('output_tokens')!r}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
