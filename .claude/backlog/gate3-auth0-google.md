# Gate 3 — Auth0 (with Google social connection) for og118 accounts

Status: Accepted
Proposed: 2026-06-20 by Bernard

## What it is
Real auth for og118 (Gate 3), replacing the `OG118_ACCESS_TOKEN` bearer speed-bump
in localStorage. Decision: **Auth0**, NOT raw Google OAuth — with Google configured
as a social connection inside Auth0. The user clicks "Sign in with Google"
(one-click; the papelería owner already has Gmail), but the flow goes THROUGH Auth0,
so og118 gets Google's UX AND the canonical session/JWT layer AND email/magic-link
later, without re-architecting.

## Why Auth0 over raw Google OAuth (Art. 6)
Auth0 is ALREADY wired in the stack — the full `AUTH0_*` env set (`AUTH0_DOMAIN`,
`AUTH0_CLIENT_ID`/`SECRET`, `AUTH0_AUDIENCE`, cookie config, DPoP) exists for aurity.
Reuse the canonical; raw Google OAuth forks the auth story with hand-rolled token
validation and zero reuse of the layer aurity already runs.

## Account / corpus model (closes proj-account)
- `corpus_id = project-{projectId}`; `projectId` owned by the authenticated Auth0
  user (`sub`).
- Kids in the papelería = NO auth = open account, no projects, no corpus (cero fuga).
- The mom's business = Auth0 user → her projects → private corpora.
- fi-runner's `active_corpus_binding` receives `corpus_id` as a parameter; it is
  agnostic to this model ([[og118-projects-papeleria-business]] proj-corpusbind
  already decoupled it).

## Canonical path to reuse (Art. 6)
Aurity's Auth0 integration (the `AUTH0_*` env contract + its session handling).
Clone that pattern into og118; reuse the existing shared dev tenant (the
`auth0-ferboli-tenants` memory: `dev-1r4daup7ofj7q6gn` is shared dev with aurity).

## The decision that's the owner's
Whether og118 gets its own Auth0 tenant/app or reuses aurity's shared-dev tenant.

## Status / next step
Not built. Sequenced as Gate 3 — AFTER the Projects feature works end-to-end
(proj-upload ✓, proj-sidebar, proj-uploadui pending). Auth is infra, comes last
(the demo-URL-before-auth doctrine). Build the Projects feature agnostic now
(`project_id = corpus_id`, unauthenticated), then bolt Auth0 on at Gate 3 to make
corpora private-per-user.
