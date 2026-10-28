# OG118-ELEMENTOS-ALTA — dar de alta un elemento sin PR ni deploy

Status: Proposed
Proposed: 2026-10-28 by Bernard (*"¿por qué og118 no tiene para agregar elementos nuevos?"*), right after element 85 Ástato needed a four-surface PR (#600) to exist.

## What it is

Today an element is born only through code. Measured on PR #600:

1. `apps/og118/server/elements/elements.registry.json` — the slot goes `active` with its `engineBinding.personaId`. The file is baked into the `og118-server` image, so it needs a deploy.
2. `apps/server-bot/shared/personas/<id>.md` + an entry in `shared/personas/registry.py` — the voice. Baked into the `persona-runner` image by `infra/azure/runner.Dockerfile`, so it needs a second deploy.
3. A non-Claude provider also needs `Persona.provider`/`model` in that registry.

No endpoint, no UI and no store writes any of that at runtime. That is by decision, not by omission:
`OG118-ELEMENTS-ADR-1` D1 says filling a slot is manual curation, and PERSONA-SSOT-2 (2026-09-10) says a
persona's prompt lives in server-bot and nowhere else, because og118's copy of Vultur had drifted to 96
lines against 205 live.

## Canonical path to reuse (Art. 6)

- The slot catalog already validates cap, uniqueness and status at load (`elements_registry.py`). A runtime
  overlay would be the same validator over a second source, never a second validator.
- `persona_files.resolve_persona_path` + `load_prompt` (mtime-aware) already hot-reload a persona from disk.
  A persona written to a durable volume the runner mounts would reload without a deploy.
- AIRE casitas already hold a persona as `CLAUDE.md` (and, since PR #600, `AGENTS.md` for Codex).

## The decision that is Bernard's

Where a runtime-created persona prompt lives. Two shapes, each keeps ONE source of truth:

- **A.** server-bot gains a durable persona store (Postgres row or Azure Files) that `load_persona` reads
  before the image's `/app/personas/`; og118 gets `POST /elements` that claims an empty slot and writes the
  prompt there. PERSONA-SSOT-2 holds: the prompt still lives on server-bot's side.
- **B.** Keep curation as code, and make the PR the UI: an og118 form that opens the four-surface PR for him
  to merge. Zero runtime state; every element stays reviewable in git.

## Status / next step

Proposed. Nothing built. Waiting on the A/B fork above.
