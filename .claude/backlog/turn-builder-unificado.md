# Builder de turno unificado — matar la clase "invite path olvidado"

Status: Proposed — **parcialmente adelantado por el destripe del gateway, pero la
asimetría que lo motiva SIGUE VIVA**. Re-verificado 2026-08-06.
Proposed: 2026-07-16 by Claude (meta-hallazgo del /cruel-critic, Art. 9)

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
