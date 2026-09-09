# Builder de turno unificado — matar la clase "invite path olvidado"

Status: **In progress** — slice 2 (arnés de paridad mención↔invite) HECHO el
2026-08-06; slice 1 (`TurnSpec`/`TurnBuilder`) sigue sin existir.
Re-verificado 2026-09-07.
Proposed: 2026-07-16 by Claude (meta-hallazgo del /cruel-critic, Art. 9)

## Re-chequeo 2026-09-09 — el item vale, pero no por el slice que le da nombre

El estado es el que decía: `TurnSpec`/`TurnBuilder` no existen (el único hit de
`grep` es un docstring de `aire_route.py:659`, y encima nombra otro concepto), y
`_handle` (`gateway.py:248`) y `respond_to_invite` (`:401`, el item dice 383 —
la línea corrió) siguen siendo dos entry points.

**Lo que cambia es la lectura del valor.** El slice 2 ya impone paridad desde el
CI, así que el refactor del slice 1 rinde poco por sí mismo. Lo que rinde son
las asimetrías que el arnés lleva marcadas y que nadie ha ido a cerrar: hoy
`pytest tests/arch/test_mention_invite_parity.py -q` da **48 passed, 5 xfailed**,
y esos cinco `xfail(strict=True)` son defectos abiertos, no deuda abstracta:

1. **El `memory.store` del turno humano está desnudo en `_handle`** y guardado en
   invite. Un parpadeo de Postgres en una @mención mata el turno con un "…".
2. **`attachment_blocks`, igual**: invite degrada a texto, `_handle` revienta. Un
   adjunto corrupto se come la respuesta.
3. **Invite consulta el corpus con el `reason` del router, no con lo que dijo el
   humano.** Fix de una línea (`corpus_query=subject_ask or reason`) — y es el
   camino por donde pasa TODO el tráfico desde el cutover del host.
4. **Invite sin sujeto humano escribe facts bajo el id del propio bot.**
5. El summon-por-edición murió en el cutover: el gateway se auto-suprime y el
   host no escucha ediciones.

Dos de los cinco (1 y 2) pierden la respuesta delante del humano, y el 3 es una
línea. Ninguno tiene issue. Si este item se ejecuta algún día, el orden honesto
es cerrar esos cinco primero y decidir después si el builder sigue haciendo
falta — puede que no.

## Cerradas el 2026-09-09 (v4.38.26): 1, 2, 3 y media de la 4

El arnés pasó de **5 `xfail` a 2**. Las cuatro se verificaron en rojo revirtiendo
cada fix antes de darlas por buenas.

- **1 y 2** — el `memory.store` y `attachment_blocks` de `_handle` quedaron
  envueltos, copiando el patrón que el camino de invite ya tenía. Un parpadeo de
  Postgres o un adjunto corrupto degradan; ya no se comen la respuesta.
- **3** — `corpus_query=subject_ask or reason`. **Y destapó una contradicción
  entre dos arneses del mismo repo:** `tests/core/test_gateway_corpus_wiring.py`
  fijaba `query == reason` como el comportamiento correcto —consagrando el
  defecto— mientras el arnés de paridad lo marcaba `xfail`. Ganó el que medía el
  daño; el otro se corrigió y ganó su resistencia (sin texto humano, el `reason`
  sigue siendo la query).
- **4, la mitad que corrompe datos** — un `[REMEMBER:]` en un turno sin sujeto
  humano ya no escribe facts bajo el id del bot: se descartan con
  `remember_discarded_no_human_subject`. Salió barato porque `bot_user_id` ya
  viajaba hasta `TurnRunner`; sólo había que mirarlo. Un fact sin dueño no se
  reubica.

**Las dos que quedan, y por qué no se cerraron:**

- **4, la mitad del runner.** Se le sigue mandando el id del bot como `user_id`,
  así que reconstruye "los facts del autor" de un autor que no existe. No se
  cierra con un guard: el runner NECESITA un id para armar el turno, y elegir qué
  mandarle es una decisión de contrato —un centinela, un id nulo que sepa leer, o
  el `channel_id`—. Se deja roja en vez de taparla con un valor inventado.
- **5, el summon por edición.** No es un fix sino una capacidad que hay que
  construir en el host: hoy el gateway se auto-suprime en ediciones y el host no
  tiene listener.

