# Builder de turno unificado — matar la clase "invite path olvidado"

Status: Proposed
Proposed: 2026-07-16 by Claude (meta-hallazgo del /cruel-critic, Art. 9)

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
