# Dedup persona.md (raíz) vs shared/personas/insult.md

Status: Proposed
Proposed: 2026-07-16 by Claude (detectado al editar el DNA de Insult)

## What it is
`persona.md` (raíz) y `shared/personas/insult.md` son copias byte a byte desde el
renacimiento (296fe8d, «verbatim» deliberado) sin ningún mecanismo de sync. El
runner usa AMBOS: `insult.md` cuando llega `persona_id="insult"` (el turn path
vivo), `persona.md` como fallback de `PERSONA_PATH` (persona_id ausente/inválido)
y como target de `scripts/sync_capabilities.py` (pre-commit). Dos copias de una
superficie = violación Art. 6; hoy el drift lo bloquea el arnés
`test_insult_dna_and_runner_fallback_never_drift` (CI rojo si divergen), pero el
arnés es la vacuna, no la cura.

## Canonical path to reuse (Art. 6)
Una sola fuente: `shared/personas/insult.md`. Rutas candidatas:
1. Apuntar `PERSONA_PATH` default a `/app/personas/insult.md` + borrar
   `persona.md` + `COPY persona.md` del Dockerfile + repuntar
   `sync_capabilities.py` a `shared/personas/insult.md`.
2. Symlink `persona.md → shared/personas/insult.md` — REQUIERE probar el
   comportamiento de Docker COPY con symlinks en un build real (Loop Law: no
   adivinar).
La opción 1 es la limpia (migration ends with deletion); auditar antes quién
llama al runner SIN persona_id (¿/v1/judge? ¿consolidator?) para no cambiarle
el system prompt a un path vivo.

## The decision that's the owner's
Ninguna — es deuda técnica ejecutable; solo secuenciarla fuera de un turno de
contenido de persona.

## Status / next step
No construido. Paso 1: grep de llamadas a `/v1/turn`/`chat()` sin `persona_id`
para mapear consumidores reales del fallback.
