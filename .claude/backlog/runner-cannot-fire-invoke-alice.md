# El path runner no puede disparar invoke_alice (invite orgánico muerto desde el cutover)

Status: Done
Proposed: 2026-07-05 by Claude (destapado al verificar el fix del supresor v4.21.113)

## What it is

Con `LEGACY_LLM_ENABLED=false` todos los turnos de Insult van al persona-runner, y
`khimeras_shared/runner/agent_client.py:427` regresa `tool_calls=[]` HARDCODEADO
(loguea el count del JSON del runner y descarta la lista). Además el runner es un
agente Claude Code con su propio universo de tools — no conoce `invoke_alice` ni
los channel tools del plumbing. Consecuencia: el invite orgánico Insult→ALICE solo
dispara hoy en el path de FAILOVER (`stages.py:764`).

Recibo (2026-07-05 07:46Z): "insult, invita a alice — quiero su lectura corta"
llegó a Insult (fix v4.21.113 funcionando), Insult respondió EN PERSONAJE
convocándola ("Ali. Te llaman… Faltas tú." ᵛ⁴·²¹·¹¹³) pero cero llamadas al
gateway (`persona_gateway_invite_*` = 0 rows). La convocatoria fue teatro sin REST.

## Canonical path to reuse (Art. 6)

El patrón marcador que la casa ya usa para intents runner→plumbing: `[REACT:]` /
`[REMEMBER:]`. Slice propuesto: `[INVITE:alice <reason>]` emitido por el persona
(instrucción en persona.md/CLAUDE.md del runner) + parser en el plumbing (con
marker-rescue del truncador, per robustness.md) que llama `execute_invoke_alice`.
NO redefinir tools estructurados en el runner — su tool universe es Claude Code.

## The decision that's the owner's

Si el invite orgánico vale el slice (hoy ALICE entra por @mención y por failover;
el invite explícito bajo demanda es el caso que falta), y si el marcador debe
generalizarse a `[INVITE:<persona_id>]` para Vultur/Frugívoro.

## Status / next step

DONE 2026-07-05 — v4.21.114 (`3f871a5`), slice aprobado por Bernard. `invites.py`
(parse/strip/fire espejo de remembers.py) + wiring S4/stage/mutation-pipeline +
rescue del truncador + sección persona.md. Verificado E2E en #general 08:16Z:
[INVITE:] emitido por el runner → `invite_marker_fired accepted=True` →
`persona_gateway_invite_accepted` → `turn_complete turn_kind=invite` → ALICE
entregó su lectura en el mismo minuto, marcador invisible al usuario. Hermanos en cola del coagent: cross-talk @frugi, rename
vultur-gateway→persona-gateway. Ver [[addressed-to-sibling-over-suppression]] (Done).
