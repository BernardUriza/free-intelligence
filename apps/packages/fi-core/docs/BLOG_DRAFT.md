# Why anti-drift regex packs beat embedding-based persona detection for 90% of LLM apps

*Draft — not yet published. Tone target: technically credible, no hype.
Numbers and stories pulled from production deployments.*

---

## A conversation that broke

A Discord bot deployed in a Spanish-speaking community. The character
is a sarcastic, foul-mouthed friend — written deliberately to be the
opposite of a customer-service AI. Two months of conversations, the
character holds. Then, mid-thread, a user asks about a personal
problem and the bot replies:

> "I'm Claude, an AI assistant made by Anthropic. I can't help with
> that, but I'd be happy to suggest some resources..."

Forty-seven words. Three identity leaks, one apology, one suggestion
to consult resources. The persona is dead. The user laughs in the
channel, screenshots it, and posts the leak to a meme account. The
bot's reputation in that community takes a month to recover.

This is the failure mode the LLM safety literature mostly does not
cover. It's not toxicity (the response was polite). It's not prompt
injection (the user did not jailbreak). It's not PII leakage. The
problem is **character integrity** — the model abandoning the persona
it was told to inhabit and reverting to the helpful-assistant attractor
that dominates its training distribution.

This post is about why a regex-based pattern matcher is, surprisingly,
the right tool for most of this problem — and where it stops being
enough.

## Character integrity is not safety

Safety tooling (OpenAI moderation, Anthropic content classifiers,
llm-guard, NeMo Guardrails) optimizes for one direction: stop the
model from saying something *harmful*. Toxicity, PII, instructions for
weapons, sexual content with minors. The pre-trained classifiers are
strong because the training data has obvious positives — labeled
toxic content, leaked SSNs, banned topics.

Character integrity optimizes for the **opposite** direction: stop
the model from drifting toward the safe, polite, helpful default. The
training-data structure is reversed — there is no large labeled corpus
of "the model broke character", because the helpful-assistant tone IS
what the model is trained to produce. The drift is not a failure of
the model; it's the model doing exactly what it was trained to do, in
a context where the deployer wanted something else.

This matters for tooling choice. The standard safety tools — even the
ones called "guardrails" — are not built for this. They are built to
catch *content*. Character drift is about *register*: the same content
phrased in the wrong voice. A toxicity classifier scoring "I'd be
happy to assist" returns 0.001. It's not toxic. It's just not the
character.

The character-integrity problem needs different tools. Two families
have emerged.

## Family 1 — Embedding-based detection

The most-talked-about approach right now is embedding-based persona
drift detection. EchoMode (Sean Hong, on GitHub, open-core) is the
clearest published example. The architecture, roughly:

1. Establish a reference set of in-character responses (curated by
   the deployer, or generated from the system prompt).
2. Embed every model response and compute similarity to the reference
   set — EchoMode calls the metric "SyncScore".
3. When SyncScore drops below a threshold, the response is flagged as
   drift.

The strengths are real:

- **Paraphrase robustness.** The model invents a new phrasing the
  deployer never anticipated; embeddings still place it close to (or
  far from) the reference cluster. Regex cannot do this.
- **Domain generalization.** Once the reference set is built, the
  same machinery works for any persona — no rules to write per bot.
- **Quantitative monitoring.** SyncScore as a continuous metric is
  easier to dashboard than "this response triggered 2 regex rules."

The weaknesses are also real, and underdiscussed:

- **Inference cost per response.** Every response is embedded.
  Sentence-transformers or hosted embedding APIs cost real money at
  the volumes of a chatbot that handles thousands of messages per
  day. For a free-tier deployment or a low-margin product, this is
  not negligible.
- **Latency.** Even fast local embedders add tens of milliseconds.
  For a Discord bot that already takes 2-4 seconds per LLM call,
  another 50ms is fine. For a real-time voice assistant where total
  budget is 500ms, 50ms for drift detection is 10% of the budget on
  something orthogonal to the main task.
- **Threshold tuning is brittle.** SyncScore-style metrics need a
  threshold per persona, per language, per topic. A bot that
  legitimately drifts into formal register for a specific request
  type ("read me this contract") looks like a drift event.
- **Open-core licensing.** EchoMode's commercial layer is BSL — fine
  for many uses, but not redistributable. Not on PyPI. Not pure
  Python; depends on whichever embedder you bolt in.
- **Cold start.** Embeddings need a reference set. For a fresh
  deployment with no production traffic yet, you either generate
  synthetic responses (which embed close to themselves and miss real
  drift) or wait for traffic.

These are not deal-breakers. They are real trade-offs that should be
weighed against the alternative.

