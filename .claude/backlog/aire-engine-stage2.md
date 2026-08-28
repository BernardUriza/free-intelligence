# AIRE engine — etapa 2: el runner deja de hostear el SDK y las personas viven en casitas

Status: **TERMINADA — borrado completo 2026-08-28 (v4.35.0)** (encendida en
prod y verificada en vivo 2026-08-27; Bernard declaró el flag permanente el
2026-08-28: "dale con el borrado"). La Container App `persona-runner` (insult-rg, revisión activa
`persona-runner--0000185`, creada 2026-08-26) corre con `TURN_BACKEND=aire` y
`AIRE_GATE_URL=https://gate.bernarduriza.com`: los turnos de producción salen
por la puerta engine. Evidencia adicional de tráfico real: v4.32.81 (fix de
cortes `budget_*` de AIRE en canales vivos) sólo existe porque turnos reales se
cortaban por esa ruta. **El vendored `aire_backend.py` MURIÓ el 2026-08-27**
(paso de borrado nº 6): fi-runner 0.20.0 publica `fi_runner.backends.aire` con
las seis adaptaciones upstreameadas (free-intelligence PR #443, incluida la
sexta — el corte post-result de v4.32.81, que el vendoreo había crecido sin
documentar), el pin subió `0.11.0 → 0.20.0` y
`grep -rn "engine.aire_backend" persona_runner/ tests/` devuelve vacío. **El BORRADO se completó el 2026-08-28 (v4.35.0)**: murieron `session_pool.py`,
`options.py` (Playwright incluido), la rama local de `api/turn.py`/`api/judge.py`,
el flag `TURN_BACKEND`, el reaper, la dep `claude-agent-sdk` (las tools de
memoria se declaran vía `mcp_tools/tooldef.py`, mismo JSON Schema pinneado por
test) y las capas Playwright/Chromium de `runner-base.Dockerfile`. `route_model`
se mudó a `routing/router_runtime.py`; el reset de canal renació sobre topics
(`aire_route.reset_channel` + `aire_topic.reset_channel`: DELETE de la fila
durable ⇒ el siguiente claim acuña topic fresco); `/health.credentials_rejected`
ahora lo marca la ruta AIRE en `credentials_exhausted` (la señal volvía a ser
un verde incapaz de fallar). Los tres greps del criterio, corridos 2026-08-28:
`grep -rn "session_pool\|build_options\|TURN_BACKEND" persona_runner/ tests/` → **0**
· `grep -rn "claude_agent_sdk" persona_runner/` → **0 imports** (2 docstrings de
procedencia en tooldef.py) · `grep -rni "playwright" persona_runner/ Dockerfile.* environment.yml` → **0**.
Suite: 1423 passed. Lo que sigue abierto: (b) hallazgo 1 (el `model` ignorado en
sesión caliente) CERRADO 2026-08-28: aire-server #38 rebindea al cambiar el
spec, verificado en vivo (misma sesión: haiku y luego `claude-sonnet-4-6`,
cada turno contestado por SU modelo). Hallazgo 2 (las tools de memoria)
CERRADO 2026-08-28 (v4.34.1): Insult, desde el droplet, invocó
`mcp__persona_memory__get_emotional_arc` por la cadena completa (fi-runner
0.21.0 remote_tools → puerta AIRE → SDK → HTTPS de vuelta a /mcp/{casita} →
principal durable → Khimeras PG) y contestó el registro real en #general
(phase: stability, crisis_depth: 0, turns_in_phase: 145). El primer turno
real destapó además un bug pre-existente del tool (SELECT de una columna
inexistente, `intensity` → `crisis_depth`), arreglado en v4.34.1.
Proposed: 2026-08-22 (orden de Bernard: "etapa 2, NO hoy") · Construida: 2026-08-22
· Auditada por code review y corregida: 2026-08-22 (seis defectos, abajo)
· Encendida en prod: revisión del 2026-08-26; verificada en el env vivo 2026-08-27
· Des-vendoreada: 2026-08-27 (fi-runner 0.20.0 en el canal; borrado nº 6 hecho)

## Qué es

La migración real: `persona-runner` deja de ser un host propio del Claude Agent
SDK y cada turno se vuelve un
`POST /projects/{p}/sessions/{s}/messages` contra la puerta ENGINE de AIRE. El
precedente es og118 (free-intelligence), migrado 2026-08-21 — pero og118 era un
runner delgado; éste no.

## El diseño, ya decidido (no reabrir)

