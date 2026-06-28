# OG118-ELEMENTOS — 118 named GPT personas (periodic table, hard cap)

Status: ADR open — `apps/og118/OG118-ELEMENTS-ADR-1.md` (2026-06-27), awaiting Bernard's ratification of the 4 decisions
Proposed: 2026-06-24 by Bernard

> 2026-06-27: the security gate that blocked this CLEARED (#277 root-fixed + raised
> to the framework in PR #291, #276 identity-scoping merged, RAG owner-gate live).
> `OG118-ELEMENTS-ADR-1` written with the 4 owner-decisions ratified-as-defaults +
> a concrete registry schema (Oxígeno/vultur-bot as the first slot) and build plan.
> Build of the first slice opens once Bernard ratifies D1–D4.

## What it is

og118 will host special GPT-like assistants called **"elementos"**. Unlike
ChatGPT's GPTs (effectively infinite), og118's are **hard-capped at 118** — one
per element of the periodic table, because **og118 = Oganesson = element 118**,
the last element. The cap is not a limitation bolted on; it is the product's
thematic closure (scarcity as a feature, the periodic table as the namespace).

The names are **already assigned** — the 118 element names ARE the slot registry
(H, He, Li, Be, B, C, N, **O**, F, Ne, …, Og). Each slot is filled by mapping an
**existing bot/persona** onto it. Bernard's seed example: **"O — oxígeno"**
(symbol O, oxygen) could BE **`vultur-bot`** from the discord-bot repo. So an
"elemento" is a named, numbered persona backed by a real already-built bot, not a
new GPT scaffolded from scratch.

## Canonical path to reuse (Art. 6)

This is almost entirely composition over existing surfaces — the 118 cap and the
periodic-table naming are the only genuinely new pieces.

- **Persona infra already ships in fi-glass** — Californio closed the persona
  selector + SpeakButton ([[fi-glass-framework]] memory). og118 already renders
  and switches personas. An "elemento" is a persona with element metadata
  (symbol, atomic number) + a backing bot, NOT new GPT plumbing.
- **The backing bots already exist** — `vultur-bot` lives in the discord-bot repo;
  the insult fleet exists. Mapping them onto element slots is reuse of the
  canonical bot fleet, not reinvention. Don't rebuild a bot to fill a slot.
- **Prompts-as-content is P0** ([[p0-prompts-as-content-debt]],
  `prompts-as-content-not-code`): each elemento's persona MUST be a `.md` content
  file loaded via `load_prompt` at runtime — NEVER an inline `PERSONA = (...)`
  constant. The element registry itself (slot → symbol → backing persona file) is
  content, not code.
- **Canary discipline** ([[framework-first-canary]]): a "registry of N named
  personas with a hard cap" is reusable framework, not og118-local. If it's built,
  the registry/cap primitive belongs in fi-glass/core; og118 is its first consumer.

## The decision that's the owner's

1. **The element → bot mapping.** Which of the 118 slots maps to which existing
   bot/persona. `vultur-bot → O (oxígeno)` is the seed; the full curated table is
   Bernard's call. This is a hand-curated registry, not auto-generated.
2. **Numbering/naming scheme.** Bernard wrote "o1 - oxigen", but oxygen's symbol
   is **O** and its atomic number is **8** (O1 ≠ standard notation). Decide the
   canonical label format: atomic number ("8 — O — Oxígeno"), symbol-only, or his
   "o1" shorthand. Pick ONE scheme before the registry is written.
3. **Is the 118 cap a hard product constraint** (true scarcity — slots get claimed
   and run out) or a thematic ceiling? Affects whether slot assignment needs a
   claim/lock mechanism.
4. **Where the 118-slot registry lives** — a single content file, per-element
   files under `personas/`, or backend-owned. Follows from the prompts-as-content
   rule + the canary-vs-app-specific classification.

## Orchestrator's proposed architecture (coagent, 2026-06-24)

Relayed to the og118 prompt-engineer coagent via `/exchange-coagent`. Its take on
the 4 owner-decisions above (a strong default, still Bernard's to ratify):

- **Two layers, not one .md.** (A) A **structural registry** —
  `apps/og118/server/elements/elements.registry.json` (or `.yaml`) holding all
  118 slots (even empty ones): `atomicNumber`, `symbol`, `slug`, `displayName`,
  `status`, `backingBotId`, `personaPromptPath`, `capabilities`, `enabled`. The
  coagent argues this is a **catalog, not model-facing prompt**, so JSON/YAML is
  valid and does NOT violate the P0 prompts-as-content rule (it needs validation,
  uniqueness, lookup, tests). (B) **Per-element persona `.md`** —
  `elements/personas/008-o-oxigeno.md` holds the model-facing content, loaded via
  `load_prompt` inside the element resolver. One file per element — changing
  Oxígeno must not touch Hidrógeno.
- **Primary key = atomic number**, not symbol, not "o1". Canonical id
  `element-008-o-oxigeno`; filename `008-o-oxigeno.md`; display `8 · O · Oxígeno`;
  "o1"/"oxygen"/"vultur" only as optional aliases. Reason: `O` collides with zero,
  symbols are ambiguous, names change by language, and "o1" reads like a model id.
- **118 = HARD cap, finite resource** (not a thematic ceiling). Slots get claimed
  and run out; no element 119; no duplicate backing bot (except explicit
  allowlist). Slot states: `empty | reserved | active | deprecated | disabled`.
  Filling an element is an act of curation, not spawning another infinite GPT.
- **Stays in og118 for now** — the "118 elements" concept is product/brand/myth,
  too specific to graduate. What *could* extract later (once a 2nd consumer needs
  it, per [[framework-first-canary]]): a generic **finite AgentRoster** primitive
  in fi-glass + the persona-card/loader/routing primitives. NOT the chemistry/118
  model. Don't framework-first before two consumers exist.
- **Recommended sequencing** (the coagent gated this behind active security work):
  close #277 (filesystem exposure) → #276 (identity-scoped stores) → RAG
  lock/perms → discord-bot summaries P0 → THEN open `OG118-ELEMENTS-ADR-1`
  (finite 118-slot persona registry) → then the registry with Oxígeno as the
  first real slot (`backingBotId: vultur-bot`, `status: active`).
- **Its hard challenge:** "no conviertas elementos en otra forma de hardcodear
  prompts" — the failure mode is `elements.ts` with 118 inline persona strings.
  Correct pattern = structural registry + per-element `.md` + runtime loader +
  hot-reload tests. Internally these are "finite named persona slots backed by
  existing bots"; "GPTs/elementos" is the external/marketing name only.

## Status / next step

Not built — vision captured (the day Bernard described it, Art. 5).

**GATED behind active security work (Bernard's call, 2026-06-24):** stays in
backlog, NOT opened, until the security surface closes — #277 (filesystem
exposure), #276 (identity-scoped stores), RAG lock/perms, then discord-bot
summaries P0. Only after that does `OG118-ELEMENTS-ADR-1` open and the registry
build begin (Oxígeno / `vultur-bot` as the first real slot).

When unblocked, the remaining owner-decisions to ratify are the 4 above
(mapping + naming scheme + cap semantics + registry home); the coagent's proposed
architecture is the strong default. Fixed points: `vultur-bot → O` and the 118
hard cap.

Related: [[fi-glass-framework]], [[framework-first-canary]],
[[p0-prompts-as-content-debt]], the discord-bot `vultur-bot`.
