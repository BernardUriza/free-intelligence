# The monorepo — server and front in one repo, one wall

Status: In progress
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

Phase 1: restructure into `server/` (droplet paths pinned via unit env), deploy
green with probes. Phase 2: subtree `front/` + migrate its workflow + verify
the render. Phase 3: amend the two rules, archive `aire-front-seed`.
