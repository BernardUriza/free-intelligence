# CONTRACTS-BEHAVIOR-1 — lo que iOS todavía transcribe a mano de core es COMPORTAMIENTO, no formas

Status: **Proposed** — corte 0 entregado (ver abajo); los cortes 1–3 esperan el go
Proposed: 2026-10-17 by Bernard (dirección: *"seguir sacando contratos comunes entre
la app nativa y la web; fi-glass debería ayudar"*) — diseño: Claude

## Qué es

El riel de contratos cubre **formas**: tres schemas escritos a mano
(`agent-events`, `conversation-record`, `glass-chat-tokens`) de los que derivan
cinco archivos generados (TS y Swift) con sus `check:` de deriva. Lo que el iPhone
sigue copiando a mano de core es **comportamiento** — máquinas de estado y
derivaciones puras que ya viven en `@free-intelligence/core` como funciones sin
React:

| core (SSOT) | og118-ios (copia a mano) |
|---|---|
| `agent/state.ts` `applyAgentEvent` (plan, pasos, result) | `Models/TurnPlan.swift` + `ChatModel.apply` |
| `agent/conversation-state.ts` (fold, falla, timeout, deferred) | `ChatModel.fold` |
| `conversation/helpers.ts` `deriveConversationTitle/Preview`, `truncate`, `conversationRenamePatch`, `organizeConversationSummaries` | `ConversationSchema`, `ConversationsModel.pinned/active/archived` |
| fi-glass `normalizeStreamedMarkdown` | `Models/StreamedMarkdown.swift` |
| `useOg118Agent.ts` troceo SSE (`\n\n`, `data:`) | `Services/SSEParser.swift` |

**fi-glass no cruza a Swift** (decisión del dueño, OG118-IOS-1): las 1,424 líneas
de vistas nativas se quedan. Lo que SÍ cruza es lo que ya cruzó una vez: dato.

## Lo que se encontró leyendo las dos copias (2026-10-17)

Divergencias reales entre la web y el teléfono, invisibles para el riel actual:

1. **`step_started` barre los pasos anteriores** en core (0..N-1 pasan a `done`
   porque SSE pierde frames); Swift sólo marca N como `corriendo`.
2. **`result` cierra los pasos abiertos** como `done` en core; Swift los deja
   `pendiente`/`corriendo` para siempre.
3. **Rename a 60**: core corta en seco (`slice(0, 60)`); Swift trunca con elipsis
   a 59. El mismo título renombrado se guarda distinto según el dispositivo.
4. **Falla del turno**: la web revierte la burbuja optimista y devuelve el borrador
   al composer; iOS deja la burbuja y ofrece *Reintentar*. Es producto, no bug.

Y dos huecos del riel mismo, cerrados en el corte 0:

- `reactions` viajaba en el frame `result` del server de og118 sin que el schema
  de fi-runner lo declarara: la web lo leía a mano, el Swift generado no podía
  verlo, y un turno de sólo reacción llegaba al teléfono como error + Reintentar.
- `main` **no compilaba para iOS** desde `a6670182` (`deferred` entró al enum
  generado; nadie actualizó el `switch` del consumidor). Ningún CI compilaba Swift.

## Camino canónico a reusar (Art. 6)

La misma doctrina del riel — *"el contrato es DATO, no código"* — aplicada al
comportamiento: **vectores de conformidad**. Un `contracts/<máquina>.vectors.json`
escrito a mano (bootstrap una sola vez desde el reducer de core, luego el JSON es
la fuente): cada vector es `eventos → estado esperado` proyectado a los campos que
las dos superficies comparten. core lo consume en vitest (`check:turn-vectors`
falla si core deja de conformar) y el arnés Swift lo re-ejecuta contra `TurnPlan`
+ `ChatModel`. Ningún lenguaje manda; los dos obedecen al JSON.

- **Corte 1 — `agent-turn.vectors.json`**: plan/pasos/result/deferred/reactions.
  Cierra las divergencias 1 y 2 en Swift.
- **Corte 2 — `conversation-derivations.vectors.json`**: título, preview,
  truncado, rename, agrupado del sidebar. Cierra la 3 con la decisión del dueño.
- **Corte 3 — el fixture SSE compartido**: `Tests/Fixtures/turno-real.sse` ya es
  un contrato de facto; sube a `contracts/` y core lo parsea también.
- **Candidato — copy como contrato**: las ~6 frases que core posee (`New chat`,
  el aviso de `deferred`, los dos mensajes de falla) hoy se duplican a mano;
  un `contracts/copy.json` las haría una, como los tokens.

## La decisión que es del dueño

- Divergencia 4 (falla del turno): ¿revertir y devolver el borrador (web) o
  conservar la burbuja y reintentar (iOS)? Los vectores sólo pueden codificar una.
- Divergencia 3 (rename): ¿corte seco o elipsis? Propuesta: el `truncate` con
  elipsis de core en los dos lados — es un cambio en core, no sólo en Swift.

## Estado / siguiente paso

**Corte 0 — entregado 2026-10-17** (rama `bernarduriza/contracts-conformance-vectors`):
`reactions` en `TurnResultPayload` (fi-runner 0.24.0, schema 1.2.0) → TS y Swift
regenerados; iOS pliega la reacción sola como respuesta y maneja `deferred` con
aviso + relectura acotada del hilo; `test_stream_contract.py` valida cada frame
de `/chat/stream` contra el schema; el PR gate corre los ocho `check:` de deriva
y compila + corre el arnés de iOS en `macos-15`.

**Siguiente:** corte 1 en cuanto haya go.
