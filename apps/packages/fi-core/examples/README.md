# fi_core.persona — Example pattern packs

This directory contains reference implementations showing how to write a
custom pattern pack for a specific persona use case. Use them as templates
for your own packs — copy one, rename it, tweak the patterns + reinforcement
string to fit your bot's character, and compose with the built-in packs
shipped under `fi_core.persona.packs`.

The library deliberately ships only patterns that generalize across personas
(`GENERIC_AI_DISCLOSURE_EN/ES`, `ASSISTANT_TONE_EN/ES`, etc.). Patterns that
are specific to a single bot's character or domain belong in the consumer's
codebase, merged with the generic packs at composition time. The examples
below show the shape of that consumer-side code.

## Available examples

| File | Persona | Use case |
| --- | --- | --- |
| [`customer_support_persona.py`](./customer_support_persona.py) | Customer-support agent | Catch the bot punting users to administrators / ToS / "outside my scope" instead of helping. |
| [`children_chatbot.py`](./children_chatbot.py) | Children's chatbot | Catch profanity, violence, philosophical despair, AI-identity disclosures, and adult-formality drift. |
| [`technical_assistant.py`](./technical_assistant.py) | Pair-programming assistant | Catch "consult a professional" / "I cannot give legal-medical-financial advice" dodges on technical questions. |

## How to wire one in

Each example file exports one or more `list[re.Pattern[str]]` constants and
a reinforcement string. Composition is a one-liner:

```python
from fi_core.persona import BreakDetector, packs
from examples.customer_support_persona import (
    CUSTOMER_SUPPORT_BREAK_PATTERNS,
    CUSTOMER_SUPPORT_REINFORCEMENT,
)

detector = BreakDetector(
    patterns=packs.GENERIC_AI_DISCLOSURE_EN + CUSTOMER_SUPPORT_BREAK_PATTERNS,
    reinforcement=CUSTOMER_SUPPORT_REINFORCEMENT,
)
```

Lists of compiled patterns concatenate with `+`. There is no registry, no
plugin system, no DSL — composition is plain Python.

## Writing your own

See the `## Writing your own pack` section in the top-level
[`README.md`](../README.md) and the long-form authoring guide at
[`docs/PATTERN_AUTHORING.md`](../docs/PATTERN_AUTHORING.md) for
conventions on boundaries, case sensitivity, false-positive avoidance,
and severity-tier decisions.
