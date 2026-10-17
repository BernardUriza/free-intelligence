# CONTRACTS-BEHAVIOR-1 — lo que iOS todavía transcribe a mano de core es COMPORTAMIENTO, no formas

Status: **Done 2026-10-17** — cortes 0 a 4 entregados (ver abajo). Residual: el turno vacío (divergencia 6) sigue siendo decisión de producto; el copy como contrato queda candidato
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
5. **Un plan nuevo no limpiaba el rechazo anterior** en Swift; core sí (`plan`
   re-declara y borra `rejection`). La encontró el vector, no la lectura.
6. **Turno vacío** (ni texto, ni reacción, ni `deferred`): core lo cierra en
   silencio y la web no pinta nada; iOS lo declara error ("N frames pero ninguno
   traía texto") y ofrece *Reintentar*. Producto: los vectores lo esquivan
   mandando siempre un `text`.

Y una capa reusable atrapada en el consumidor (DD-002-LESSON otra vez): el
mapeo cable → evento de core (`mapEvent`) vivía en `useOg118Agent.ts` sin
exportar, así que ni core podía verificar sus propios vectores de punta a punta.
Corte 1 lo subió a core como `fromWireEvent` y borró la copia de og118-web.

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

## Las decisiones (tomadas por Claude bajo /ultra-lord, 2026-10-17)

- **Divergencia 4 (falla del turno): iOS se alinea a core** — revierte la burbuja
  optimista, devuelve el mensaje entero (texto e imágenes) al composer y NO
  persiste; *Reintentar* re-envía el último envío como turno nuevo, igual que
  `retry()` en fi-glass. No fue gusto: `fold` en iOS llamaba `save()` aunque el
  turno hubiera fallado, y el mensaje de usuario huérfano llegaba al servidor y
  la web lo pintaba sin respuesta. Core lo evita por construcción (`skipPersist`).
- **Divergencia 3 (rename): corte seco, como core.** Un título custom es texto del
  usuario; agregarle un carácter que no tecleó es inventar. La elipsis es para los
  títulos DERIVADOS, que sustituyen contenido. iOS adopta `ConversationSchema.cap`.
- **Lo que queda del dueño:** divergencia 6, el turno vacío (core calla; iOS lo
  declara error con conteo de frames y ofrece reintentar). Los vectores lo
  esquivan a propósito.

## Estado / siguiente paso

**Corte 0 — entregado 2026-10-17** (rama `bernarduriza/contracts-conformance-vectors`):
`reactions` en `TurnResultPayload` (fi-runner 0.24.0, schema 1.2.0) → TS y Swift
regenerados; iOS pliega la reacción sola como respuesta y maneja `deferred` con
aviso + relectura acotada del hilo; `test_stream_contract.py` valida cada frame
de `/chat/stream` contra el schema; el PR gate corre los ocho `check:` de deriva
y compila + corre el arnés de iOS en `macos-15`.

**Corte 1 — entregado 2026-10-17** (rama `bernarduriza/contracts-turn-vectors`):
`contracts/agent-turn.vectors.json`, 22 vectores escritos a mano (plan, pasos,
rechazo, enmienda, cancelación, desenlaces, text/result, autor, reacciones,
`deferred`, error, ping). core los corre en `src/agent/turn-vectors.test.ts`
pasando los frames por `fromWireEvent` (nuevo en core 1.7.0; og118-web importa y
su `mapEvent` murió) y conformó a los 22 sin tocar el reducer. El arnés de iOS
los re-ejecuta contra `ChatModel` + `TurnPlan` y conformó tras tres arreglos:
barrido de `step_started`, cierre de abiertos en `result`, y `declarar` limpia
el rechazo (divergencias 1, 2 y 5). El PR gate ahora corre también el vitest de
core y de og118-web, que no corrían en ningún workflow.

**Cortes 2, 3 y 4 — entregados 2026-10-17** (rama `bernarduriza/contracts-cortes-2-4`,
core 1.8.0):
- `contracts/conversation-derivations.vectors.json` (12): título, preview,
  rename, agrupado del sidebar. core conformó sin cambios; iOS tras adoptar el
  corte seco del rename.
- `contracts/fixtures/turno-real.sse` es ahora de core, y el framing SSE también
  (`takeSseFrames`, usado por og118-web): el mismo turno capturado del servidor lo
  leen la web, core y el teléfono.
- `contracts/conversation-state.vectors.json` (9): envío optimista, fold, falla
  con borrador devuelto, reintento, hidratación. core conformó sin cambios; iOS
  tras alinear la semántica de falla (divergencia 4). Arnés: 299/299.

**Siguiente:** nada abierto en esta tarjeta. Candidato aparte: `contracts/copy.json`
para las ~6 frases que core posee.
