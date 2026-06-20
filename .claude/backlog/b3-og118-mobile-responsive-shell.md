# B3-OG118-MOBILE-1 — Responsive shell / mobile drawer for og118

Status: Proposed
Proposed: 2026-06-19 by Claude (DD-mobile read-only audit on og118 staging)

## What it is

og118 is effectively **unusable on mobile** today. Audited at 390×844 (iPhone
12/13/14, dpr 3, mobile+touch) on the staging SWA:

- The `<aside>` sidebar is **fixed at 168px and never collapses** — it eats 43%
  of a 390px viewport.
- The chat + composer are squeezed into the remaining ~128px: the assistant
  bubble (~111px) **wraps one word per line** ("here / to help / you / with …"),
  and the composer textarea is only ~101px wide.
- No horizontal overflow and no double scroll (the squeeze is "clean", just
  unusable). No semantic `<header>`. Mic/speak tap targets are 26×26px (< 44px).

## Canonical path to reuse (Art. 6)

This is a **framework gap, not an og118 patch**. The two-column layout comes from
fi-glass `AgentWorkspaceShell` (shipped in #247), which has no responsive/drawer
mode. The fix is a **new configurable level in fi-glass**: the shell collapses the
sidebar into a drawer below a breakpoint, og118 just opts in. Do NOT hack a
mobile layout into the og118 consumer — that forks the gap to the next shell
(canary-driven upstream loop, [[framework-first-canary]]).

Classification of findings:
1. **Responsive shell / mobile drawer needed** (root) — fi-glass.
2. **Framework gap** — `AgentWorkspaceShell` lacks a drawer/responsive mode.
3. **og118 consumer layout** (minor) — opt into the breakpoint once fi-glass ships it.
4. **Tap targets** (minor, a11y) — mic/speak ≥ 44px, can live in fi-glass.

## Status / next step

Not started — read-only audit only, per the coagent's instruction not to open the
ticket yet. When prioritized: add the responsive drawer level to fi-glass
`AgentWorkspaceShell`, then thin og118 onto it and re-smoke at 390×844.
