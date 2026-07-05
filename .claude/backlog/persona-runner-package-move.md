# Mover el runner compartido a `persona_runner/` top-level

Status: Accepted
Proposed: 2026-07-05 by Bernard (hallazgo Claude, diseño dialogado con el coagent insult-gpt vía /exchange-coagent)

## What it is

El servicio FastAPI del Container App `persona-runner` — el brain compartido que
sirve a TODAS las personas Claude vía `persona_id` — vive en
`personas/insult/agent/runner.py` por arrastre histórico, no por decisión: nació
como `insult/agent/runner.py` (v3.9.22, cuando Insult ERA el sistema) y el demux
fase 1 (`31b4301`) hizo el move mecánico `insult/` → `personas/insult/`
llevándose el runner adentro. El multi-persona (`_resolve_persona_path`,
allowlist de `shared/personas/*.md`) se atornilló después sin mudarlo. El árbol
miente: infraestructura compartida adentro del paquete de UN sibling.

Veredicto del coagent (2026-07-05): *"el runner ya no es comportamiento de
Insult… si vive bajo personas/insult/, el árbol miente y cada nuevo sibling
hereda deuda mental."* Ni `demux_ai/` (host-router gpt-4.1, otra capa) ni
`khimeras_shared/` (contratos/capabilities, no un servicio con auth/env/HTTP
lifecycle) son el hogar.

## Canonical path to reuse (Art. 6)

Paquete top-level `persona_runner/`, simétrico a `persona_gateway/` (el patrón
ya existe en el repo). PR mecánico, GO/NO-GO acordado con el coagent:

**GO:**
- `git mv personas/insult/agent/*` → `persona_runner/` + update imports
- update `infra/azure/runner.Dockerfile` COPYs (líneas ~61)
- update `tests/arch/test_runner_dockerfile_copies_imports.py`
- API `/v1/turn` idéntica, env vars sin cambio, Container App name sin cambio
- shim `from persona_runner.runner import *` en el path viejo SOLO si la suite
  no permite borrarlo limpio; preferir borrado limpio (sin legacy que confunda)

**NO-GO (no mezclar en este PR):**
- rename `INSULT_AGENT_RUNNER_URL/TOKEN`
- rename imagen ACR `insult-bot:<sha>`
- cambios al contrato `/v1/turn`, persona resolution, auth, topología

**Verificación requerida:** arch tests + Dockerfile COPY ratchet green, smoke
real `/v1/turn`, cada persona responde (`persona_id` omitido=Insult, vultur,
alice, frugivoro), round-trip en #general.

## The decision that's the owner's

Ninguna — diseño y secuencia ya consensuados. Secuencia acordada (coagent,
2026-07-05): **1)** fix @frugi cross-talk → **2)** este move → **3)** rename
`vultur-gateway` → `persona-gateway` → **4)** cleanup env/image names. NO
juntar el move con el rename del gateway en un PR (superficies distintas; si
algo falla conviene saber cuál fue).

## Status / next step

GATE ABIERTO (2026-07-05): el cross-talk @frugi era un doble-store multi-writer
en el Postgres compartido (Insult plumbing + persona_gateway persistían el mismo
turno). Fix raíz shipped en v4.21.116 `6385c1a` (discord_message_id + unique
partial index + ON CONFLICT DO NOTHING) y E2E-verificado en #general: 1 fila por
mensaje + `memory_store_deduped` en el gateway + Frugívoro respondiendo normal.
Este move es el siguiente paso de la secuencia. Hermano de deuda de nomenclatura
de [[rename-discord-bot-to-server-bot]].
