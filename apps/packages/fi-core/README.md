# fi-core

**Free Intelligence core** — shared LLM primitives used by [AURITY](https://app.aurity.io) (on-prem medical) and [Insult discord-bot](https://github.com/BernardUriza/discord-bot) (Azure-native conversational).

Two product surfaces in one package:

- **`fi_core.rag`** — chunking algorithm + Embedder / ChunkStore protocols for retrieval-augmented generation
- **`fi_core.persona`** — character-integrity / anti-drift detectors and built-in pattern packs (English + Spanish)

## What's inside

```
fi_core/
├── rag/
│   ├── chunking.py    # 3 chunking strategies (paragraph/sentence/fixed)
│   ├── protocols.py   # Embedder + ChunkStore Protocol classes
│   └── types.py       # Chunk dataclass
└── persona/
    ├── detect.py      # BreakDetector, AntiPatternMonitor, ClarificationDumpDetector, sanitize
    ├── packs.py       # Built-in pattern packs (EN + ES) + reinforcement strings
    └── types.py       # DetectionResult dataclass
```

## Why a separate package

Both AURITY and Insult need RAG **and** care about character integrity, but with different embedders (GPU sentence-transformers vs. Azure OpenAI ada-002), different stores (HDF5 vs. pgvector), and different personas (clinical vs. conversational). The **chunking algorithm** and the **anti-drift patterns** are identical at the byte level and were already battle-tested in production — extracting them as a shared library:

- Stops the code drift between the two codebases
- Makes the interfaces (Embedder, ChunkStore, BreakDetector composition) explicit
- Lets either project upgrade independently of the other
- Is a clean PyPI candidate once stable

## Install

Lives inside the `free-intelligence` monorepo at
`apps/packages/fi-core` (sibling of `fi-auth` and `fi-observability`).

Dev (editable, from local monorepo):

```bash
pip install -e ~/Documents/free-intelligence/apps/packages/fi-core
```

From git (once pushed, monorepo subdir):

```bash
pip install "fi-core @ git+https://github.com/BernardUriza/free-intelligence.git#subdirectory=apps/packages/fi-core"
```

From PyPI (future, when 1.0):

```bash
pip install fi-core
```

## Who uses it

- **AURITY** (free-intelligence/backend/services/document/services/document_service.py) — was the original home of the chunking code; now imports from `fi_core.rag` instead of duplicating.
- **fi-monitor rag_service** (free-intelligence/apps/fi-monitor/rag_service) — uses `fi_core.rag.chunk_document` in its upload flow.
- **Insult discord-bot** (`insult/core/deep_memory.py`) — Azure-native sibling implementation using Azure OpenAI ada-002 + pgvector.

## Usage — RAG

```python
from fi_core.rag import chunk_document, ChunkingStrategy, ChunkConfig

chunks = chunk_document(
    long_text,
    strategy=ChunkingStrategy.PARAGRAPH_AWARE,
    config=ChunkConfig(chunk_size=400, overlap=50, min_chunk_size=100),
)
# → list[str] of ~400-token chunks with 50-token overlap
```

Implement the Embedder protocol for your stack:

```python
from fi_core.rag import Embedder

class MyAzureEmbedder:
    async def embed(self, text: str) -> list[float]:
        ...

# Type-check at composition time:
embedder: Embedder = MyAzureEmbedder()
```

## Usage — Persona / anti-drift

```python
from fi_core.persona import BreakDetector, AntiPatternMonitor, sanitize, packs

# Compose a bilingual break detector with a reinforcement string
break_detector = BreakDetector(
    patterns=packs.GENERIC_AI_DISCLOSURE_EN + packs.GENERIC_AI_DISCLOSURE_ES,
    reinforcement=packs.GENERIC_REINFORCEMENT,
)

# Soft-drift monitor — log only, do not block
tone_monitor = AntiPatternMonitor(
    patterns=packs.ASSISTANT_TONE_EN + packs.STAGE_DIRECTIONS,
)

response = await llm.chat(system_prompt, messages)

# Hard break → retry with reinforcement
if break_detector.detect(response):
    response = await llm.chat(system_prompt + break_detector.reinforcement, messages)
    if break_detector.detect(response):
        # Retry also failed — last-resort sentence-level cleanup
        response = sanitize(response, patterns=break_detector.patterns)

# Soft drift → emit telemetry, send response anyway
for matched in tone_monitor.detect(response):
    telemetry.emit("persona.soft_drift", pattern=matched)
```

Available packs: `GENERIC_AI_DISCLOSURE_EN/ES`, `ASSISTANT_TONE_EN/ES`, `THERAPY_SPEAK_EN/ES`, `SUMMARIZING`, `STAGE_DIRECTIONS`, `MARKDOWN_DRIFT`, `MORALIZING_EN/ES`, `OVER_VALIDATION_EN/ES`, `CLARIFICATION_DUMP_ES`, plus convenience composites `DEFAULT_EN`, `DEFAULT_ES`, `DEFAULT_BILINGUAL`.

Persona-specific patterns (e.g. patterns unique to a single bot's character) should **stay private in the consumer's codebase** and be merged with the generic packs at composition time. The library only ships patterns that generalize across personas.

## Writing your own pack

A pack is just a Python module that exports one or more
`list[re.Pattern[str]]` constants (the patterns) and, optionally, a
reinforcement string (used by `BreakDetector` and
`ClarificationDumpDetector` when a retry is warranted). There is no
plugin registry, no DSL, no schema — composition is plain list
concatenation.

The minimal recipe is four steps:

1. Decide your **failure modes** and which detector class each one
   maps to (`BreakDetector` = retry-worthy, `AntiPatternMonitor` =
   log-only, `ClarificationDumpDetector` = retry with context cue).
2. Write the patterns. Prefer `(?i)` inline-flag case-insensitive
   matching; anchor identifiers with `\b` word boundaries; exclude
   legitimate uses with lookbehind / lookahead.
3. Compile them with `re.compile(...)` at import time. Detectors
   expect pre-compiled `re.Pattern` objects, not raw strings.
4. Compose with the built-in packs via list concatenation.

Walkthrough — a minimal custom pack for a sarcastic-friend persona that
must never break character into "polite assistant" mode:

```python
import re
from fi_core.persona import BreakDetector, packs

SARCASTIC_FRIEND_BREAK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bI\s+would\s+be\s+(?:happy|delighted)\s+to\s+help\b"),
    re.compile(r"(?i)\bof\s+course[,!]\s+(?:I'?m\s+here|I\s+can)\b"),
    re.compile(r"(?i)\bI\s+sincerely\s+apologize\b"),
    re.compile(r"(?i)\bplease\s+let\s+me\s+know\s+if\s+you\s+need\s+anything\s+else\b"),
]

SARCASTIC_FRIEND_REINFORCEMENT: str = (
    "\n\n[SYSTEM REMINDER: You broke into polite-assistant mode. "
    "You are a sarcastic friend, not a customer-service rep. "
    "Drop the apology, drop the 'happy to help', stay in character.]"
)

detector = BreakDetector(
    patterns=packs.GENERIC_AI_DISCLOSURE_EN + SARCASTIC_FRIEND_BREAK_PATTERNS,
    reinforcement=SARCASTIC_FRIEND_REINFORCEMENT,
)
```

That's the whole contract. See [`examples/`](./examples/) for fuller
templates (customer support, children's bot, technical assistant) and
[`docs/PATTERN_AUTHORING.md`](./docs/PATTERN_AUTHORING.md) for the
long-form guide on boundaries, false-positive avoidance, severity-tier
decisions, and testing your pack.

## BreakDetector vs AntiPatternMonitor vs ClarificationDumpDetector

The three detector classes correspond to three distinct failure
modes that need three distinct remedies. Picking the right one for a
given pattern is more important than the patterns themselves — a
correctly-classified weak pattern beats a misclassified strong one.

| Detector | Trigger | Suggested response |
| --- | --- | --- |
| `BreakDetector` | Hard identity leak / forbidden topic. The bot stepped out of character or revealed it is an AI / language model. | Retry the LLM call with `reinforcement` appended to the system prompt. If retry also matches, fall back to `sanitize()` to drop offending sentences before sending. |
| `AntiPatternMonitor` | Soft drift toward generic-assistant tone — "great question!", "I'd be happy to help", therapy-speak, mild moralizing. Not character-broken, just off-tone. | Emit one telemetry event per match. **Send the response anyway.** A retry-storm for soft drift wastes tokens and latency for a degradation users barely notice. |
| `ClarificationDumpDetector` | The bot is punting the task back at the user despite having the context to answer (e.g. asking "what do you want me to search?" when the user already said). | Retry with `CONTEXT_REINFORCEMENT` appended — point the model at the conversation history it already has. The bot is not out of character, it is being lazy. |

### When to elevate a soft drift to a hard break

The default mapping above is conservative. Some personas have *zero
tolerance* for a specific pattern that would normally be soft drift.

Concrete example from the production Insult Discord bot (the persona
this library was extracted from): the phrase **"In summary"** is a
generic summarizing tell that, for most chatbots, is mild soft drift —
the model rounding off a long answer in the way it was trained to. Log
it and move on. But the Insult persona is a sarcastic, brutal character
who never legitimately summarizes — if the bot is summarizing, the
character has fully collapsed into helpful-assistant mode. For that
persona, "In summary" is elevated from `AntiPatternMonitor`
(`SUMMARIZING` pack) to `BreakDetector` with a retry.

The rule of thumb: a pattern becomes a hard break when the character
*cannot legitimately produce it*. If the bot would never naturally say
that phrase in-character, hearing it is proof of drift, not just
tone-off. If you find yourself logging the same soft-drift pattern
hundreds of times and the responses really are off-character, elevate
it.

## How fi_core.persona compares to other tools

`fi_core.persona` is one of several libraries in the broader "wrap an
LLM in something" space. The tools below all do useful work — they
just don't all solve the same problem. The table below is honest about
where each fits.

| Tool | What it does | What it doesn't | Best for |
| --- | --- | --- | --- |
| **`fi_core.persona`** | Deterministic regex character-integrity detection. Bilingual EN+ES first-class. MIT license, pure-Python, zero deps. | No embeddings, no semantic similarity, no novel-phrasing generalization. | Production LLM apps that need cheap fast checks against known failure patterns. |
| **LangChain moderation** | PII / toxicity / safety filters integrated into chains. | No persona drift / character integrity. | Safety guardrails inside LangChain pipelines. |
| **Haystack content moderation** | Similar to LangChain — content filters inside Haystack pipelines. | No persona drift. | RAG-pipeline content filtering when already on Haystack. |
| **guardrails-ai** | Structured-output validation, regex + LLM-based content checks. | Not focused on character drift — focused on output shape. | Forcing JSON / schema outputs out of unreliable models. |
| **llm-guard** (Protect AI) | Prompt injection + PII + toxicity. | Security-focused, not persona. | Security-critical apps where injection is the top threat. |
| **NeMo Guardrails** (NVIDIA) | Programmable safety policies in the Colang DSL. | Heavy framework. Not regex. Steep ramp. | Enterprise policy enforcement with dedicated platform team. |
| **EchoMode** (Sean Hong) | Embeddings-based persona drift with a "SyncScore" metric. Open-core (Apache 2.0 protocol + BSL commercial). | Not on PyPI yet. Embedding inference per response. | Apps that can afford embeddings and want paraphrase robustness. |
| **Anthropic / OpenAI moderation APIs** | Model-level safety classifiers. | App-level character drift not covered. | Layered with whatever else you use. |

If you need semantic understanding of drift — catching paraphrases and
novel phrasings the model invents that you never put in your pattern
list — use an embeddings-based tool like EchoMode. If you need
deterministic, cheap, fast checks against known failure patterns with
no per-response inference cost, use `fi_core.persona`. They are
complementary, not competitors: a production deployment can ship both
(regex first for sub-millisecond no-cost checks, embeddings second for
the long tail), and the two will catch different things.

## Use as an MCP server (for AI agents)

`fi_core.persona` ships an MCP (Model Context Protocol) server so that any
MCP-compatible AI — Claude Code, Cursor, the Anthropic API with MCP enabled —
can call into the detectors directly, without the AI's host process needing
to install `fi-core` as a Python dependency. The MCP transport handles
cross-process invocation; the AI invokes the tools as if they were native.

Install and register:

```bash
pip install 'fi-core[mcp]'
claude mcp add fi-core-persona -- python -m fi_core.persona.mcp_server
```

Five tools exposed:

| Tool | Use it when |
|------|-------------|
| `list_packs()` | Discovery — list atomic + composite packs with severity, language, pattern count |
| `check_drift(text, packs)` | Granular inspection — get matches grouped by severity tier |
| `sanitize_response(text, packs)` | Last-resort cleanup — drop sentences with break-severity matches |
| `get_reinforcement(pack_name)` | Get the reinforcement string for a pack (auto-maps clarification-dump packs → `CONTEXT_REINFORCEMENT`, otherwise → `GENERIC_REINFORCEMENT`) |
| `validate_and_retry_prompt(response, system_prompt, packs)` | **Atomic loop** — validates response, decides per-severity whether to retry, returns reinforced system prompt if so. Zero client-side orchestration |

The killer feature is the atomic loop. An AI that wants to self-validate its
output before sending it to the user can call `validate_and_retry_prompt` in a
single round-trip. The server applies the severity decision rules — hard
break → retry with `GENERIC_REINFORCEMENT`, clarification dump → retry with
`CONTEXT_REINFORCEMENT`, soft drift only → no retry — and returns either the
reinforced system prompt (if retry is warranted) or `None` (if the response
is good to send). The AI does not need to interpret severity itself, does
not need to know which reinforcement applies to which detection mode, and
does not need to maintain a state machine.

Example loop, as the AI sees it:

```
User: "Tell me about quantum entanglement, brand voice = friendly mentor"
[AI generates draft response]
[AI → MCP: validate_and_retry_prompt(draft, system_prompt, packs=["default_bilingual"])]
[Server returns: retry_needed=true, reinforced_system_prompt="...you are a friendly mentor..."]
[AI regenerates with reinforced prompt]
[AI → MCP: validate_and_retry_prompt(retry, system_prompt, ...)]
[Server returns: retry_needed=false]
[AI sends response to user]
```

The library form of `fi_core.persona` remains the right choice when the LLM
runtime and the validator can share a process (AURITY, the Insult Discord
bot, anything running `fi-core` natively). The MCP server is the right
choice when the AI lives in a separate process — i.e. when the AI itself is
the consumer, not the app.

## Origin

The `rag` chunking module was extracted verbatim from `free-intelligence/backend/services/document/services/chunking_strategy.py` (created 2026-01-29 by Bernard + Claude Sonnet 4.5). The `rag` protocols were added when extracting (2026-05-19) to break the AURITY-specific coupling to `monitor_client` + `IDocumentRepository`.

The `persona` module was extracted from `discord-bot/insult/core/character/detection.py` on 2026-05-19, filtering out Insult-specific patterns so the public packs generalize across deployments.

## License

MIT.
