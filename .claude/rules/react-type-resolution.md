# React Type Resolution — Explicit devDeps, Never Hoisting Roulette

This monorepo runs **mixed React majors**: `fi-monitor` is React 18, every other
React workspace is React 19. Because of that, a blind root override of
`@types/react` / `@types/react-dom` is FORBIDDEN — it would pin React-19 types
against React-18 runtime in `fi-monitor` (or vice versa) and silently break that
package's typecheck.

## The rule

**Every workspace that compiles JSX/TSX declares `@types/react` AND
`@types/react-dom` as explicit `devDependencies`, aligned to that package's real
React major.** Never rely on the hoisted root copy.

- React 19 packages → `@types/react` and `@types/react-dom` at `^19.x`.
- React 18 packages → both at `^18.x`.
- A package that pins `@types/react` but omits `@types/react-dom` (or vice versa)
  is consuming the other half by accidental hoisting — add the missing one.

## Why explicit, not hoisted

pnpm hoists one copy of `@types/react` to the root. Which version wins depends on
install order, lockfile state, and whether a fresh worktree was used — i.e. it is
**non-deterministic**. A package whose declared spec disagrees with the hoisted
copy compiles green on one machine and red on the next. Explicit per-package
devDeps make type resolution reproducible regardless of hoisting.

## Workspaces that do NOT need React types

A peer-only package with **zero** `.tsx`/`.jsx` files (pure logic/hooks/types —
e.g. `@free-intelligence/core`, `@aurity-standalone/hooks`,
`@aurity-standalone/medical`) keeps `react`/`react-dom` as `peerDependencies`
only and declares no `@types/react`. Adding type devDeps to a package that never
compiles JSX is noise.

## Checklist for a new React package

```
☐ Does it contain .tsx/.jsx?  → if no, peerDependencies only, stop here.
☐ Declare @types/react in devDependencies, ^<its react major>.
☐ Declare @types/react-dom in devDependencies, same major.
☐ Verify against a FRESH worktree install (clean hoisting) before merging.
```

Established by **B3-REPO-TYPES-1** (2026-06-19). The trigger: `aurity` ran React
`^19.2.0` but declared `@types/react@^18.2.37` + `@types/react-dom@^18.2.15`, and
`fi-glass` (100 `.tsx`) declared `@types/react` but no `@types/react-dom`, leaving
both at the mercy of the hoisted root copy.
