# Committed dist Artifacts — fi-glass & fi-core ship their built `dist/` ON PURPOSE

In this monorepo, the general rule "never commit build outputs" has a **deliberate,
documented exception**: the built `dist/` trees of the two published packages are
**tracked in git on purpose** and MUST be committed alongside their source changes.

## The tracked-dist paths (exhaustive)

- `apps/packages/fi-glass/dist/**`
- `apps/packages/free-intelligence-core/dist/**`

This is encoded in the root `.gitignore` (the global `dist/` ignore, then explicit
`!apps/packages/fi-glass/dist/` / `!apps/packages/free-intelligence-core/dist/`
un-ignore lines, with a comment explaining why).

## Why they are committed (not a smell)

These two packages **ship their built `dist/` as the v1 release surface**. Downstream
consumers (e.g. `og118-web`) depend on them via `workspace:*` and resolve the package
`exports` straight to `dist/` — and the consumer build does **not** rebuild the
package first (og118's CI runs `next build` directly, never `^build` on fi-glass).
So the committed `dist/` IS what consumers compile and ship. A package whose `dist/`
is stale or absent breaks the consumer's deploy.

## The rule

1. **A change to fi-glass / fi-core source MUST include the rebuilt `dist/` for that
   package in the same commit.** `pnpm --filter <pkg> build`, then stage both `src/`
   and the regenerated `dist/`. Source and shipped bundle must agree (committing only
   `src/` leaves a real src↔dist drift — the actual fake-green to avoid).
2. **Editing `dist/` BY HAND (without the matching `src/` change) is forbidden** —
   that is the genuine violation. The legitimate pattern is always: edit `src/` →
   build → commit both.
3. **The gatekeeper must NOT flag a PR that commits these `dist/` paths when the
   matching `src/` changed and the `dist/` diff is a clean build of it.** That is the
   designed release mechanics of this repo, not a hand-edited bundle. Flag only the
   inverse: a `dist/` edit with no corresponding `src/` change, or a `dist/` diff that
   doesn't match a rebuild of the `src/` diff.

## Why this rule exists

Registered 2026-06-30. PR #308 (B3-FIGLASS-SEMANTIC-SHELL-1) committed the correct
`src/` change to `AgentWorkspaceShell.tsx` AND its rebuilt `dist/agent/index.js`, per
the convention above. The BAIR gatekeeper, which reads `.claude/rules/**` + the
universal playbook but NOT `.gitignore`, had no knowledge of the tracked-dist
exception and applied the generic "don't commit build outputs" heuristic — a false
positive that blocked a convention-correct PR (and contradicted PR #307, the same
pattern, which it had passed). This rule gives the gatekeeper the missing doctrine
through its own repo-rules channel, scoped to this repo's two published packages.
