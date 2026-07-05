# Fix addressed_to_sibling over-suppression (alias-anywhere silencia a Insult)

Status: Done
Proposed: 2026-07-04 by Claude (descubierto durante la verificación de ALICE single-host; coagent lo puso en la cola post-soak)

## What it is

`personas/insult/cogs/chat/batch.py:addressed_to_sibling()` suprime a Insult cuando
CUALQUIER alias de sibling aparece como palabra en el mensaje. "insult, invita a
alice al canal" → `msg_skipped_addressed_to_sibling` (recibo: 2026-07-04 21:50:05Z,
message_id=1523083505230151971) — el mensaje se dirige a Insult POR NOMBRE y aun
así Insult calla. Consecuencia: el `invoke_alice` orgánico solo puede disparar en
turnos que NO nombran a ALICE, o sea casi nunca cuando el usuario lo pide explícito.

## Canonical path to reuse (Art. 6)

La señal 1 y 2 del propio `addressed_to_sibling` (user-mention / role-mention) son
correctas; el hoyo es la señal 3 (text alias). Fix candidato: no suprimir cuando el
mensaje ABRE dirigiéndose a Insult ("insult," / @Insult primero) aunque nombre a un
sibling después — el destinatario es quien encabeza. Tests obligatorios: positivo
("alice, ¿estás?" → suprime) + resistencia ("insult, invita a alice" → NO suprime),
per el patrón mutator de `.claude/rules/robustness.md`.

## The decision that's the owner's

Ninguna — es un fix de lógica con tests. El coagent lo ordenó DESPUÉS del soak de
ALICE single-host y antes del rename vultur-gateway → persona-gateway.

## Status / next step

DONE 2026-07-05 — v4.21.113 (`783b00d`): `_opens_addressing_host()` corta el gate
cuando el mensaje ABRE con "insult"/@Insult/mention-pill propio; 5 tests nuevos
(positivo + resistencia, incl. "insultante" no des-mutea). alice-bot legacy ya
eliminado (v4.21.112). Quedan en cola: cross-talk @frugi, rename vultur-gateway→persona-gateway.
