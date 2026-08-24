# CONV-CONCURRENCY-1 — pin/título pierden en last-write-wins entre dispositivos

Status: **Done** (2026-08-23) — PUT deja de opinar sobre las banderas; PATCH manda el delta
Proposed: 2026-07-13 by Claude (hallazgo del /cruel-critic sobre CONV-ORGANIZE-1, aceptado por Bernard)

## What it is

Toda mutación de conversación viaja como **put del record completo** (`PUT
/conversations/{id}`, patrón de CONV-CLOUD-1): rename, pin, archive y el
persist de cada turno reconstruyen y suben el JSON entero. Con dos
dispositivos activos sobre la misma cuenta, el último put gana el record
completo:

- Teléfono fija (`pinnedAt`) una conversación → desktop, con lista stale en
  memoria, manda un mensaje → su `persist` sube el record SIN `pinnedAt` → el
  pin se pierde en silencio. Lo mismo aplica a `titleCustom`/`title` (deuda que
  existe desde CONV-CLOUD-1) y a `archivedAt` (superficie ampliada por
  CONV-ORGANIZE-1, PR #362).
- No hay corrupción ni pérdida de mensajes (el persist siempre lleva el thread
  completo del dispositivo activo); se pierden los FLAGS de organización.

Mitigante actual: el cliente refresca la lista del server tras cada acción, así
que la ventana es "acción en A mientras B tiene estado viejo y persiste
después" — real pero angosta para un usuario single-owner (og118 es de uso
personal hoy).

## Canonical path to reuse (Art. 6)

Dos rutas, de menor a mayor cirugía — decidir cuando el multi-dispositivo sea
uso real y no teórico:

1. **Guard optimista barato**: el server rechaza (409) un put cuyo `updatedAt`
   sea ANTERIOR al almacenado; el cliente re-lee, re-aplica su delta puro
   (transformers de core: `setConversationPinned`/`renameConversationRecord`)
   y reintenta. Sin endpoint nuevo; ~20 líneas server + retry en
   `transformConversation`/`persist` de fi-glass.
2. **PATCH parcial de metadata**: endpoint `PATCH /conversations/{id}` que
   acepta solo `{title?, titleCustom?, pinnedAt?, archivedAt?}` y hace merge
   server-side; el persist de mensajes deja de tocar flags. Más limpio, más
   cirugía (nuevo verbo en store/app/librerías/tests).

## The decision that's the owner's

Si esta deuda amerita fix antes del multi-usuario/multi-device real, y cuál
ruta (guard 409 vs PATCH). Hoy no bloquea: og118 es single-owner y la ventana
de carrera es angosta.

## Status / next step

No construido. Se activa cuando Bernard reporte el primer pin/rename perdido
entre su Mac y su teléfono, o antes de abrir og118 a más cuentas. Referencias:
`useConversationLibrary.persist` (acarreo de flags), `conversations.py::put`,
PR #362/#364.

## Re-verificado 2026-08-22 — la carrera sigue intacta de punta a punta

- Sin guardia 409: `apps/og118/server/app.py:963` `put_conversation` valida
  forma del id (`:974`), que el id del body y el de la ruta coincidan (`:976`) y
  el tamaño (`:979`) — y luego escribe incondicionalmente en `:986`. No hay
  read-before-write, no se compara `updatedAt`, y no existe un solo `409` en el
  archivo.
- Sin `PATCH`: no hay un solo endpoint parcial en el server.
- Sin `etag` / `If-Match` en `apps/og118/web` ni en `apps/packages/fi-ts`.
- El store es last-write-wins ciego: `server/conversations.py:86` toma un lock,
  escribe a un tmp y hace `os.replace`. **El lock hace la escritura atómica, no
  ordenada** — evita un archivo partido, no una bandera perdida.
- Y del lado del cliente el acarreo empeora la carrera:
  `fi-glass/src/conversation/useConversationLibrary.ts:169` arrastra
  `pinnedAt`/`archivedAt` desde `prevForTitle`, que es `activeRecord` (`:157`) —
  *justo la copia en memoria y vieja* que esta tarjeta describe.
  `transformConversation` (`:205`) hace `get → transform → put` sin versión, así
  que también puede pisar.

## Cerrada 2026-08-23 — la autoridad se movió, no se agregó una versión

La tarjeta dejaba dos rutas y la decisión al dueño. **La ruta 1 (guard optimista
409 sobre `updatedAt`) no era una de las dos: era incorrecta**, y lo prueba el
propio código de este repo — no una preferencia de estilo:

- `setConversationPinned` **deliberadamente NO toca `updatedAt`** (helpers.ts:
  *"pinning is organization, not content, and must not fake recency"*). Un guard
  que compara `updatedAt` no vería ningún cambio al fijar, y dejaría pasar
  exactamente la escritura que existe para frenar.
