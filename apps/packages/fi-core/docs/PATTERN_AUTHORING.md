# Pattern authoring guide — fi_core.persona

A long-form companion to the `## Writing your own pack` section in the
top-level [`README.md`](../README.md). The README shows the four-step
recipe; this doc covers the design decisions that make the difference
between a pack that fires once a week with a false positive and a pack
that catches the failure modes you actually deployed for.

Read this if you are about to write more than ~5 patterns. For 1-5
patterns, the README walkthrough is enough.

---

## 1. Boundaries — `\b`, lookbehind, lookahead, anchors

The most common source of false positives is a pattern that matches as
a substring inside an unrelated word or sentence. The fix is almost
always tighter boundaries.

### `\b` — word boundary

Use `\b` on both sides of any keyword that could appear inside another
word. Without `\b`, a pattern for `AI` matches `Email`, `naive`, `fail`,
`raisin`, etc.

```python
# Bad — matches "Email", "naive", "fail", "trail"
re.compile(r"(?i)AI")

# Good — only matches AI as its own word
re.compile(r"(?i)\bAI\b")
```

The built-in packs use `\b` consistently around tokens like `AI`,
`Claude`, `Anthropic`, `OpenAI`, `ChatGPT`. Follow the same convention
in your own packs.

### Lookbehind `(?<!...)` and lookahead `(?!...)`

Word boundaries are not enough when the surrounding character isn't
alphanumeric. The canonical case in this codebase is **stage directions
vs markdown emphasis**:

- Stage direction: `*sighs*` — narration drift, should fire.
- Markdown emphasis: `*important*` or `**bold**` — legitimate, should
  NOT fire.

The `STAGE_DIRECTIONS` pack distinguishes them using lookbehind +
lookahead to exclude the `**` case:

```python
re.compile(
    r"(?<!\*)\*(?!\*)"  # single * not preceded or followed by another *
    r"(?:sighs?|leans?|pauses?|smiles?|nods?|shrugs?|...)[^*]*\*(?!\*)"
)
```

`(?<!\*)` says "the character before this `*` is NOT another `*`"; the
`(?!\*)` immediately after says "the character after this `*` is NOT
another `*`". Together they reject `**bold**` while accepting `*sighs*`.

Use the same trick whenever you need a regex that is *almost* a simple
keyword match but has a known legitimate variant you must exclude.

### `^` and `$` — anchors with `re.MULTILINE`

If a pattern must only fire at the start or end of a line — e.g.
markdown headers, single-word punt responses — anchor it and use
`re.MULTILINE` (or the `(?m)` inline flag) so `^` and `$` match line
boundaries instead of only string boundaries.

```python
# Markdown header drift — only at line start
re.compile(r"^(#{1,3} )", re.MULTILINE)

# Single-word "repite" punt — only at end of line
re.compile(r"(?im)(?<!\w)repite(?:\s+...)?[.!?]?\s*$")
```

---

## 2. Case sensitivity — prefer `(?i)` inline

Two equivalent ways to make a pattern case-insensitive:

```python
# Style A — inline flag
re.compile(r"(?i)\bI'?m an AI\b")

# Style B — compile-time flag
re.compile(r"\bI'?m an AI\b", re.IGNORECASE)
```

Both work. The built-in packs use **Style A consistently**. Reasons:

- The inline flag is visible at the start of the regex string. When
  you `grep` for `re.compile` in your codebase, you can tell at a
  glance whether case matters without scanning for trailing args.
- Mixed styles in the same file create noise during review.
- `(?i)` survives when patterns are concatenated or stored as raw
  strings; the compile-time flag does not.

Pick a style, document it, stick to it. We picked `(?i)`.

