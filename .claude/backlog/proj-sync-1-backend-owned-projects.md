# PROJ-SYNC-1 — backend-owned project hydration (localStorage → cache, not source of truth)

Status: Proposed
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