**Hallazgo lateral, sin cerrar:** `subject_ask` se calcula del contenido del
trigger **aunque su autor sea un bot** (`gateway.py`, la línea es
`subject_ask = (react_to.content or "").strip()`, sin mirar `subject`). O sea que
`relevant_query`, `guidance_message` y ahora `corpus_query` pueden ir keyed por
el texto de un bot. Es viejo —viene de `b9f8de4`, no de este cambio— y
consistente entre los tres, así que no se tocó hoy; pero si el trigger de un bot
alguna vez trae texto largo, la memoria relevante y el corpus se recuperan contra
lo que dijo una máquina.

## Re-chequeo 2026-09-07 (auditoría del backlog)

- **Slice 2 existe**: `tests/arch/test_mention_invite_parity.py`, nacido en
  `d4fefb9` (2026-08-06, v4.32.37 — el mismo día de la auditoría anterior, que
  lo reportó ausente) y reforzado en `5319ec2` (2026-08-31, #40/#56). Su
  docstring nombra literalmente la clase de bug de este item (*"el invite path
  olvidado"*) y lo cierra de dos formas: **estructural** (AST: las dos puertas
  invocan el mismo conjunto de servicios de `self`) y **de comportamiento** (el
  mismo mensaje por las dos puertas, capacidad por capacidad). Las asimetrías
  reales quedan como `xfail(strict=True)`; las deliberadas (STT del host,
  recepción) como excepciones explícitas.
- **Slice 1 no**: `grep -rn "TurnSpec\|class TurnBuilder" --include='*.py' .`
  → un solo hit, y es un docstring de `persona_runner/engine/aire_route.py:659`
  hablando del `TurnSpec` de fi-runner (otro concepto). `_handle` y
  `respond_to_invite` siguen siendo dos entry points en `persona_gateway/gateway.py`.
- `ls tests/arch/` hoy: 7 arneses (eran 3 el 08-06).

Con el arnés vivo, el valor restante del slice 1 baja: la paridad ya se
ejecuta en CI. Si se construye, es por limpieza estructural, no por seguridad.

## Verificación 2026-08-06 (qué se movió sin cerrar el item)

- **Adelantado**: `persona_gateway/turn_context.py` (`TurnContextBuilder`, nacido
  en el destripe del God Object — a026661 v4.22.57 / f52f807 v4.27.6) YA
  centraliza la mitad cara: contexto reciente, `guidance_for_turn`, bloque de
  corpus (`append_corpus_block`), facts relevantes y reminders. Esa mitad ya no
  se cablea dos veces.
- **NO hecho**: `grep -rn "TurnSpec\|TurnBuilder" --include='*.py' .` → **cero
  hits**. `_handle` (gateway.py:248) y `respond_to_invite` (gateway.py:383)
  siguen siendo dos entry points artesanales: cada uno arma por su cuenta el
  `ask`, los `attachment_blocks` (`self._ingest.attachment_blocks`, con su propio
  try/except sólo en el invite) y el STT de DM.
- **NO hecho**: el arnés de paridad. `ls tests/arch/` → sólo
  `test_dockerfiles_log_json.py`, `test_import_smoke.py`,
  `test_routing_prompt_promises_are_kept.py`. Nada obliga a que una capacidad
  nueva se pruebe en AMBOS paths.
- La clase de bug siguió cobrando piezas después de capturar el item: v4.32.7
  (DM muertos), v4.32.13 (nota de voz en DM en silencio), v4.32.26/27 (el
  marcador de invitación filtrado y luego ALICE incovocable).

## What it is
Tres bugs de la MISMA clase en 48h: reactions sin target en invites (fix
2026-07-14), imágenes ciegas en invites (fix 2026-07-16 AM, v4.22.74), corpus
ausente en invites (fix 2026-07-16 PM, v4.24.2). Causa raíz: `_handle` (mención)
y `respond_to_invite` arman turnos por caminos artesanales separados — cada
capacidad nueva (attachments, corpus, guidance, STT) se cablea a mano en cada
path y el invite siempre queda al último. Post-purga el invite ES el path
principal (el host rutea ahí todo turno sin mención): la asimetría garantiza
que la próxima capacidad repita el bug.

## Canonical path to reuse (Art. 6)
Un `TurnBuilder` (o extender `TurnRunner`) donde ingest/corpus/guidance entran
UNA vez: ambos entry points producen un `TurnSpec` (query, mensajes, trigger
message opcional) y el builder aplica attachments + corpus + guardián con el
mismo código. Los tests de paridad (arch harness): toda capability que consuma
el turn path debe tener test en AMBOS paths o CI truena.

## The decision that's the owner's
Timing — es refactor estructural del gateway recién modularizado; secuenciarlo
cuando el turn path esté quieto unos días.

## Status / next step
No construido. Slice 1: TurnSpec + builder con attachments/corpus/guidance;
slice 2: arnés de paridad mention↔invite.