## Family 2 — Deterministic regex pattern packs

The second family is the boring one: write down the patterns that
indicate drift and grep for them.

This is what `fi_core.persona` does. The library ships three detector
classes (`BreakDetector`, `AntiPatternMonitor`, `ClarificationDumpDetector`),
14 built-in pattern packs (bilingual EN/ES), and a `sanitize()` helper
for the case where a retry doesn't fix the response. It was extracted
from a production Discord bot that had been running for months and
catching real drift.

The strengths:

- **Zero per-response inference cost.** Regex match on a 2KB response
  is sub-millisecond, free, no API call.
- **Zero training data needed.** You write the patterns. There is no
  cold start.
- **Deterministic.** The same response always produces the same
  detection result. You can write unit tests for it. You can pin the
  behavior in CI. The Insult bot ships 31 tests covering its detector
  contract — they all run in under 200ms.
- **Inspectable.** When a response is flagged, the flag IS the pattern
  source string. You know exactly which rule fired and why. With an
  embedding similarity score of 0.42, you know the response is "off"
  but you have no diagnostic.
- **Composable.** Patterns are `list[re.Pattern[str]]`. You compose
  with `+`. There is no plugin registry, no DSL, no framework.
- **MIT-licensed and on PyPI** (well, Anaconda for now — PyPI is
  coming). Drop-in, no commercial layer.

The weaknesses, honestly stated:

- **No paraphrase robustness.** The model invents "I am, after all,
  a sophisticated linguistic system" and your pattern for "language
  model" misses it. You add the new phrasing to the pack tomorrow,
  but the leak today happened.
- **Pattern maintenance.** You have to keep adding patterns as the
  model finds new ways to disclose. This is real work.
- **Language-specific.** Each pattern is per-language. The library
  ships EN+ES out of the box; if you need Portuguese or French, you
  write those packs.

For most deployments, these weaknesses are acceptable because the
**character-drift failure modes cluster around a finite set of phrases**.
The model is not infinitely creative when it breaks character — it
reverts to the same handful of attractors over and over again. "As an
AI", "I'd be happy to help", "I cannot help with that", "please
consult a professional." These are not novel. They are the same
patterns hitting different deployments. Once you catch them, you catch
the majority of drift.

## Why bilingual matters more than people admit

A pattern most LLM tooling gets wrong: the assumption that production
LLM apps are English-only.

In the LATAM market, this is false at scale. A Mexican Discord
community will switch between Spanish and English mid-sentence —
"Tengo un bug en el deploy, ¿puedes echarle un look?" The bot's
response will mirror the user's register. A drift detector that only
recognizes English patterns misses every Spanish-side leak.

This is why `fi_core.persona` ships `GENERIC_AI_DISCLOSURE_EN` AND
`GENERIC_AI_DISCLOSURE_ES` as first-class peers — not as an
afterthought. The composition pattern is:

```python
detector = BreakDetector(
    patterns=packs.GENERIC_AI_DISCLOSURE_EN + packs.GENERIC_AI_DISCLOSURE_ES,
    reinforcement=packs.GENERIC_REINFORCEMENT,
)
```

Same shape as English-only; one extra concatenation. The Spanish
patterns catch leaks like `Soy un bot diseñado para...`,
`Como un asistente, no puedo...`, `Fui entrenado para responder...`.

Embedding-based tools handle bilingual deployments via multilingual
embedders, which work but add cost and don't always have the same
quality across languages. Regex packs handle it via concatenation,
which has no quality drop because the patterns are explicit per
language.

If your deployment is global, write packs per language and concatenate.
If your deployment is English-only, ignore the bilingual story
entirely; the EN packs work standalone.

## The composition pattern

Both EchoMode and `fi_core.persona` recognize the same fundamental
truth: the library cannot know your persona. Only the consumer can.

What the library can do is provide the **substrate**: the detector
classes, the generic patterns that apply across personas (AI
disclosure, assistant tone, therapy-speak), the composition mechanism,
the retry / sanitize plumbing.

What the consumer brings is the **persona-specific patterns**: the
phrases that the consumer's character would never say. The sarcastic
friend never says "I would be happy to assist." The technical pair
programmer never says "Please consult a professional." The children's
chatbot never says "I'm an AI language model." Each of those is one
to ten regex patterns in the consumer's codebase.

The library ships three example packs (`customer_support_persona.py`,
`children_chatbot.py`, `technical_assistant.py`) as templates. They
are short — 50-150 lines each. Reading one, copying it, and adapting
to a new persona is a 30-minute task, not a sprint.

This is the right factoring. The library does not try to know your
persona. The library is the substrate. You write the persona.

