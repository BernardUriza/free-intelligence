# Robustness Rules

## Error Handling
- Every command must have try/except with user-facing error message
- Error messages are ALWAYS in-character (via `get_error_response()` in `core/errors.py`)
- NEVER expose "Claude", "Anthropic", "API", or internal error types to users
- DB write failures are logged but don't crash the command (user message still gets a response)
- Never let exceptions propagate silently — always log with structlog

## Rate Limiting
- !chat: 1 use / 15s per user (protects Claude API tokens)
- !buscar: 1 use / 10s per user
- !memoria: 1 use / 5s per user
- !perfil: 1 use / 10s per user
- !ping: 1 use / 3s per user
- Cooldown errors are in-character (not generic Discord messages)

## LLM Resilience
- Timeout: 30s (configurable via LLM_TIMEOUT)
- Max retries: 5 for most errors (configurable via LLM_MAX_RETRIES)
- SDK-level retries disabled: `AsyncAnthropic(max_retries=0)` — our outer loop
  owns retry policy. Without this, the SDK silently retries ~2x internally and
  inflates observed timeouts from 30s to ~90s per attempt.
- RateLimitError: exponential backoff (2^attempt seconds), up to LLM_MAX_RETRIES
- AuthenticationError: fail immediately, no retry
- Timeout/ConnectionError: **capped at 2 attempts total** (`_MAX_TIMEOUT_RETRIES` in `llm.py`),
  with 1s delay between them. Five timeouts × 30s = 2+ minutes of dead air is too
  punishing; after 2 we give up and raise.
- Timeout retry UX: callers may pass `on_timeout` to `LLMClient.chat()`. It fires
  **once** after the first APITimeoutError so the user gets an in-character
  "retry_notice" message instead of silent dead air. `chat.py._respond()` wires this.
- APIStatusError 529 (Overloaded): exponential backoff, up to LLM_MAX_RETRIES
- Other APIError: fail immediately
- Character break detected: auto-retry with reinforced system prompt, then sanitize

## Lifecycle
- Signal handling: SIGTERM/SIGINT → graceful shutdown (close DB, close bot)
- Health check task: every 60s, logs latency + guilds + memory stats
- on_disconnect / on_resumed events logged for connection monitoring
- DB auto-reconnect via _ensure_connection() before every operation

## Logging
- Use structlog everywhere (never print())
- Log events: bot_ready, bot_disconnected, bot_resumed, health_check
- Log LLM: llm_request, llm_response (with token counts), llm_*_error
- Log character: character_break_detected, character_break_fixed_on_retry
- Log style: style_adapted (with user profile metrics)
- Log memory: memory_connected, memory_closed, memory_store_failed
- Log attachments: attachment_processed, attachment_rejected
- Log commands: command_error with user context

## Destructive Post-Processing — MANDATORY

Any post-LLM mutator (regex stripper, heuristic truncator, profile updater)
that acts on a single signal MUST consider context before mutating output
or persistent state. Three production bugs hit users within the same hour
on 2026-05-18 from this exact class:

| Bug | File | Symptom |
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
  like `detected_language`. Continuous fields keep using EMA.

### Required tests for any new mutator

Every mutator MUST land with at least two tests:

1. The positive case it exists to fix (the bug it claims to detect)
2. The **resistance case** — a near-miss that looks like the target but is
   intentional and must be preserved.

Examples in this codebase:
- `test_preserves_intentional_quote` ⇆ `test_strips_unquoted_echo`
- `test_confident_profile_resists_single_off_language_msg` ⇆
  `test_confident_profile_switches_after_three_consecutive_off_language`
- `test_uniform_medium_preserves_markers_in_tail` ⇆
  `test_uniform_medium_truncates`

Without the resistance test, the mutator's regression risk is invisible
until production hits the wrong shape.

### Code-review checklist before approving a new mutator

- What context would make this mutation wrong? (quote-wrapped span,
  established profile, marker-bearing tail)
- Is there a paragraph-level / multi-signal check before the hard
  mutation, or does it act on the first match?
- Are there tests for both the positive case AND the resistance case?
- Does the telemetry event (`echo_stripped`, `length_enforced`, etc.)
  include a `reason` field describing WHY the mutation fired?

Reference: full case studies in
`memory/feedback_destructive_post_processing.md`.
