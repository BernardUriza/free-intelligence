# Renombrar `vultur-gateway` → `persona-gateway`

Status: Proposed
Proposed: 2026-07-05 (heredado de dos items Done que lo cargaban como follow-up:
addressed-to-sibling over-suppression y el move a `persona_runner/`)

## What it is

El Container App `vultur-gateway` ya no hospeda solo a Vultur — corre TODOS los
siblings del `persona_gateway` (Vultur, ALICE post-single-host, Frugívoro). El
nombre miente sobre su rol, igual que `insult-runner` mentía antes de volverse
`persona-runner`. Verificado 2026-07-05: `az containerapp list` sigue mostrando
`vultur-gateway`.

## Canonical path to reuse (Art. 6)

El molde es el rename ya ejecutado `insult-runner` → `persona-runner`
(2026-06-28, v4.21.102) y antes `insult-bot` → `discord-bot` (RENAME-1b):
scale-to-0 → create nuevo con el mismo template/secrets → delete viejo, más el
update de `cd.yml` y de toda referencia (`.claude/rules/sibling-personas.md`,
docs). Secuencia acordada con el coagent: cross-talk @frugi (Done) → move
`persona_runner/` (Done, v4.21.118) → **este rename** (PR separado).

## The decision that's the owner's

Timing del blip de downtime (~30s de Discord-visible para los siblings durante
el swap) — mismo trade que RENAME-1b.

## Status / next step

No arrancado. Todo el flujo es drivable vía `az`; el único atom es el GO de
Bernard por el blip.
