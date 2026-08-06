# La proactividad murió en la purga — restaurarla en el host, como banda de agentes

Status: Accepted (dirección dada por Bernard 2026-08-06) · Proposed: 2026-08-06 por Bernard
Reporte: *"ya no es proactivo, antes Insult de vez en cuando saltaba a preguntarnos
cómo estábamos, y que él de su parte había estado entreteniéndose con
investigaciones… y eran investigaciones reales, llenaba partes en sus facts e iba
acumulando de vez en ratos, en periodos, más y más info, hasta que iba corriendo y
nos contaba."*

## Qué se perdió (forense, con receipts)

El commit **`2f8d9ad`** (la purga, 2026-07-14) borró **1,184 líneas** de sistema
proactivo y **nunca las replantó**:

| Archivo borrado | Líneas |
|---|---|
| `personas/insult/core/proactive.py` | 507 |
| `personas/insult/tasks/proactive.py` | 143 |
| `tests/core/test_proactive.py` | 481 |
| `personas/insult/prompts/proactive_social.md` | 25 |
| `personas/insult/prompts/proactive_world_scan.md` | 28 |

El original es de Bernard, **`b86a79b`** (2026-04-01, v0.4.0), y describe
literalmente lo que él extraña hoy:

> *"Insult sends unprompted messages to the most active channel every ~2-3 hours.
> `should_send_now()` con reglas de hora del día (no msgs 3-7am) + 40% random
> chance. `generate_proactive_message()` uses LLM with user facts + recent
> context. `_proactive_task` runs every 30 min, finds most active channel."*

El "iba acumulando investigaciones" es el **world scan**, de `ad96c8a` (v1.4.0):
*"~30% of proactive messages search the web"* + persistencia de los scans + un
canal opcional `#insult-world-feed`. Refinado después en `c48fedf` (dedupe +
filtro por fuente).

## La cadena cortada que quedó viva

`world_scans` sigue **en el esquema de Postgres**, con
`khimeras_shared/memory/repositories/world_scans.py`, instanciado por el store
(`self._world_scans = WorldScansRepository(...)`) y con su suite
(`tests/core/test_world_scans.py`) — y **CERO escritores**. Tabla con datos
viejos, repositorio vivo, productor muerto. Es la misma familia de defectos
cazada el 2026-08-06 (RULE 1 sin contexto, `recovered_without_context`
inalcanzable, `effort` sin consumidor): **la promesa sobrevive al mecanismo, y
nada se pone rojo.** Ver [[migrations-end-with-deletion]] y
`.claude/rules/router-observability.md`.

## Por qué "se siente muerto" aunque haya 4 workers

`persona_gateway/workers/` corre `agenda`, `research`, `reminders` y
`reflection`, y los cuatro loops SÍ arrancan (`gateway.py:147`). Pero:

- **`agenda` y `research` son REACTIVOS**: sólo existen si una persona ya emitió
  un marcador `[AGENDA:]` / `[RESEARCH:]` en un turno que **un humano provocó**.
  Sin mensaje entrante no nace nada.
- **`reflection` es el único con iniciativa propia**, y su cadencia es
  `reflection_min_interval_s = 604800` — **una vez cada 7 días**.
- Post-purga **toda persona es mention-gated**, así que nadie habla sin ser
  llamado.

Resultado: el sistema no tiene UN SOLO camino por el que una persona arranque una
conversación. `c86a3a3` ("agendas permanentes + research — los personas persiguen
metas solos", v4.22.35) recuperó la *persecución de metas*, pero no el *arranque*.

## La dirección (de Bernard, 2026-08-06)

No restaurar el proactive dentro de Insult otra vez. **El dueño es el host**
(`khimeras-host` / `demux_ai/`), que despierta a las personas por turnos —
banda de agentes: un turno habla una, otro turno otra.

Encaja con lo que el host ya es:
- Ya es **omnipresente** (ve todos los mensajes de todos los canales).
- Ya **rutea** y ya sabe **despertar** a una persona: `summon_persona` → el
  `/invite` del gateway. El mecanismo de arranque YA EXISTE y está probado.
- Desde **v4.32.28** tiene el **ring buffer de contexto por canal**
  (`HostDispatchLoop.remember` / `context_for`): ya sabe *qué se está hablando*,
  que es justo lo que hace falta para decidir a quién despertar y sobre qué.

## Camino canónico a reusar (Art. 6 — NO reinventar)

El módulo borrado es maduro y su núcleo es **persona-agnóstico**; se porta, no se
reescribe. Recuperable con `git show 2f8d9ad^:personas/insult/core/proactive.py`:

- `ConversationState` + `get_conversation_state` (activa 15 min / enfriándose 2 h)
- `compute_backoff_interval(unanswered_count)` — **2 h → 24 h**. El anti-spam: si
  nadie contesta, se calla progresivamente. Sin esto, la proactividad es plaga.
- `should_send_now(...)` — reglas de hora (nada 3-7am) + probabilidad
- `should_world_scan()` — el ~30% que investiga en vez de socializar
- `_detect_conversation_mood`, `_extract_conversation_topics`,
  `_extract_participants`, `_elapsed_description`, `_pick_search_topic`
- `generate_proactive_message`, `generate_world_scan_message`, `WorldScanResult`

Los dos prompts (`proactive_social.md`, `proactive_world_scan.md`) son CONTENIDO
y renacen como `.md` cargados por `load_prompt` — nunca inline
([[prompts-as-content-not-code]]).

## Slices propuestos

1. **Núcleo puro a `khimeras_shared/proactive.py`** — las funciones de decisión
   (estado, backoff, `should_send_now`, `should_world_scan`, mood/temas), sin
   Discord y sin persona. Con la suite portada de `tests/core/test_proactive.py`.
2. **`ProactiveWorker` en el host** (`demux_ai/`) — un `tasks.loop` que evalúa por
   canal y, cuando toca, **elige persona** y la despierta con `summon_persona`
   (`invited_by="host_proactive"`), con la razón sembrada desde el contexto del
   ring buffer.
3. **Rotación de la banda** — la política de a quién le toca: rotar, o elegir por
   tema usando el mismo cerebro gpt-4.1 que ya rutea. **Fork de Bernard.**
4. **Resucitar el world scan** — devolverle escritores a `world_scans` para que
   la acumulación entre periodos vuelva a existir, que es la mitad que Bernard
   más extraña ("iba acumulando… hasta que iba corriendo y nos contaba").
5. **Instrumentación desde el día uno** — que este sistema no pueda volver a
   morir en silencio: un evento por evaluación y por disparo, y un bloque en
   `scripts/router_health.py`. Un contador de proactividad en cero durante días
   tiene que poder verse.

## La decisión que es del dueño

- **Cadencia y agresividad**: el original era ~2-3 h con 40% de probabilidad.
  ¿Se conserva? Con 5 personas rotando, la frecuencia percibida se multiplica.
- **Rotación vs. afinidad temática** (slice 3).
- **Alcance de canales**: ¿sólo #general, o todos?
- El `unanswered_count` y su backoff son **innegociables** — sin ellos, cinco
  personas proactivas son cinco bots spammeando.
