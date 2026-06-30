# OG118-ELEMENTS-ADR-1 — Finite 118-slot persona registry (the "elementos")

**Status:** Proposed — decisión de Bernard (ratificar las 4 decisiones de §4)
**Fecha:** 2026-06-27
**Autor:** Claude Code (vía /work; visión de Bernard + arquitectura del coagent AURITY, destiladas del backlog `og118-elementos-118-gpt-personas`)
**Scope:** ADR. Define el modelo; NO construye el registry todavía (el primer slice se abre al ratificar). Cero cambios de auth/endpoints/voz/Gate 4.
**Decide:** cómo og118 hospeda asistentes nombrados ("elementos") con un cap duro de 118, mapeados a bots ya existentes, sin hardcodear prompts.

---

## 1. Qué es (el producto)

og118 = **Oganesson = elemento 118**, el último de la tabla. Los "elementos" son
asistentes tipo-GPT **con cap duro de 118** — uno por elemento de la tabla
periódica (H, He, Li, …, **O**, …, Og). El cap NO es una limitación añadida: es el
cierre temático del producto (escasez como feature, la tabla periódica como
namespace). Un "elemento" es una **persona nombrada y numerada respaldada por un
bot ya construido**, no un GPT scaffolded desde cero. Semilla fija: **`O` —
oxígeno (Z=8)** respaldado por **`vultur-bot`** (repo discord-bot).

Nombre externo/marketing: "elementos / GPTs". Nombre interno real: **slots finitos
de persona nombrada, respaldados por bots existentes.**

## 2. Inventario actual (estado REAL — verificado en código)

