# PROJ-SYNC-1 — backend-owned project hydration (localStorage → cache, not source of truth)

Status: **Done** — el servidor es la fuente de verdad; falta sólo el flag de staleness (verificado 2026-08-22)
Proposed: 2026-06-21 by Bernard (via coagent adversarial review of the identity-scoping leak fix)

## What it is

After Gate 3 (Auth0), og118's Projects list must hydrate from the **owner-filtered
backend registry** (`GET /projects`, already implemented + owner-gated via
`ProjectRegistry.list_for(principal.sub)`), instead of trusting `localStorage` as
the source of truth. The identity-scoping fix (this session) closed the
shared-device LEAK by namespacing the client store per account, but it did NOT
close the **client↔server drift**: `localStorage` is still authoritative on the
client and the front never calls `GET /projects`.

Drift risks the fix does NOT cover (the coagent's adversarial review):
- a user on a **different browser** sees none of their projects (local-only list);
- `localStorage` shows a project the server already **deleted**;
- `localStorage` keeps a project whose **corpus no longer exists** server-side;
- the backend returns 404 for a stale corpus and the UI has no reconciliation.

## Canonical path to reuse (Art. 6)

The server side already exists — `GET /projects` (owner-filtered) in
`apps/og118/server/app.py`. This is purely a **consumer** change in
`apps/og118/web/lib/useOg118Projects.ts`: on login, fetch the server list and make
`localStorage` a cache, not the truth. No new backend, no new framework primitive
(the identity-scoping primitive `fi-glass/identity` already shipped).

## Acceptance criteria (from the review)

- on login / mount with a real identity, call `GET /projects` and reconcile;
- `localStorage` becomes a cache layer, not the source of truth;
- if the backend says a project is missing or not owned → remove it locally;
- if the backend has a project the local cache lacks → hydrate it locally;
- handle offline gracefully (fall back to cache, flag staleness);
- a backend 404 for someone else's corpus is handled with NO leak in the UI.

## Status / next step

Not built yet. Deliberately scoped OUT of the urgent leak-fix PR (the leak is
closed by per-identity partitioning; this is the durable correctness model on top).
Unblocked now that Gate 3 + `PROJ-ACCOUNT` ownership are live. Promote to *In
progress* when Bernard greenlights the Projects-sync arc.

Related: [[og118-projects-papeleria-business]], [[gate3-auth0-google]].

## Cierre verificado (2026-08-22)

`apps/og118/web/lib/useOg118Projects.ts` se reescribió server-owned y su propio
docstring cita esta tarjeta (`:3`).

- Hidratación: efecto en `:135` que hace `GET /projects` con `authHeaders()`
  (`:157`), **esperando a `tokenReady`** (`:152`) para no correr la carrera del
  401. El servidor responde filtrado por dueño: `server/app.py:820` →
  `registry.list_for(principal.sub)`.
- localStorage quedó como **caché**: pinta al instante (`:142`) y luego la lista
  del servidor la **reemplaza** entera (`:166`); si el activo ya no existe del
  lado del servidor, se suelta la selección (`:170`).
- Offline no destruye nada: `catch { }` en `:183` conserva la caché.
- Sin fuga entre cuentas: las llaves van particionadas con
  `scopedStoreName(base, userId)` (`:72`), más un barrido único de las llaves
  peladas de antes del scoping (`:126`).
- `deleteProject` ya es server-side (`:214`), tratando el 404 como éxito — se
  acabó el corpus huérfano que dejaba el borrado local.
- Tests: `web/lib/__tests__/useOg118Projects.test.ts`, 13 casos, incluido
  *"server list REPLACES a stale local cache"* y *"an account never sees another
  account's server projects"*.

**Lo que falta, y es lo único:** el *flag de staleness*. Existe `ready` (`:37`)
pero no una señal de "esto que ves es caché, todavía no reconcilia", así que un
render offline es indistinguible de uno ya reconciliado. Queda anotado aquí en
vez de fingir el 100%.
