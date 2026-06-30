# B3-AURITY-REACT19-REFS-1 — Fix latent React-19 ref-type errors in aurity

Status: Proposed
Proposed: 2026-06-19 by Claude (surfaced during B3-REPO-TYPES-1)

## What it is

After [B3-REPO-TYPES-1](../rules/react-type-resolution.md) aligned `aurity`'s
`@types/react`/`@types/react-dom` from 18 → 19 (matching its real React 19
runtime), `aurity tsc --noEmit` surfaced **8 latent React-19 strictness errors**
that the wrong (18) types had been masking:

- `RefObject<HTMLDivElement | null>` not assignable to `RefObject<HTMLDivElement>`:
  - `hooks/useChatScroll.ts(397, 398)`
  - `hooks/useIntersectionScroll.tsx(123, 124, 125)`
  - `components/bryntum/hooks/useBryntumScheduler.ts(311)`
- `useRef()` called with no argument (React 19 requires an initial value):
  - `components/background/NeuralNetworkCanvas.tsx(20)`

These are real type-unsafety, not noise: React 19's `useRef<T>(null)` returns
`RefObject<T | null>`, and the consuming code/annotations assumed non-null.

## Why it is a follow-up, not part of #249

- `aurity tsc --noEmit` was **already red on origin/main** (15 errors) — it is a
  dev convenience, **not a CI gate**. The aurity deploy uses
  `next.config.js → typescript.ignoreBuildErrors:true`, so it is not type-gated.
- B3-REPO-TYPES-1 is scoped as **pure infra-hygiene, no product-code changes**.
  These fixes touch product hooks/components (scroll, canvas), so bundling them
  would violate that scope.
- We are in the og118/fi-glass daily-driver stretch; opening another aurity
  branch before closing #249 is avoidable churn.

## Scope when picked up

Mechanical React-19 migration — for each site either widen the target type to
`RefObject<T | null>` or give the ref a concrete initial value. No behavior
change. Verify with `pnpm --filter aurity type-check` dropping these 8 errors
(the remaining pre-existing domain errors — `SeverityLevel`, `DedupeEntry`,
`TaskStatus`, `AppointmentCreate` — are out of scope here too).

## Status / next step

Not started. Registered as AURITY tech-debt. Pick up only after #249 merges, or
sooner if #249 is blocked by Gatekeeper/CI. Related: [[react-type-resolution]].