| Pieza | Dónde vive | Estado |
|---|---|---|
| Persona única de og118 | `server/prompts/persona.md` (cargada por `load_prompt(PERSONA_PATH)` en `runner.py`) | Vigente — UNA sola persona |
| Selector de persona (UI) | `fi-glass/src/persona-selector/PersonaSelector.tsx` (Californio) | Existe en el framework, **og118 NO lo usa** |
| Props de persona del shell | `fi-glass/shell/types.ts` (`selectedPersona`, `onPersonaChange`, `personaSelector` slot) | Opcionales, hoy omitidos por og118 |
| ToolPolicy por runner | `fi_runner.ToolPolicy.companion()` (PR #291) | Mergeado — cada elemento puede tener su política |
| Corpus binding per turn | `fi_runner.active_corpus_binding` | Mergeado |
| Prompts-as-content P0 | `fi_core.prompts.load_prompt` (mtime hot-reload) | Vigente — regla dura |
| `vultur-bot` | repo **discord-bot** (separado) | Existe; su persona hay que portarla a un `.md` |

**Hueco:** og118 sirve UNA persona fija. No hay (a) registro de slots, (b) noción
de "elemento" con metadata (símbolo, número atómico, bot de respaldo), (c)
resolución de persona por elemento en el turno, (d) cap. fi-glass YA trae el
selector — el hueco es el **modelo de datos + el resolver**, no la UI.

## 3. El gate de seguridad — CERRADO

El backlog bloqueó este ADR detrás del trabajo de seguridad. Estado hoy
(2026-06-27): **#277** (exposición filesystem) root-fixed + **subido al framework
en PR #291** (`ToolPolicy.companion()`); **#276** (identity-scoped stores)
mergeado; RAG owner-gate vigente (PROJ-ACCOUNT-1). Lo único fuera de og118 es
discord-bot summaries (otro repo). **El gate del lado og118 está cerrado → el ADR
abre.**

## 4. Las 4 decisiones (defaults fuertes del backlog — a ratificar)

Las 4 ya tienen tu visión + un default fuerte del coagent. Recomiendo ratificarlas
tal cual; el fork real es solo confirmar.

| # | Decisión | **Recomendación (default)** | Por qué |
|---|----------|------------------------------|---------|
| D1 | Mapping elemento→bot | `vultur-bot → O (Z=8)` fijo; el resto de la tabla es **curación manual tuya**, slot por slot | No auto-generable; es un catálogo curado |
| D2 | Esquema de nombre / PK | **PK = número atómico**. id `element-008-o-oxigeno`, archivo `008-o-oxigeno.md`, display `8 · O · Oxígeno`; `o1`/símbolo/`vultur` solo como aliases | `O` colisiona con cero, símbolos ambiguos, nombres cambian por idioma, "o1" parece model-id |
| D3 | Semántica del cap | **118 = cap DURO, recurso finito.** No hay 119, no se duplica bot de respaldo (salvo allowlist). Estados: `empty/reserved/active/deprecated/disabled` | La escasez ES el producto |
| D4 | Dónde vive el registry | **Dos capas:** (A) registry estructural `server/elements/elements.registry.json` (catálogo: validación/unicidad/lookup → JSON es válido, NO viola P0) + (B) persona por elemento `server/elements/personas/008-o-oxigeno.md` cargada con `load_prompt` | Catálogo ≠ prompt; un cambio en Oxígeno no toca a Hidrógeno |

**Anti-patrón que esto prohíbe (challenge del coagent):** un `elements.ts` con 118
strings de persona inline. El patrón correcto = registry estructural + `.md` por
elemento + loader runtime con hot-reload. Esto es P0 [[prompts-as-content-not-code]].

## 5. Dónde vive (framework-first-canary)

**Se queda en og118 por ahora.** El concepto "118 elementos / tabla periódica" es
producto/marca/mito — demasiado específico para graduar. Lo que PODRÍA extraerse
*después* (cuando un 2º consumer lo necesite, [[framework-first-canary]]): un
primitive genérico **`AgentRoster` finito** en fi-glass + las primitives de
persona-card/loader/routing. **NO** el modelo químico/118. No framework-first antes
de que existan dos consumers.

## 6. Esquema concreto propuesto (el primer slice, listo al ratificar)

`server/elements/elements.registry.json` (los 118 slots; aquí los primeros + Og):

```json
{
  "version": 1,
  "cap": 118,
  "elements": [
    { "atomicNumber": 1, "symbol": "H",  "slug": "hidrogeno", "displayName": "Hidrógeno", "status": "empty" },
    { "atomicNumber": 8, "symbol": "O",  "slug": "oxigeno",   "displayName": "Oxígeno",
      "status": "active", "backingBotId": "vultur-bot",
      "personaPromptPath": "personas/008-o-oxigeno.md",
      "aliases": ["o1", "oxygen", "vultur"] },
    { "atomicNumber": 118, "symbol": "Og", "slug": "oganesson", "displayName": "Oganesson", "status": "reserved" }
  ]
}
```

`server/elements/personas/008-o-oxigeno.md` — el contenido model-facing de Oxígeno
(portado de `vultur-bot`), cargado con `load_prompt` DENTRO del resolver del turno
(hot-reload). El resolver: dado un `element` activo → carga su `.md` como persona +
aplica su `ToolPolicy`/capabilities. Validaciones del registry (tests): exactamente
≤118 slots, `atomicNumber` único 1–118, `slug` único, `active` exige
`backingBotId` + `personaPromptPath` existente, no 119.

## 7. Plan de build (al ratificar)

1. Registry JSON + cargador/validador (`elements_registry.py`) + tests (cap, unicidad, archivos existen).
2. Persona `008-o-oxigeno.md` portada de vultur-bot (su persona vive en discord-bot — la traigo).
3. Resolver de elemento en `runner.py`: elemento activo → persona `.md` + ToolPolicy. Default = la persona og118 actual (elemento "ninguno") para no romper el turno base.
4. Selector mínimo: reusar `fi-glass/PersonaSelector` alimentado por el registry (dev-only/oculto si no hay UI final aún).
5. E2E: seleccionar Oxígeno → preguntar → la respuesta usa la persona de vultur; el trace muestra qué elemento está activo; no hay elemento 119; cambiar de elemento no rompe Projects ni conversaciones.

## 8. Lo que NO hace este ADR

No construye nada todavía (status Proposed). No toca auth/endpoints/voz/Gate 4. No
sube el modelo 118 a fi-glass. No cura la tabla completa (eso es tu D1, slot por slot).
