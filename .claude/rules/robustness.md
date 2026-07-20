# Robustness Rules

> **Post-purga (2026-07-14, 2f8d9ad):** the prefix-command bot
> (`!chat`/`!buscar`/`!memoria`/`!perfil`/`!ping` + their cooldown table) and
> the direct-Anthropic `LLMClient` (`personas/insult/core/llm.py`) are DELETED.
> The live turn path is `persona_gateway/` → `persona_runner` `/v1/turn`. This
> file describes the live failure surfaces plus the historical lessons that
> still bind.

## Error Handling
- The live guarded entry is `persona_gateway/gateway.py::_dispatch`: any turn
  failure logs `persona_gateway_turn_failed` and NEVER exposes internals to the
  channel — the recovery is a neutral "…" send, itself guarded, falling through
  to a reaction (different rate-limit bucket) if the send 429s.
- NEVER expose "Claude", "Anthropic", "API", or internal error types to users.
- DB write failures are logged but don't kill the turn (the user still gets a
  response).
- Never let exceptions propagate silently — always log with structlog.
- **Fail-safe doctrine (guidance/behavior engine):** any fault in guidance
  assembly degrades to a normal turn, never a mute bot
  (`khimeras_shared/guidance.py`).

## LLM Resilience (historical lessons — the client died, the doctrine stands)

The tuned retry loop below lived in the deleted `LLMClient`; today the gateway
calls the runner over HTTP (`khimeras_shared/runner/` client) and the runner
owns the model call via the Claude Agent SDK. When (re)building any direct
model client, these remain law:

- **Disable SDK-level retries** (`max_retries=0` on the SDK client) — the outer
  loop owns retry policy. Otherwise the SDK silently retries ~2x internally and
  inflates observed timeouts from 30s to ~90s per attempt.
- RateLimitError / 529 Overloaded: exponential backoff **with jitter**, bounded
  attempts; honor `retry-after` when ≤60s.
- AuthenticationError: fail immediately, no retry.
- Timeout/ConnectionError: cap at 2 attempts total — five timeouts × 30s of
  dead air is too punishing for a chat surface.
- Give the user an in-character signal after the first timeout instead of
  silent dead air.

## Lifecycle (live: `persona_gateway/boot.py` + `gateway.py`)
- **Bind → connect → login order is mandatory**: the health/API port (8788)
  binds BEFORE Postgres connect and Discord login, so the platform's startup
  probe never kills a slow boot (root fix of the ActivationFailed hangs,
  v4.22.14 — see [[reference_activationfailed_gateway_hang]]).
- Each persona runs under its own supervision; one persona crashing logs
  `persona_gateway_persona_failed` without silently killing the siblings, and
  `persona_gateway_all_personas_down` fires when nothing is left.
- `/health` is honest — it reflects real serving state, not an early flag
  (the 2026-06-13 boot-zombie lesson: `is_ready:true` while dead for 14 min).

## Logging
- Use structlog everywhere (never print()).
- Prefer structured event names with a stable prefix (the gateway family is
  `persona_gateway_*`) and typed fields over prose; `LOG_FORMAT=json` in prod
  (ANSI in prod logs broke KQL parsing once — see
  [[feedback_kql_has_lies_and_ansi_logs]]).
- Log every stage transition of a turn so an orphaned turn (start without end)
  is detectable in KQL — see the dropped-messages workflow in `testing.md`.

## Destructive Post-Processing — MANDATORY

> The three files named in the 2026-05-18 table died in 2f8d9ad, but the
> principle binds every LIVE post-LLM mutator: the marker strippers
> (`khimeras_shared/markers.py`, `khimeras_shared/reactions.py::strip_reactions`),
> and the style-profile updater (`khimeras_shared/style.py` — which today
> implements the two-regime stickiness this lesson demanded).

Any post-LLM mutator (regex stripper, heuristic truncator, profile updater)
that acts on a single signal MUST consider context before mutating output
or persistent state. Three production bugs hit users within the same hour
on 2026-05-18 from this exact class (files as they existed then):

| Bug | File (historical) | Symptom |
|---|---|---|
| Echo strip ate quoted citations | `core/character/formatting.py:strip_echoed_quotes` | `"su equipo no crece" — eso te lo inventas` became ` no crece" — eso te lo inventas` (orphan quote + missing opener + missing content) |
| Language flipped on a single paste | `core/style.py:UserStyleProfile.update` | Bernard pasted an English email; bot responded entirely in English next turn |
| Length enforcer truncated 80-90% of content | `core/character/formatting.py:enforce_length_variation` | Cut a 217-word response to 38 words, silently dropping `[REMEMBER:]` and `[REACT:]` markers in the tail |

### Required design when mutating LLM output

- **Quote-adjacency rule** (text mutators): if the matched span is inside
  `"..."`, `'...'`, `«...»`, smart quotes, it is almost certainly
  intentional content — skip the mutation. Use **paragraph-level evidence**
  (`≥2 quote chars in the paragraph → assume intentional citation, skip`).
  Character-adjacent lookbehind/lookahead is NOT enough; quotes may be
  separated from the span by 1-2 words.
- **Marker rescue** (truncators): before dropping any portion of the LLM
  output, extract `[REMEMBER:]` and `[REACT:]` markers from the dropped
  region and re-append to what remains. The persistence and reaction
  layers must not silently lose state because of a formatting heuristic.
- **Two-regime stickiness** (profile updaters): brand-new profiles
  (`count < CONFIDENCE_THRESHOLD`) may flip on a single signal — they are
  still learning. Confident profiles MUST require N consecutive
  other-side signals (streak counter) before flipping a discrete field
  like `detected_language`. Continuous fields keep using EMA. Live
  implementation: `khimeras_shared/style.py` (`lang_switch_streak`).

### Required tests for any new mutator

Every mutator MUST land with at least two tests:

1. The positive case it exists to fix (the bug it claims to detect)
2. The **resistance case** — a near-miss that looks like the target but is
   intentional and must be preserved.

Live examples: `tests/core/test_style.py` (confident profile resists a single
off-language message ⇆ switches after consecutive ones).

Without the resistance test, the mutator's regression risk is invisible
until production hits the wrong shape.

### Code-review checklist before approving a new mutator

- What context would make this mutation wrong? (quote-wrapped span,
  established profile, marker-bearing tail)
- Is there a paragraph-level / multi-signal check before the hard
  mutation, or does it act on the first match?
- Are there tests for both the positive case AND the resistance case?
- Does the telemetry event include a `reason` field describing WHY the
  mutation fired?

Reference: full case studies in
`memory/feedback_destructive_post_processing.md`.