| Fork | Decisión |
|---|---|
| Alcance de la casita | **persona+canal**: `{persona_id}-{channel_id}` — el ALMA del canal, persiste |
| Alcance de la SESIÓN | **un TOPIC temporal** que rueda tras `AIRE_TOPIC_IDLE_TIMEOUT_S` (default 3600 s) de silencio del canal. Ver *"El tercer eje"* abajo |
| Dónde vive el ADN | casita BASE por persona (`insult`), instalada vía `/init`; cada casita de chat nace THIN con el stub `@base insult` que AIRE dereferencia en cada spawn (aire-server `ef21e68`) |
| Playwright | **SE CAE** en la ruta AIRE (droplet de 512MB, presupuesto duro de $20 — [[do-budget]] de aire-server) |
| WebSearch/WebFetch | sobreviven vía `mode=agent` (dial server-side de AIRE) |
| facts + `behavioral_guidance` | viajan **IN-BAND**, compuestos en el mensaje del turno como ya se compone `turn_context`. **Ninguna credencial de Khimeras llega al droplet** |
| tools del registry | `["persona","memory"]` en cada turno |
| `/v1/judge` | `mode=complete` en la casita utilitaria `{persona_id}-judge`, sesión desechable por llamada |
| errores terminales | `budget_exhausted` / `credentials_exhausted` → 500 (el gateway usa su error neutral en personaje); `slot_busy` → 503 (reintento transitorio). **Un turno cortado JAMÁS se ve como éxito** |

## Qué se construyó (en `main`, detrás del flag)

