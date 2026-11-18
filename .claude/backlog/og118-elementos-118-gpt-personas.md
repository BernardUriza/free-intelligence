# OG118-ELEMENTOS — 118 named GPT personas (periodic table, hard cap)

Status: **Done en estructura** (verificado contra el código 2026-09-09) — el registry de 118 slots existe con `cap: 118` y las 4 decisiones del ADR se implementaron tal como se recomendaron, así que `OG118-ELEMENTS-ADR-1` pasó a **Aceptado por implementación**. Curados al 2026-11-18: **24 activos** (7 en el catálogo de la imagen + 17 GPTs dados de alta por la app, ver la última sección) + 1 reservado (Og), de 118. Lo que falta es curación slot por slot, que es trabajo de Bernard por definición (D1) — NO un gate de arquitectura. Esta línea decía *"ADR open, awaiting ratification"* dos meses y medio mientras el código ya lo cumplía
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

## Cierre verificado (2026-08-22)

El ADR no quedó esperando ratificación: se construyó, y con el diseño de dos
capas intacto.

- Catálogo estructural: `apps/og118/server/elements/elements.registry.json` —
  `{version, cap, elements[]}` con **exactamente 118 slots**.
- Resolver: `apps/og118/server/elements_registry.py`; las personas core viven en
  `apps/packages/fi-personas/personas/` (PERSONA-SSOT-1, marcador
  `<!-- CONTEXTO_OPERATIVO -->`).
- **El cap es duro y truena al cargar**, no en runtime: `:19` `CAP = 118`,
  `:154` cap distinto → `ElementsRegistryError`, `:156` más de 118 → error
  (*"the cap is HARD"*), `:163` número atómico fuera de `1..118` → error.
- Los dos puntos fijos de Bernard se respetaron: **`vultur-bot → O` (8)** y el
  tope de 118. La decisión de nombres cayó en número atómico como llave
  primaria, con `aliases: ["o1","oxygen","vultur"]` en el slot 8 — su "o1"
  sobrevive como alias.
- Superficies vivas: `GET /elements` (`server/app.py:491`, filtra a activos),
  caché de runner por elemento (`:234`), token `element` en `ChatRequest`
  (`:409`), rama de engine externo (`:447`), y el deploy los cablea
  (`og118-backend.yml`, *"Wire the external persona engine"*). Web:
  `Og118ElementSelector.tsx`.

**Poblado hoy: 3 activos de 118** — O/oxígeno (`vultur-bot`), Al/aluminio
(`alice`), I/yodo (engine externo sin personaId); Og/oganesón queda reservado.
Lo que falta no es código: es **curación** de los 114 slots vacíos.

**2026-09-08 — cuarto activo, y el primero LOCAL:** Pu/plutonio ← *Reaper
Arquetipo*, el GPT de ChatGPT de Bernard (`g-685301d472188191b49626605246b776`),
portado a `fi-personas/personas/reaper.core.md` + `094-pu-plutonio.context.md`,
sin `engineBinding` (corre en el fi-runner de og118). Destapó que la imagen del
servidor nunca copiaba `fi-personas` — corregido en el mismo PR. El slot 94
(Plutón, señor de los muertos) es propuesta de Claude bajo D1: se mueve con un
campo. La base de conocimiento del GPT (15 PDFs + `modulo_brevedad_afilada.txt`)
NO se portó — en og118 eso es un Project con documentos, no parte de la persona.

## 2026-11-18 — de 5 a 24 activos: los GPTs de ChatGPT entran por la puerta sin deploy

Bernard: *"quiero en og118 tener todos mis gpt, plugins personas y cosas que he hecho"*.
Inventario medido ese día: 22 GPTs en `chatgpt.com/gpts/mine` (los mismos 22 ya
aparecen como plugins en `chatgpt.com/plugins` → Personal → Created by you; ChatGPT
retira los GPTs el 11-dic-2026) y 8 personas en server-bot.

**17 GPTs dados de alta por `POST /elements`** (OG118-ELEMENTOS-ALTA: persona en el
Postgres del runner, slot en el overlay; editables desde "Editar mis elementos").
El ADN es el campo `instructions` de cada GPT, literal, tomado de
`~/Documents/backups/chatgpt-gpts-backup-2026-09-25.json`. Slots propuestos por
Claude bajo D1; se mueven borrando y recreando el elemento.

| Z | Elemento | personaId | GPT |
|---|----------|-----------|-----|
| 2 | He Helio | serenityops_prompt_engineer | SerenityOps Prompt Engineer |
| 6 | C Carbono | ayotzinapa | Archivo Ayotzinapa Vivo |
| 9 | F Flúor | deshilachando | Deshilachando Estructuras |
| 14 | Si Silicio | debian_dell | Experto Debian Dell |
| 15 | P Fósforo | lucifer | Lucifer-GPT |
| 16 | S Azufre | testigo_del_humo | 11S: El Testigo del Humo |
| 22 | Ti Titanio | portfolio_prompt_engineer | Portfolio Prompt Engineer |
| 23 | V Vanadio | vhouse_tech_lead | VHouse Tech Lead |
| 26 | Fe Hierro | codefucker | CodeFucker: Multitrabajo, Pobreza, y Orgullo |
| 27 | Co Cobalto | telares | La Secta de Telares (Parodia) |
| 33 | As Arsénico | toxicity_mastermind | Toxicity Mastermind |
| 36 | Kr Kriptón | archivo_de_sombra | Archivo de Sombra |
| 47 | Ag Plata | mirror_emoji | Mirror Emoji |
| 75 | Re Renio | reduxllm_architect | ReduxLLM Architect |
| 79 | Au Oro | aurity_prompt_engineer | AURITY Prompt Engineer |
| 82 | Pb Plomo | cioran | Cioran GPT – Filosofía del Derrumbe |
| 90 | Th Torio | teologia_del_poder | Teología del Poder |

Verificado en producción: `GET /elements` devolvió 22 activos; un turno de prueba
real a Plomo contestó en voz de Cioran (31 s) y uno a Plata repitió la frase con
16 emojis (22 s).

**2 personas de la imagen prendidas en el catálogo** (no pasan por `POST /elements`:
el runner rechaza con 422 un id que la imagen ya tiene): 1 H Hidrógeno →
`unborn_being`, 19 K Potasio → `frugivoro`. FrugivoreGPT no se portó aparte: el
Frugívoro de server-bot es el canónico.

**Fuera, a propósito:**
- VisaLaw.ai Internal Engineering - VIE 3 y Paylocity Assistant: instrucciones
  internas de un empleador; no entran a su app personal sin que Bernard lo diga.
- Valentis: vive sólo en Khimeras por la decisión documentada en
  `apps/server-bot/shared/personas/registry.py`.

**Lo que NO se portó:** los archivos de conocimiento (135 entre los 22 GPTs). El
respaldo sólo trae sus nombres y tamaños, no el contenido. En og118 eso es un
Project con documentos, no parte de la persona.