- `updatedAt` lo acuña el CLIENTE (`nowFn()`), y dos dispositivos no comparten
  reloj. Un teléfono con la hora corrida daría 409 siempre o nunca.

Así que no se agregó una versión: **se movió la autoridad.**

| Verbo | Qué manda ahora |
|---|---|
| `PUT /conversations/{id}` | CONTENIDO — mensajes, preview, `updatedAt`. **No opina sobre las banderas**: el server conserva las suyas |
| `PATCH /conversations/{id}` | ORGANIZACIÓN — `title`/`titleCustom`/`pinnedAt`/`archivedAt`, como delta |

Un dispositivo con copia vieja **no puede perder un pin porque no tiene permiso
de hablar de él**. No hay carrera que ganar: no hay carrera.

### Lo que el delta expresa y el record entero no

`null` = BORRA, ausente = NO TOQUES. Esa distinción es todo el bug: con el put
entero, *"desfijar"* y *"un segundo dispositivo cuya copia es anterior al pin"*
producían **bytes idénticos**, y el server no tenía cómo distinguir una decisión
de una ignorancia. Ganaba la ignorancia, en silencio.

Un test viejo (`test_unpin_upsert_drops_the_stored_flag`) afirmaba justo esa
ambigüedad como si fuera el contrato. Se reescribió, no se borró: la razón por la
que dejó de valer queda escrita ahí.

### Las decisiones que se tomaron construyendo

- **La semántica vive UNA vez, en core.** `applyConversationMetadataPatch` +
  los tres constructores de delta; los transformers de record entero quedaron
  como composiciones delgadas de ellos. Sin eso, la ruta local (aplicar y poner)
  y la remota (mandar el delta) derivan, y hay un test que las compara campo por
  campo para que no puedan.
- **`patch()` es OPCIONAL en el contrato de `ConversationLibrary`**, duck-typeado
  como `forget_session` en fi-runner. Sólo se gana el sueldo donde hay un segundo
  escritor: IndexedDB es un navegador, no tiene con quién competir, y ahí
  `get → transform → put` ya era correcto. Un verbo obligatorio habría sido
  ceremonia para el adaptador que no lo necesita.
- **El merge ocurre bajo el MISMO lock que la escritura** (`put_content` /
  `patch_metadata` en el store). Un read-modify-write en el endpoint habría
  metido una carrera nueva entre dos requests para arreglar la de dos
  dispositivos.
- **`titleCustom` es una bandera de organización**, aunque no lo parezca: un
  rename es un acto del dueño, y dejar que el título auto-derivado del siguiente
  mensaje lo pise es el mismo bug con otro nombre de campo. Pero un título que
  NUNCA fue renombrado sí se sigue actualizando — hay test para las dos mitades.
- **`projectId` se preserva** por lo mismo: es birth-only, y un put que lo omitió
  no debe des-archivar el chat de su proyecto.
- **El cliente adopta el record que devuelve el server**, no su propio cálculo
  optimista — que es, por definición, la copia vieja. `PATCH` responde el record
  completo para que no haga falta un GET extra.

### Lo que NO se hizo, y por qué

- **`projectId` no entró al PATCH.** Mover una conversación de proyecto no es una
  función que exista; agregar el verbo antes que la función es inventar producto.
- **El `persist` del cliente sigue acarreando las banderas.** No es redundancia:
  es lo único que las preserva en el adaptador local. En la nube el server ignora
  esa opinión, que es precisamente lo que cierra la carrera.
- **Sigue sin haber orden entre escrituras de CONTENIDO.** Dos dispositivos
  escribiendo mensajes distintos en el mismo hilo siguen siendo last-write-wins.
  Esta tarjeta cerró la pérdida de banderas, que es la que ocurría en silencio;
  el hilo divergente es un problema distinto y todavía abierto.

### Por qué ahora y no "cuando el multi-dispositivo sea real"

La tarjeta decía *"se activa cuando Bernard reporte el primer pin perdido entre
su Mac y su teléfono"*. Ese día dejó de ser hipotético: **OG118-IOS-1 está In
progress** — hay un cliente nativo de iPhone que compila y arranca. Esperar al
primer pin perdido es esperar a que el bug cobre antes de cobrarlo.

### Verificación

core **100**, fi-glass **560**, og118-web **78**, og118 server **225**, fenix
**68**. `tsc --noEmit` limpio en core y fi-glass; `dist/` de los dos reconstruido
y commiteado ([[committed-dist-artifacts]]); og118-web y fenix-web compilan
contra el fi-glass nuevo.

**Cinco mutaciones probadas en rojo** — tres en el server (el PUT vuelto
sobrescritura ciega tumbó 4 tests: pin, archive, rename y refile; quitar la
preservación del título custom; el `null` tratado como "no toques") y dos en
fi-glass (el seam ignorando el verbo `patch`; el cliente adoptando su propio
cálculo en vez de la respuesta del store).