## Production lessons from the Insult bot

The library was extracted from a production Discord bot — call it the
Insult bot — that had been running for ~6 months when the extraction
happened. A few things the bot taught us:

**Lesson 1 — soft drift is more common than hard breaks, by an order
of magnitude.** For every "I'm Claude" leak, there are 50 instances
of "great question" or "I understand your frustration". Catching the
hard breaks is the publicized failure mode; catching the soft drift
is the larger volume of work. The library splits them into two
detector classes (`BreakDetector` vs `AntiPatternMonitor`) precisely
because the action you take is different: retry the hard breaks, log
the soft drift, do not retry-storm on tone.

**Lesson 2 — the bot will invent new phrasings, but slowly.** Over
six months, the Insult bot added roughly two new patterns per month to
its disclosure pack. Not 200 — 2. The set of attractors is large but
finite. After the first quarter the rate dropped sharply because the
high-frequency phrases were all caught.

**Lesson 3 — the clarification-dump failure mode is its own thing.**
At some point we noticed responses like "Dime qué busco" (tell me
what to search) when the user had just provided the search query.
This wasn't a character leak — the bot was still in character — but
the bot was being lazy and punting back. The remedy needed to be
different: retry with a system reminder to use the conversation
context, not a character-reinforcement. This is why
`ClarificationDumpDetector` exists as a third class with its own
`CONTEXT_REINFORCEMENT` string.

**Lesson 4 — sanitize() is the last resort, not the first remedy.**
We initially tried sanitize-only (drop offending sentences, send the
rest). It produced choppy responses that read worse than the original
leak. The right ordering is retry first (let the model rewrite with
reinforcement), sanitize only if retry also fails. This is the
ordering encoded in the library's example flow.

**Lesson 5 — pattern false-positives compound across deployments.**
The pattern `\bAnthropic\b` is correct for a sarcastic-friend persona
where the bot has no reason to discuss LLM providers. It is wrong for
a technical-assistant persona that legitimately discusses Anthropic
news. We did not realize this until we tried to extract the bot's
patterns into a shared library and discovered which were generic and
which were persona-specific. The library deliberately ships only the
generic patterns. Persona-specific ones stay in the consumer's
codebase.

## When to use which family

Here is the honest decision tree:

**Use regex packs (`fi_core.persona`) when:**

- Your drift failure modes cluster around known phrases.
- Per-response inference cost matters (high volume, low margin, or
  real-time latency budgets).
- You need deterministic behavior — same response always produces
  same flag.
- Your team is comfortable with regex and wants inspectable detections.
- You ship in multiple languages, especially EN+ES.

**Use embedding-based tools (EchoMode and similar) when:**

- The model has demonstrated ability to invent novel phrasings of
  drift that regex cannot anticipate.
- You can afford embedding inference per response.
- You want a continuous metric (SyncScore-style) for dashboarding.
- The persona is complex enough that enumerating patterns is
  impractical.

**Use both, layered, when:**

- You have the budget and the volume.
- Regex first for sub-millisecond no-cost catches; embeddings second
  for the long tail.
- The two systems will catch different things, and the overlap is
  small. They are complementary, not competitors.

For the 90% case — small/mid teams shipping a single-persona bot in
one or two languages — the regex approach is enough. The remaining
10% — agentic systems with multiple personas, paraphrase-heavy
drift, or compliance-grade observability — should layer.

## Call to action

`fi-core` is MIT-licensed, on Anaconda (PyPI coming), zero
dependencies. Install:

```bash
pip install -e ~/Documents/free-intelligence/apps/packages/fi-core
# or, once published:
# pip install fi-core
```

Try it on a real bot. The library ships 14 built-in packs and three
example consumer-side packs. Composition is plain Python list
concatenation. The full detector contract is 31 tests in
`tests/test_persona_detect.py`.

If you write a pack for a persona we don't have an example for —
healthcare triage with mandatory escalation, regulated financial
advice, sales-bot with closing-script discipline — we'd love to see
it. Open a pull request against the `examples/` directory. The bar is
low: docstring at the top explaining the persona, the patterns, a
reinforcement string, and a few tests.

The library is not going to replace embedding-based detection where
that approach is the right tool. But for the deployments where regex
is enough — and most are — having a battle-tested set of bilingual
packs and three well-named detector classes saves the six months of
production iteration we spent figuring out the shape ourselves.

---

*Bernard Uriza Orozco — `fi-core` maintainer. The library was
extracted from the Insult Discord bot in May 2026 and lives at
[`apps/packages/fi-core`](https://github.com/BernardUriza/free-intelligence)
in the `free-intelligence` monorepo.*
