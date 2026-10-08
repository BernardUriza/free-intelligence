# The monorepo — server and front in one repo, one wall

Status: Done 2026-07-20
Proposed: 2026-07-20 by Bernard

## What it is

Fuse `aire-server` and `aire-front-seed` into one monorepo: `server/` (the
daemon, the pen) and `front/` (the waiter, Next.js SSR). The CQRS wall stops
being physical-by-repo and becomes physical-by-credential-and-pipeline: the
daemon keeps role `aire`, the front keeps `aire_reader` (SELECT only), two
deploy workflows path-filtered (`server/**` → droplet SSH, `front/**` → Azure
Container Apps). The schema contract between pen and waiter becomes one atomic
diff instead of a two-repo coordination.

## Canonical path to reuse (Art. 6)

`git subtree add --prefix front` (history preserved — never cut-and-paste,
Art. 5). Path-filtered workflows as `deploy.yml` already does. The rules
travel: `write-only-daemon` amended (repo-wall → credential-wall),
`read-only-waiter` rides in `front/`.

## The decision that's the owner's

Done — Bernard greenlit 2026-07-20 ("genial idea!"). Archive of
`aire-front-seed` happens only AFTER the front deploys green from here.

## Status / next step

All three phases landed 2026-07-20. Phase 1: `server/` restructure, droplet
paths pinned in units, deploy-server green, /health + listener + tick verified
live. Phase 2: `front/` via git subtree (history intact), ci-front (attack
suite green on disposable Postgres) + deploy-front (fresh SP scoped to
insult-rg) → Container App rolled, /api/health 200 verified. Phase 3: both
laws amended (repo-wall → credential-wall), `aire-front-seed` archived with a
pointer README.
