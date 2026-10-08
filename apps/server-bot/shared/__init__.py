"""Shared modules between Insult and ALICE bots.

Both bots live in the same monorepo and have grown duplicated infrastructure
(text chunking, retry policies, structlog setup, ...). This package is the
canonical home for the cross-bot primitives.

Design rules:

1. NO provider-unifying wrappers. Insult uses Anthropic, ALICE uses OpenAI;
   their SDK exceptions and tool schemas don't unify cleanly. The shared
   layer is for timing math, text formatting, IO, and data plumbing — never
   for hiding which LLM is talking.

2. Hooks over inheritance. When two bots need the same primitive but with
   diverging side effects (DB pool pre-warm, structlog processors), expose
   the difference as a callable parameter instead of subclassing.

3. Tests live in `tests/shared/`, run independent of either bot's container.
   The coverage gate for this directory is higher than the project-wide
   floor because a bug here affects two production bots at once.

`shared/` is not separately versioned. Breaking changes here require a
coordinated bump of both `insult/__init__.py` and `alice/__init__.py` in
the same PR.
"""
