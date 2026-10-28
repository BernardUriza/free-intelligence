# OG118-ELEMENTOS-ALTA — dar de alta un elemento sin PR ni deploy

Status: In progress — option A merged (#602), CD fake-green fixed (#605), read/edit/delete/probe merged (#607); the UI moved onto fi-glass/persona-admin in #608 (open). Not yet verified with a real element on app.og118.ai.
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

Built 2026-10-28, both ends in one PR ([[both-ends-of-the-data-path]]):

- **server-bot (the voice).** Table `runtime_personas` (append-only, newest row per id wins), repository
  `persona_core/memory/repositories/runtime_personas.py`, runner module `engine/runtime_personas.py` that
  materializes each row as `<RUNTIME_PERSONAS_DIR>/<id>.md` plus an in-process registry entry (provider,
  model). The runner hydrates it at boot BEFORE serving and on every write. `resolve_persona_path`,
  `engine_for` and the runner pipeline read it after the image's own personas, which always win: an id the
  image owns (insult, astra…) is refused with 422. Write door: `PUT /v1/personas/{id}`, runner bearer.
- **og118 (the slot).** `elements.overlay.json` on the Azure Files volume, applied by the same
  `ElementsRegistry` (a claim may only turn an EMPTY slot active and may not steal an alias).
  `GET /elements/slots` (empty slots + `canCreate`) and `POST /elements`, which validates the claim, writes the
  persona to the engine first, then the slot. Authors: `OG118_ELEMENT_AUTHORS` = the sha256[:32] of the Auth0
  sub (the conversation store's owner hash), set in `og118-backend.yml`; unset = nobody.
- **The form.** "Nuevo elemento" at the foot of the element selector, only for an author; a full sheet on
  mobile, measured at 390 px (no overflow, 44 px targets, 16 px fields).

Tests: server-bot 2003 passed (incl. a real-Postgres repository test); og118 server 274; web 134.

**2026-10-28, later the same day.** Bernard: *"todo esto ya lo teníamos… vas a tener que deshacer todo lo que
hiciste y volverlo a hacer pero ahora subiéndolo al framework"*. The hand-built form was a reinvention: aurity
already had the whole persona admin (zod schema, form, create modal, tabbed editor with a probe tab, service
with list/get/create/update/delete/test). Rule written: `.claude/rules/framework-first-canary.md`, "grep aurity
FIRST" (#606).

- **#605** — server-bot CD was fake-green: `AZURE_CREDENTIALS` could not see og118-rg, `continue-on-error`
  hid it, and the verify step skipped an invisible app. Now OIDC + a hard check that the live image is the
  new SHA. That is why the first real create returned "Not Found".
- **#607** — runner `GET/DELETE /v1/personas/{id}` (delete = tombstone row), og118
  `GET /elements/{slug}/persona`, `PUT`, `DELETE`, `POST …/test` (probe as `probe-element-editor`,
  `origin=probe`).
- **#608** — `fi-glass/persona-admin` extracted from aurity, aurity renders it, og118 deletes
  `Og118ElementCreateDialog` and runs on it through a `PersonaStore` over `/elements`; "Editar mis
  elementos" in the selector. Mobile measured at 390×844: full sheet, 0 overflow, 44 px targets, 16 px fields.

What stays from the first build: the backend. aurity's own `backend/` is dead code, so the og118 store needs
the og118 + runner endpoints above. Only the og118 frontend was undone.

Next: merge #608, then create a test element on app.og118.ai (slot 117 Teneso), send it a real turn, edit,
probe and delete it, with no deploy in between. Phase 2 (aurity's model catalog → fi-glass) follows.
