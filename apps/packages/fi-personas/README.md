# fi-personas — shared persona source of truth

The single home for personas that more than one surface speaks. A persona's
**core** (method, tone, knowledge, identity lock) lives here ONCE; each consumer
surface (og118 element, the Discord bot, a future shell) injects only its own
small **operative-context** block. This kills the drift that happens when the same
character is copied per repo and edited independently (PERSONA-SSOT-1).

## Layout

```
personas/
  <name>.core.md     # the shared core, with a <!-- CONTEXTO_OPERATIVO --> marker
```

The core carries everything common; the marker is where a consumer splices its
environment-specific context (where the persona "lives", what it can touch). A
consumer composes its full system prompt as:

```
core.replace('<!-- CONTEXTO_OPERATIVO -->', <consumer operative-context block>)
```

## Consumers

- **og118** — element `O · Oxígeno` composes `vultur.core.md` + its own
  `008-o-oxigeno.context.md` (the first consumer / canary).
- **discord-bot** — `vultur` persona (separate repo) adopts the same
  `vultur.core.md` + its Khimeras context block. Cross-repo consumption (publish /
  submodule) is decided in ENGINE-BINDING-ADR-1; until then og118 is the canary
  proving the SSOT shape.

## Why not proxy one surface to another

A persona is shared *content*; a surface (og118, the Discord bot) is not an engine.
The right move is to extract the persona beneath both surfaces, not to make one
surface call the other at runtime. See `apps/og118/ENGINE-BINDING-ADR-1.md`.
