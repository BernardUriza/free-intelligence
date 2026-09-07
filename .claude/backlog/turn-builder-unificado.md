# Builder de turno unificado — matar la clase "invite path olvidado"

Status: **In progress** — slice 2 (arnés de paridad mención↔invite) HECHO el
2026-08-06; slice 1 (`TurnSpec`/`TurnBuilder`) sigue sin existir.
Re-verificado 2026-09-07.
Proposed: 2026-07-16 by Claude (meta-hallazgo del /cruel-critic, Art. 9)

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