The few exceptions in the built-in packs (`STAGE_DIRECTIONS`'s second
pattern, `MARKDOWN_DRIFT`'s header pattern) use the compile-time flag
because they also need another flag (`re.IGNORECASE | re.MULTILINE`),
and the combined-flag form is clearer than `(?im)`.

---

## 3. False-positive avoidance

A bad pattern is a pattern that fires when the response is fine. Two
worked examples:

### Bad pattern — bare brand reference

```python
# WRONG — fires on legitimate references to Anthropic
re.compile(r"(?i)\bAnthropic\b")
```

This pattern is in `GENERIC_AI_DISCLOSURE_EN` because in 99% of
in-character chatbot responses, the bot does NOT mention Anthropic. It
fires on identity leaks like "I was made by Anthropic". But for a
**technical assistant bot** that legitimately discusses LLM providers,
this pattern is a constant false positive — "Anthropic released a new
Sonnet" is a perfectly fine response.

The fix is to specialize the pattern to the leak context:

```python
# Better for a technical-assistant persona
re.compile(r"(?i)\b(?:I\s+(?:am|was)|soy|fui\s+creado\s+por)\s+(?:made\s+by\s+)?Anthropic\b")
```

This matches "I was made by Anthropic" but not "Anthropic shipped a
new model." Use the bare brand pattern when you have a persona where
the bot should never mention the company; use the specialized version
when the bot might legitimately talk about LLM providers.

### Bad pattern — overbroad disclaimer

```python
# WRONG — fires on perfectly legitimate uses
re.compile(r"(?i)\bplease\s+note\b")
```

"Please note that the script overwrites the file" is a fine engineering
response. The intended target was disclaimers like "Please note that I
am an AI and..." — but the regex doesn't say so. The fix is to bind
the disclaimer to the leak context:

```python
re.compile(r"(?i)\bplease\s+note\s+that\s+I\s+am\s+(?:an?\s+)?(?:AI|bot|assistant)\b")
```

The general rule: **a pattern should only fire if its match is, on its
own, sufficient evidence of the failure mode.** If the match needs
additional context to be a real leak, tighten the regex to require
that context.

---

## 4. Stage directions vs emphasis — the discord-bot pattern

The `STAGE_DIRECTIONS` pack solves a specific sub-problem that recurs
in roleplay / character bots: the model narrating its own actions in
prose, like `*sighs*`, `*leans back*`, `[pauses thoughtfully]`. The
trick is excluding markdown emphasis (`*italic*`, `**bold**`).

The solution in `packs.py`:

```python
STAGE_DIRECTIONS: list[re.Pattern[str]] = [
    re.compile(
        r"(?<!\*)\*(?!\*)"
        r"(?:sighs?|leans?|pauses?|smiles?|nods?|shrugs?|laughs?|winks?|"
        r"looks|turns|walks|grabs|adjusts|crosses|tilts)[^*]*\*(?!\*)"
    ),
    re.compile(
        r"\[[^\]]*(?:leans|sighs|laughs|pauses|smiles|nods|shrugs)[^\]]*\]",
        re.IGNORECASE,
    ),
]
```

Three things to notice:

1. **Lookbehind + lookahead** reject the `**bold**` case (see § 1).
2. The action **vocabulary is enumerated** — `sighs?`, `leans?`, etc.
   This intentionally limits the regex to verbs that are common stage
   directions. A pattern like `\*[a-z]+\*` would match `*italic*` too.
3. **Two patterns**, one for `*action*` and one for `[action]`. Both
   bracketing styles appear in the wild; the bot uses whichever its
   training corpus weighted higher.

If your persona has a roleplay drift problem, copy this pattern shape
and add your own action vocabulary. Don't try to generalize it to "any
single-word action" — that produces false positives in normal prose.

---

## 5. Severity tier decision — when does a pattern belong where

The three detectors map to three severity tiers:

| Tier | Detector | Action |
| --- | --- | --- |
| Hard break | `BreakDetector` | Retry the LLM call. If retry also matches, sanitize. |
| Soft drift | `AntiPatternMonitor` | Log telemetry. Send response. |
| Clarification dump | `ClarificationDumpDetector` | Retry with context cue. |

The tier matters because the actions have very different costs:

- A retry costs another LLM round-trip (latency + tokens). Wrong call
  on a soft-drift pattern means you double your latency on responses
  that were fine.
- A log-only event costs nearly nothing. Wrong call on a hard-break
  pattern means you ship the leak and only find out from telemetry.

### The decision matrix

When in doubt, weigh two factors against each other:

| Factor | Push toward hard break | Push toward soft drift |
| --- | --- | --- |
| **False-positive rate** | Low — pattern almost never fires in clean output. | High — pattern fires occasionally on legitimate responses. |
| **Cost of missing the failure** | High — single match destroys trust or violates policy. | Low — annoying but recoverable on next turn. |
| **Frequency in clean output** | Near zero. | Non-zero but acceptable. |
| **Can the persona ever legitimately say this?** | No. | Maybe rarely. |

A pattern with low false-positive rate AND high cost-of-miss belongs in
`BreakDetector`. A pattern with high false-positive rate OR low
cost-of-miss belongs in `AntiPatternMonitor`. Patterns that punt the
task back at the user (regardless of false-positive rate) belong in
`ClarificationDumpDetector` because the remedy is different — the bot
isn't out of character, it just needs to be told to use its context.

### Elevation rule

A pattern can be elevated from soft drift to hard break for a specific
persona where the legitimate-use rate drops to zero. The Insult bot
example: `SUMMARIZING` (`In summary`, `to recap`) is soft drift for
most chatbots — they legitimately summarize. For the Insult persona,
the character never legitimately summarizes, so `In summary` is moved
to `BreakDetector`. Document the elevation in a comment in your
consumer code so future maintainers know why.

---

## 6. Idempotency of detector calls

The detectors are pure functions of `(patterns, text)`. Calling
`detect()` twice on the same text yields the same result; there is no
internal state, no mutation, no side effects. You can call detectors
in any order on the same response and the answers are the same.

This is contractual — tests pin it and downstream code (including
sanitize-after-retry flows) depends on it. If you fork a detector
class for your codebase, **do not** add caching, memoization, or any
form of internal state. The patterns can be reused across many calls
safely; do not introduce per-instance state.

(The `save_chunks` idempotency contract referenced elsewhere in
`fi-core` lives in `fi_core.rag` — not relevant to persona detection.
Mentioned here only because the brief asked.)

---

## 7. Testing your pack

Every pack you author should ship with a pytest smoke test. Two tests
are the minimum:

1. **Positive** — the detector with your patterns detects an example
   leak phrase.
2. **Negative** — the detector returns empty on a clean response.

Optionally:

3. **Boundary** — your tightest pattern doesn't fire on the
   false-positive case you designed it to exclude.

Example skeleton, paralleling `tests/test_persona_detect.py` in this
package:

```python
# tests/test_my_persona_pack.py
from fi_core.persona import BreakDetector
from my_pkg.persona_patterns import (
    MY_BREAK_PATTERNS,
    MY_REINFORCEMENT,
)


def test_my_pack_detects_known_leak():
    detector = BreakDetector(patterns=MY_BREAK_PATTERNS)
    matches = detector.detect("the leak phrase that should fire")
    assert len(matches) >= 1


def test_my_pack_clean_text_returns_empty():
    detector = BreakDetector(patterns=MY_BREAK_PATTERNS)
    matches = detector.detect("a perfectly fine in-character response")
    assert matches == []


def test_my_pack_does_not_match_known_false_positive_case():
    """The pattern uses lookbehind to exclude **bold** etc."""
    detector = BreakDetector(patterns=MY_BREAK_PATTERNS)
    matches = detector.detect("the legitimate variant you took care to exclude")
    assert matches == []


def test_my_reinforcement_string_is_non_empty():
    assert MY_REINFORCEMENT
```

Run with `pytest tests/test_my_persona_pack.py -v`.

### When a pattern is added or changed

Add one positive and one negative test per pattern. The library's own
test suite (`tests/test_persona_detect.py`) shows the shape — short
focused tests, one assertion each, named after the failure mode.

### What NOT to test

- Do NOT test the implementation of `re.search()`. That's the standard
  library; assume it works.
- Do NOT test that compiled patterns are `re.Pattern` instances unless
  you are exporting a public pack — the library's
  `test_all_packs_are_compiled_patterns` covers the public surface.
- Do NOT test against live LLM responses in your unit tests. The whole
  point of regex detection is that it's deterministic and decoupled
  from the model. Live-response checks belong in eval suites, not in
  the pack's tests.

---

## 8. Pattern review checklist (before you ship)

Before merging a new pack to your codebase, walk through this checklist:

- [ ] Every pattern uses `(?i)` inline OR documents why it doesn't.
- [ ] Every keyword that could appear inside other words is bounded
      with `\b`.
- [ ] Every pattern that excludes a legitimate variant has a comment
      explaining what it excludes and why.
- [ ] Patterns are classified into the right detector class
      (break / soft / clarification dump).
- [ ] At least one positive and one negative pytest test per pattern.
- [ ] False-positive rate has been sanity-checked against ~10 real
      in-character responses from your bot.
- [ ] Reinforcement string is phrased as a directive, not a request,
      and tells the model *what to do*, not just *what not to do*.
- [ ] The pack file has a module docstring explaining the persona and
      when to use / not use it. (See `examples/` for the shape.)