| Archivo | Qué es |
|---|---|
| ~~`persona_runner/engine/aire_backend.py`~~ | **BORRADO 2026-08-27**: el cliente es el REAL `fi_runner.backends.aire` (fi-runner 0.20.0 del canal). Las seis adaptaciones del vendoreo viven upstream (free-intelligence PR #443): `AIREDoorError` (código como dato), la normalización de errores sin `type`, y el corte `budget_exhausted` post-result que no anula una respuesta entregada (v4.32.81) |
| `persona_runner/engine/aire_route.py` | La ruta: casitas, pre-fetch de facts, guard de capacidades, mapeo de errores, judge, el candado por casita |
| `persona_runner/engine/aire_topic.py` | **El tercer eje**: el claim atómico del topic contra `aire_topics`, su fallback en RAM y el bit durable que gobierna el pliegue de historia |
| `persona_runner/api/turn.py` · `api/judge.py` | La bifurcación por `TURN_BACKEND` |
| `persona_runner/runner.py` | El boot verifica la ruta que DE VERDAD va a servir turnos; el shutdown cierra los backends y el pool |
| `persona_runner/mcp_tools/shared.py` | El pool asyncpg compartido (`acquire`/`close_pool`) que usa el pre-fetch de facts. `_connect` (one-shot) sigue vivo para las tools MCP |
| `core/config.py` · `core/schemas.py` · `engine/framing.py` | El flag, `AIRE_TOPIC_IDLE_TIMEOUT_S`, `JudgeRequest.persona_id`, el bloque `<user_memory>` |
| `tests/agent/test_aire_{route,backend,topics}.py` · `test_turn_backend_flag.py` · `test_pg_pool.py` | 95 tests; el default `local` está pinneado por test |

## El tercer eje: la sesión es un TOPIC (decisión de Bernard, 2026-08-22)

Sus palabras: casitas *"por sesión de discord bot y por channel y por topic
temporal"*. La etapa 2 había mandado dos ejes y **clavado el tercero a una
constante** (`SESSION_NAME = "live"`, una sesión que nunca termina). Esa
constante era el defecto: un canal de Discord vive AÑOS, así que un canal era un
solo transcript que crece sin techo — cada `resume` lo carga entero, cada turno
lo paga, y una conversación de hace tres meses se mete en la respuesta de hoy.

| Eje | Qué es | Qué lo mueve |
|---|---|---|
| casita `{persona}-{canal}` | el **ALMA** del canal: el stub `@base` más lo que la tool `persona` haya escrito en la mitad viva | nada: persiste entre topics |
| sesión = **topic** `t<epoch>` | el hilo de conversación: el transcript que AIRE resume | rueda tras `AIRE_TOPIC_IDLE_TIMEOUT_S` de silencio |
| persona | quién contesta | el `persona_id` del turno |

**El topic NO va en el nombre de la casita, a propósito.** AIRE llavea la memoria
por (project, session), así que un topic nuevo ya estrena transcript DENTRO de la
misma casita — el alma sobrevive. Meterlo en el nombre bifurcaría la identidad
viva por topic y recrearía el problema de "N copias congeladas de la persona" que
el nacimiento THIN (aire-server `ef21e68`) existe para matar.

### Por qué 3600 s, y qué cuesta rodar

Un rollover deja la siguiente sesión **FRÍA**: el system prompt de la persona
(~14k tokens sólo de ADN) se vuelve a *cache-crear* — un turno frío de una frase
midió **$0.107** contra la puerta en vivo. Ventana muy corta = fuga de dinero una
vez por cada silencio; muy larga = vuelve el transcript infinito.

El default de **3600 s** está elegido para que el rollover sea casi **GRATIS**, no
apenas tolerable: **AIRE desaloja su cliente ocioso a los `AIRE_POOL_IDLE_S`
(3300 s ≈ 55 min)**, así que un canal callado una hora YA perdió su cliente
caliente y ese turno iba a re-pagar el system prompt rodara o no el topic. Rodar
justo pasando ese borde compra transcript limpio al precio de un arranque en frío
que ya estaba cobrado. **Bajar la perilla de ~55 min es donde empieza a costar
dinero de verdad** — ése es el trade a pesar, no "más corto es más limpio".

Los topics **no** aumentan la concurrencia (son secuenciales por canal, y el
candado por casita los serializa), así que no tocan el techo de 2 clientes /
458 MB de AIRE (aire-server #39). Sí aumentan los arranques en frío, que es
exactamente el costo de arriba.

### Por qué el id es DURABLE (y no un derivado de RAM)

Este repo redespliega varias veces al día. Un id derivado de estado en RAM
bifurcaría el topic **en silencio** a media conversación: mismo canal, transcript
vacío nuevo, y la historia replicada por el caller plegada otra vez. Así que el
ancla se **persiste**: una fila por casita en el Postgres de Khimeras, tabla
**`aire_topics`** cuyo DDL vive en el módulo que la posee (`engine/aire_topic.py`)
y se aplica una vez por proceso.

Una sola sentencia atómica (`_CLAIM_SQL`) lee la fila, decide rodar-o-continuar y
registra la actividad bajo el lock de la propia fila, y el id lo acuña el reloj
del SERVIDOR — así la decisión es correcta entre réplicas, no sólo entre
corrutinas. `answered_at` (durable) es lo que gobierna el pliegue de historia:
**tras un reinicio a media conversación la fila dice "este topic ya tuvo
respuesta" y el runner NO vuelve a plegar** lo que la sesión de AIRE ya tiene —
lo cual cierra, mientras Postgres esté vivo, el hueco #4 de abajo (la
duplicación acotada por falta de sonda `¿existe esta sesión?`).

Postgres caído ⇒ el claim se hace en RAM (`TopicMemory`, mismo algoritmo) porque
un fallo de DB **jamás** mata un turno; se grita `aire_route_topic_not_durable` en
cada turno afectado. Lo único que el fallback no sobrevive es un reinicio con la
DB abajo: ahí sí arranca topic nuevo y pliega una vez. Acotado y logueado, nunca
silencioso.

### La decisión del topic va DENTRO del candado por casita

Mismo `asyncio.Lock` que ya serializaba decidir→turno→marcar (defecto 1 abajo).
Dos mensajes simultáneos en un canal tienen que caer en **UN** topic y plegar la
historia **una** vez; el candado es lo que hace atómica esa ventana. `CasitaState`
pasa a llavearse por la CASITA sola (antes `casita/live`): la sesión ahora se
DECIDE bajo ese candado, así que no puede formar parte de la llave que lo elige.

### Observabilidad

`agent_runner_turn_complete` lleva `topic`, `topic_rolled_over` y `topic_state`
(`durable`/`ram`) — una casita ya no identifica qué transcript contestó. Un
rollover emite además su **propio** evento `aire_route_topic_rolled_over` (con el
hueco de inactividad, la ventana y el costo declarado), y el primer topic de una
casita emite `aire_route_topic_opened` — que **no** es un rollover: nada se
reseteó, y contarlo como reset ensuciaría la métrica que importa.

**Tests del modo de falla** (`tests/agent/test_aire_topics.py`, 19): canal ocioso
pasado la ventana rueda · canal dentro de la ventana NO rueda (resistencia) · dos
mensajes concurrentes caen en un topic y pliegan una vez · un reinicio simulado a
media ventana conserva el id y **no** re-pliega · un turno fallido deja el topic
sin responder · un `mark_answered` perdido no compra un segundo pliegue · PG
caído responde igual y se reporta como no-durable · la ruta local del SDK jamás
toca el eje. Cada uno verificado en ROJO mutando el arreglo (id derivado de RAM,
claim fuera del candado, sesión constante `"live"`, marcar antes del turno).

## Los seis defectos del code review (2026-08-22) — arreglados

Encontrados auditando `05d311d`/`ac3abca`/`a709dd3`. Cada arreglo trae su test
del MODO DE FALLA (el interleaving que era posible antes), no del happy path;
cada uno se verificó revirtiendo el arreglo y viendo el test en rojo.

| # | Defecto | Arreglo | Test que lo prueba |
|---|---|---|---|
| 1 🔴 | `is_first_turn` se leía sin candado y se marcaba DESPUÉS del turno: dos mensajes casi simultáneos en un canal se creían ambos "el primero" y **plegaban la historia dos veces**. AIRE serializa con su candado por sesión, así que no truena — la sesión simplemente termina con la conversación duplicada y esos tokens pagados dos veces | Un `asyncio.Lock` por casita (`CasitaState`) sostenido sobre decidir→turno→marcar, igual que `api/turn.py` ("only under the lock does 'not open' mean THIS turn opens the session"). Crear el candado es un paso síncrono (estilo `session_pool.slot_lock`), así que la creación tampoco corre carrera. Un turno FALLIDO sigue sin marcar la sesión | `test_two_simultaneous_turns_fold_the_history_exactly_once`, `test_turns_in_different_channels_are_not_serialized_against_each_other` (resistencia), `test_a_failed_turn_leaves_the_session_unmarked` |
| 2 🔴 | El judge mandaba TODAS las llamadas de una persona a una sola casita `{persona}-judge`, y el `system_prompt` arbitrario del caller se instala con `/init` ANTES del turno. Con `JUDGE_MAX_CONCURRENCY=1` el semáforo lo tapaba; **subir esa variable —seguro en la ruta local, donde cada judge es un subproceso aislado con su propio prompt— hace que el `/init` de B pise el CLAUDE.md mientras A está a media respuesta**, y A contesta bajo el prompt de B con una respuesta que se ve perfecta. Una perilla cuya seguridad depende en silencio del backend ES el bug | La casita se llama `{persona}-judge-{sha256(prompt)[:32]}`. Misma casita ⟺ prompt byte-idéntico (un `/init` concurrente escribe los mismos bytes); prompt distinto = casita distinta. **Estructural, sin candado**, así que los judges siguen corriendo en paralelo. **Acotado**: los prompts de judge son `.md` de `khimeras_shared/prompts_md/` templateados a lo sumo con el nombre de la persona (todo lo del usuario viaja en el mensaje USER), así que el conteo de casitas es "prompts distintos × personas" — un puñado, estable — y no un directorio por extracción de facts en background. Eso importa: AIRE tiene escoba para sus tablas, **no para las casitas**, y una casita es un directorio en una caja de 458 MB | `test_two_concurrent_judges_never_execute_under_each_others_prompt` (con `JUDGE_MAX_CONCURRENCY=4`, la configuración para la que existe el arreglo), `test_many_judges_on_one_identical_prompt_still_share_one_casita` (resistencia: no ensucia el droplet), `test_the_judge_casita_is_named_after_its_prompt` |
| 3 🟠 | `AIREBackend.aclose()` existía y **nadie lo llamaba**: `_lifespan` sólo cerraba `session_pool`, así que cada cliente `httpx` (de turno y de judge) se fugaba en cada shutdown | `aire_route.close_backends()` drena las dos cachés, best-effort por backend, y `_lifespan` lo llama en la rama AIRE (más `shared.close_pool()`, siempre) | `test_close_backends_closes_turn_and_judge_clients`, `test_one_stubborn_backend_does_not_strand_the_others` (resistencia), `test_the_runner_lifespan_closes_the_aire_backends` |
| 4 🟠 | `fetch_user_facts` abría y cerraba una conexión Postgres **en cada turno**. Antes de esta ruta ese costo se pagaba sólo cuando el modelo ELEGÍA llamar la tool de memoria; el pre-fetch in-band lo volvió incondicional (connect + handshake TLS a Azure por turno) | Un pool asyncpg compartido en `mcp_tools/shared.py` (`acquire()` / `close_pool()`), que es donde vive la política de conexión (Art. 6) para que cualquier futuro caller de hot path lo reuse. `_connect()` one-shot **se queda** para las tools MCP: el modelo las llama rara vez y cambiarlas sería tocar la ruta local. La ley se conserva: cualquier falla de DB devuelve `""` y jamás mata el turno | `tests/agent/test_pg_pool.py` (un solo pool con N acquires, la conexión se RELEASEA no se cierra, dos primeros callers concurrentes no construyen dos pools), `test_the_hot_path_never_opens_its_own_connection` |
| 5 🟠 | `to_http_error` decidía terminal-vs-backpressure con `in` contra el TEXTO del error, mientras `aire_backend` ya normalizaba el código estructurado de AIRE y lo tiraba al formatearlo dentro de un string | `AIREDoorError` (adaptación 5 del vendoreo) conserva `code` y `http_status` como atributos; `_error_status` decide sobre el código. El substring queda **sólo como fallback para fallas sin estructura**, y su modo de falla es el seguro: si AIRE re-redacta un mensaje, el peor caso es 502-y-reintenta, no un corte terminal leído como algo que un reintento arregla | `test_a_structured_terminal_code_is_500_even_when_the_prose_changes`, `test_a_structured_backpressure_code_is_503_...`, `test_an_unknown_structured_code_is_502_not_a_guess`, `test_an_unstructured_reworded_failure_degrades_to_502`, y en el backend `test_an_sse_error_carries_aires_code_as_an_attribute` + `test_a_torn_stream_stays_an_uncoded_failure` |
| 6 🟡 | `verify_aire_route()` construía Y CACHEABA un backend como efecto secundario de verificar; `_seen_sessions` crecía sin techo | La construcción se extrajo a `_build_backend` y el boot verifica ese, sin tocar la caché. `_seen_sessions` desapareció dentro de `CasitaState`, un `OrderedDict` LRU con tope (`AIRE_CASITA_STATE_MAX`, 4096) — obligatorio ahora que cada entrada carga un `asyncio.Lock` y no una cadenita. La expulsión **nunca toca una casita con el candado tomado**; lo único que cuesta es el bit `seen`, o sea que esa casita pliega historia una vez más — exactamente la duplicación acotada que ya causa un reinicio | `test_verifying_the_route_does_not_warm_the_backend_cache`, `test_the_casita_state_map_is_bounded`, `test_a_casita_mid_turn_is_never_evicted` (resistencia) |

**Lo que NO se tocó, a propósito:** la ruta local del SDK (sus tests siguen
verdes, 1374 en la suite completa), el flag (`TURN_BACKEND` sigue en `local` y
nada de esto lo prende), y el techo de capacidad de AIRE (`POOL_MAX=2`, 129 MB
por cliente, espera de 45 s, ~60 casitas ⇒ la mayoría de los turnos son fríos y
re-pagan el `cache_creation` del system prompt). Ese último es decisión de
Bernard y quedó explícitamente FUERA: ningún arreglo de aquí agrega capas de
caché para rodearlo, y ninguno lo empeora.

**Un costo pre-existente que sigue ahí, en las DOS rutas** (no es regresión de
la etapa 2, no se arregló para no cambiar la conducta de la ruta local):
`session_pool._route_model` también abre y cierra su propia conexión Postgres
por turno (`mcp_tools._connect`). Ahora que el pool existe en `shared.py`, es un
one-liner el día que se quiera — pero toca la ruta local, así que va a decisión.

## Los hallazgos que BLOQUEAN encender el flag

Ninguno se sabía al proponer el item. Los dos primeros son de AIRE (cada uno =
un endpoint/capacidad que le falta a `aire-server`); el tercero es de este repo.

### 1. ✅ CERRADO 2026-08-28 — AIRE rebindea en sesión caliente (aire-server #38)

`engine/core.py::_rebind` (llamado en cada turno, `turn.py:81`) tira el cliente
caliente cuando el turno pide OTRA forma (mode/tools/model/remote_tools):
una cache-creation de costo, cero memoria perdida (el transcript resume de
Postgres). Re-medido en vivo contra la puerta el 2026-08-28, misma sesión:
haiku → contestó haiku; `claude-sonnet-4-6` → contestó `claude-sonnet-4-6`.
La divergencia queda acotada a lo sumo al turno en vuelo. `model_diverged`
sigue como tripwire de regresión. El texto original del hallazgo, abajo,
queda como historia:

### ~~1. 🔴 AIRE ignora el `model` en una sesión CALIENTE (medido en vivo)~~

Probado el 2026-08-22 contra `https://gate.bernarduriza.com`, dos turnos en una
sola sesión:

```
requested: claude-haiku-4-5-20251001  → answered: claude-haiku-4-5-20251001
requested: claude-sonnet-4-6          → answered: claude-haiku-4-5-20251001
```

Sin error y sin aviso: el campo simplemente se ignora. Causa raíz en
`aire-server/server/aire/engine/core.py::_client_for` — las opciones (mode,
tools **y model**) se construyen sólo en un **pool miss**, así que un cliente
caliente conserva la forma con la que nació durante ~55 min
(`AIRE_POOL_IDLE_S=3300`).

**Qué significa aquí:** el `routing/` de este repo elige modelo POR TURNO
(Haiku/Sonnet/Opus por severidad + presupuesto Opus 24h). Por la puerta AIRE ese
ruteo degrada a *"el modelo con el que arrancó la sesión"* — una escalada a Opus
por un turno severo la contestaría Haiku, en silencio, hasta una hora.
`aire_route.model_diverged` loguea `aire_route_model_not_honoured` cada vez, así
que deja de ser invisible; **pero el ruteo sigue roto hasta que AIRE pueda
rebindear.** El judge NO sufre esto: sesión desechable por llamada = cliente
nuevo = modelo honrado.

**Hueco de AIRE:** la puerta necesita rebindear el `TurnSpec` cuando cambia
(o un `?rebirth=1` / `DELETE .../client` que fuerce el renacimiento del cliente).

### 2. ✅ CERRADO 2026-08-28 — las 10 tools viven en la puerta MCP-sobre-HTTP (v4.34.0/.1)

`api/mcp_http.py` sirve los MISMOS objetos SdkMcpTool por HTTPS; AIRE las
cablea vía `remote_tools` (aire-server #48, origen allowlisteado) y la
identidad sale de la fila durable de `engine/aire_principal` — el modelo
jamás la pide. Recibo en vivo arriba, en el Status. El texto original, como
historia:

### ~~2. 🔴 La personalidad pierde 9 de sus 10 tools de memoria~~

La ruta local monta `persona_memory` (in-process, contra el Postgres de
Khimeras) con diez tools. En AIRE sólo existen las del registry vetado
(`persona`, `memory`). Inventario honesto:

| Tool local | En la ruta AIRE |
|---|---|
| `get_user_facts` | ✅ **compensado**: el runner lo pre-consulta y lo compone in-band como `<user_memory>` |
| `get_recent_messages` · `search_messages` · `deep_memory` | ❌ perdidas. El tool `memory` de AIRE recuerda **su propio transcript** (por casita), no el historial de mensajes ni la búsqueda vectorial de Khimeras |
| `get_disclosure_log` · `get_emotional_arc` | 🔴 **perdidas — y son la superficie clínica**: fase del arco emocional y registro de revelaciones. Es exactamente lo que protege a un usuario vulnerable. No diluir esto es la orden; hoy la ruta AIRE lo diluye |
| `get_agent_facts` · `add_agent_fact` · `update_agent_fact` | ❌ perdidas (self-facts). El tool `persona` de AIRE edita la persona viva y las cubre **en parte** |
| `publish_html_artifact` | ❌ perdida |

**Un lado bueno, real:** al pre-componer los facts, el modelo ya no puede
*pedir* memoria de nadie — la identidad la pone el servidor, siempre. El
incidente del 2026-08-10 (atribuirle a Bernard un fact de Alex) es
estructuralmente imposible por esta ruta.

**Hueco de AIRE:** el registry necesita un tenant que hable con una base AJENA
al droplet — o el fork que el item original ya nombraba (un MCP HTTP hosteado
por ESTE repo que AIRE sólo cablea). Mientras tanto, las dos tools clínicas
tendrían que viajar in-band como los facts.

### 3. 🟡 La superficie de builtins NO es la misma, y este repo no puede imponerla

`FORBIDDEN_BUILTIN_TOOLS` de este repo = Bash/Write/Edit/NotebookEdit/Task. El
`mode=agent` de AIRE (auditado contra `engine/options.py::MODES` en `ef21e684`)
concede `Read, Write, Glob, Grep, WebSearch, WebFetch` y sólo deniega `Bash`.

**Aceptado, no escondido**, sobre dos hechos verificados: el hook `PreToolUse` de
`aire-server/engine/cage.py` deniega cualquier tool de archivos que resuelva
fuera de la casita, y **el droplet no tiene ninguna credencial de Khimeras** —
`POSTGRES_URL` y el OAuth de la flota nunca salen de este contenedor, así que la
amenaza del 2026-08-10 (una shell donde están los secretos) no se traslada.
`aire_route.AUDITED_MODE_{ALLOWS,DENIES}` guarda la auditoría y el boot truena si
NUESTRA config se desvía; **un cambio del lado del droplet es invisible aquí**
hasta re-auditar. Se loguea `aire_route_accepted_tool_delta` en cada boot.

**Hueco de AIRE:** la puerta no ofrece denylist de builtins por turno.

### 4. Huecos menores de AIRE (cada uno = un endpoint que falta)

- ~~**No hay sonda de "¿existe esta sesión?"**~~ — el hueco de AIRE sigue ahí
  (`Engine.has_session` existe adentro y no está expuesta), pero **este repo ya
  no depende de él**: desde el tercer eje el bit "esta sesión ya tuvo respuesta"
  es DURABLE (`aire_topics.answered_at`), así que un reinicio del runner ya no
  re-pliega historia que la sesión de AIRE ya tiene. Sólo vuelve a doler si
  Postgres está caído en el momento del reinicio, y eso se grita
  (`aire_route_topic_not_durable`). El endpoint seguiría siendo mejor —
  preguntarle a AIRE le gana a inferirlo — pero deja de ser un bloqueo.
- **La puerta no acepta bloques de documento/PDF** (`engine/vision.py` sólo
  valida imágenes). Los attachments no-imagen se **cuentan** y se loguean
  (`aire_route_attachments_dropped`), nunca se pierden en silencio.
- **Latencia sin medir**: Discord → Azure → droplet DO → Anthropic contra el
  actual Azure → Anthropic. Los turnos de voz/TTS son los sensibles. Medir antes
  de encender.

### 5. Huecos de AIRE que destapó el code review (2026-08-22)

Estos NO se arreglaron aquí — `aire-server` es de otra sesión. Cada uno es un
item candidato allá; lo de este repo ya está resuelto alrededor de ellos.

- **No hay `system_prompt` por turno en el body de la puerta.** El único modo de
  instalar un prompt es `/init` sobre la casita, así que la casita ES la
  superficie de prompt — y una compartida es una superficie que otro puede
  sobreescribir a media respuesta. De ahí sale el defecto 2 y su remedio
  (nombrar la casita por el digest del prompt). Un campo `system_prompt` en
  `POST .../messages` para `mode=complete` mataría la clase entera: el judge
  dejaría de necesitar casita propia.
- **No hay borrado ni escoba de SESIONES tampoco.** El tercer eje crea una
  sesión nueva por topic dentro de la misma casita, así que el transcript de un
  canal deja de crecer sin techo — pero los transcripts VIEJOS se quedan en las
  tablas de AIRE hasta que su escoba (`aire/sweep.py`, retención 30 días) los
  barre. Eso está bien para las tablas; lo que no existe es una manera de LISTAR
  o BORRAR las sesiones de una casita para auditarlas.
- **No hay borrado ni escoba de casitas.** AIRE barre sus TABLAS
  (`aire/sweep.py` + `aire-sweep.timer`, retención 30 días) pero una casita es
  un directorio en un droplet de 458 MB y nada la recoge. Por eso este repo
  rechazó la casita-por-llamada para el judge. Faltan un `DELETE
  /projects/{p}` (o TTL de casitas ociosas) y una manera de LISTAR lo que hay,
  para poder auditar cuántas casitas dejó el consumidor.
- **No hay rebind del `TurnSpec` en caliente** (ya nombrado en el hueco 1) — el
  mismo endpoint que arregle el modelo arregla también mode y tools.
- **No hay sonda de "¿existe esta sesión?"** (hueco 4) — hoy el fold de historia
  se gobierna con estado en RAM, ahora acotado por LRU, así que una expulsión
  cuesta exactamente lo mismo que un reinicio: un pliegue de más.

## El cableado (env fuera de banda, como la etapa 1)

El código lee la puerta del entorno; **jamás de un archivo del repo**:

- `TURN_BACKEND=aire` — enciende la ruta (default `local`)
- `AIRE_GATE_URL=https://gate.bernarduriza.com`
- `AIRE_AUTH_TOKEN` — Bearer de la puerta engine (o `AIRE_CANARY_TOKEN`)
- `AIRE_TURN_MODE=agent` (default; cualquier otro modo TRUENA el boot)
- `AIRE_FACTS_MAX_CHARS=6000` (default)
- `AIRE_TOPIC_IDLE_TIMEOUT_S=3600` (default) — el silencio del canal tras el
  cual la SESIÓN rueda a un topic nuevo. La perilla del tercer eje; su costo y
  por qué 3600, arriba. Requiere la tabla `aire_topics` (la crea el runner solo)
- `AIRE_CASITA_STATE_MAX=4096` (default) — techo del mapa de candados/espejo de
  topic por casita. No hay que tocarlo; existe para que el mapa no sea un leak
- `PG_POOL_MIN_SIZE=1` / `PG_POOL_MAX_SIZE=4` (defaults) — el pool asyncpg
  compartido que usa el pre-fetch de facts

Documentado en `docs/runbook_dr.md` § orden de reconstrucción, paso 4, con la
misma forma que dejó la etapa 1.

**Qué token va ahí es decisión de Bernard, no del agente.** El
`~/.secrets/aire-canary-token.txt` dice textualmente *"consumer: aire-front on
Azure"*, y `aire-llm-token.txt` dice *"Only Bernard has this"*. Ninguno nombra a
`persona-runner`, así que ningún agente lo despliega por su cuenta
([[credential-scope-is-the-named-surface]]). Encender:

```bash
az containerapp secret set -n persona-runner -g insult-rg \
  --secrets aire-auth-token=<el token que Bernard elija>

az containerapp update -n persona-runner -g insult-rg \
  --set-env-vars TURN_BACKEND=aire \
                 AIRE_GATE_URL=https://gate.bernarduriza.com \
                 AIRE_AUTH_TOKEN=secretref:aire-auth-token
```

Apagar (rollback, una revisión):

```bash
az containerapp update -n persona-runner -g insult-rg \
  --remove-env-vars TURN_BACKEND AIRE_GATE_URL AIRE_AUTH_TOKEN AIRE_TURN_MODE
```

## El paso de BORRADO (el flag es andamio, no permiso de estacionamiento)

Por [[migrations-end-with-deletion]]: mientras la ruta vieja viva, **está
prohibido escribir "migrado"** en cualquier reporte de este item. La redacción
honesta es la de arriba: *flag shipped, old path alive*.

Cuando Bernard declare permanente el flag, en el MISMO PR mueren:

1. `persona_runner/engine/session_pool.py` — el pool local de `ClaudeSDKClient`
2. `persona_runner/engine/options.py` — `build_options` y el árbol de
   `ClaudeAgentOptions` (`verify_required_tools` sobrevive sólo si algo lo usa;
   si no, muere con él y `aire_route.verify_audited_surface` queda de guard)
3. La rama local de `api/turn.py` y `api/judge.py`, y el flag `TURN_BACKEND`
   entero de `core/config.py`
4. `persona_runner/mcp_tools/` — los servers in-process — **sólo si** el hueco 2
   se cerró; hasta entonces NO se borran, se migran
5. Las specs de Playwright en `options.py` y la dep `@playwright/mcp` del
   Dockerfile
6. ~~`persona_runner/engine/aire_backend.py`~~ **HECHO 2026-08-27**: fi-runner
   0.20.0 (canal conda) trae `AIREBackend` + `AIREDoorError` + thin birth con
   las seis adaptaciones; `aire_route` importa `from fi_runner import
   AIREBackend` y el grep de `engine.aire_backend` devuelve vacío

**Criterio de terminado (el grep, no el relato):** las tres salidas vacías, en
el reporte, textuales.

```bash
grep -rn "session_pool\|build_options\|TURN_BACKEND" persona_runner/ tests/   # 0
grep -rn "claude_agent_sdk" persona_runner/                                   # 0
grep -rn "playwright" persona_runner/ Dockerfile.* environment.yml            # 0
```

Un PR que mueva código sin borrados en el diff no es una migración y no se llama
así.

## Camino canónico reusado (Art. 6)

- og118 (free-intelligence PRs #410–#413) como plantilla del cliente del engine
  door — `AIREBackend` vendoreado tal cual, con cuatro adaptaciones marcadas.
- aire-server #36 (`@base` / casita THIN) para el persona.md como CLAUDE.md vivo.
- El registry de tools de AIRE (#29/#36) para los tenants MCP.

## Siguiente paso

Un turno REAL de Discord por la puerta engine, mirado en vivo, antes de nada más.
Los huecos 1 y 2 son de Bernard: el 1 pide trabajo en `aire-server`, el 2 es un
fork de arquitectura (¿tenant del registry con credencial ajena, o MCP HTTP
hosteado aquí?). La etapa 1 ([[aire-gateway-stage1]]) ya da el espejo sin nada de
esto — no hay prisa técnica.
