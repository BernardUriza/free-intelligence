# Rename `discord-bot` → `server-bot`

Status: In progress (ACR hecho 2026-07-25; RG + repo + apps pendientes)
Proposed: 2026-06-18 by Bernard

## PROGRESO 2026-07-25 — el ACR ya está migrado

**HECHO (v4.32.5, commit ac11774):** el registry `insultacr` → **`serverbotacr`**
para el runtime de discord-bot. Bernard lo pidió explícito ("hazlo ahora mismo").
Nombre válido: `serverbotacr` (los ACR NO admiten guiones → NO "serverbot-acr").
- Creado `serverbotacr` (Basic, eastus, admin on) en insult-rg.
- Importadas las 4 imágenes EN USO (`az acr import`): persona-runner, persona-gateway,
  khimeras-host @ `1c8438f`; susurro-gateway @ `2ba817d2`.
- Repuntadas las 4 apps (`registry set` + `--image serverbotacr...`), verificadas
  **Healthy/Running** pulleando del nuevo ACR.
- `cd.yml` (REGISTRY/ACR) y `scripts/dr_inventory.sh` → serverbotacr.

**NO HECHO — y por qué (hallazgo de alcance, Art. 5):**
- **`insultacr` NO se borró: es un ACR COMPARTIDO.** portfolio-spring (portfolio-rg),
  rancho-studio, aire-front tienen sus imágenes ahí. Borrarlo los rompe. Para
  eliminar insultacr hay que primero migrar (o aceptar tumbar) esos 3 proyectos.
- **Jobs huérfanos que aún apuntan a `insultacr/insult-bot`:** `fact-consolidation`
  (cron `0 0 31 2 *` = 31-feb, fecha imposible → nunca dispara; últimos runs Failed
  9-13 jul, muerto desde antes) e `insult-canary` (el canary retirado). Ambos
  candidatos a BORRAR — su imagen `insult-bot:d6fa36c7` ya no existe (purgada).
- La app `discord-bot` retired (min=0, sin scale rules) también apunta a
  insult-bot; inocua pero bloquea el borrado limpio de insultacr.

## `insult-rg` → `server-rg`: NO es un rename, es una RECONSTRUCCIÓN (Art. 7)

Bernard pidió (2026-07-25) renombrar también el RG. La verdad dura:
- **Azure NO renombra Resource Groups.** "Renombrar" = crear `server-rg` + mover
  todos los recursos + borrar el viejo.
- **Container Apps y su managed environment (`prod-env`) NO soportan `az resource
  move` entre RGs.** La única vía es RECREAR el environment + las 3 apps desde cero
  → **downtime Discord-visible real** + reconfigurar secrets/ingress/registries.
- Costo alto (downtime + reconstrucción) por cero función (el nombre del RG es el
  más interno de todos, ningún humano externo lo ve).
- **Decisión de Bernard (2026-07-25): agendado, NO ejecutar reactivo.** Se hace
  dentro de este proyecto coordinado, en una ventana dedicada, sin downtime
  sorpresa a media conversación.

## What it is

Renombrar el proyecto de `discord-bot` a `server-bot` porque el sistema ya
no es "Discord cognitivo" a secas — con el demux apunta a ser un host
multi-superficie (Discord hoy, otras superficies después). El nombre actual
ata el sistema a una sola transporte.

## La distinción que importa (stress-test, Art. 7)

Hay TRES "nombres" en juego, no uno — y "server-bot" no encaja en los tres:

| Capa | Hoy | ¿server-bot encaja? |
|---|---|---|
| **Repo / sistema** (git repo, identidad del proyecto) | `discord-bot` | **SÍ** — refleja la visión multi-superficie |
| **Container App gateway de Discord** (la plomería que escucha Discord) | `discord-bot` (Azure CA) | **NO** — esta capa ES específica de Discord; en el futuro multi-superficie habría `discord-gateway` + `slack-gateway` + …; el componente surface-agnostic es el host `demux_ai`, no esta plomería |
| **Imagen ACR** | `insult-bot:<sha>` (legacy) | aparte — ya pendiente de renombrar en p6-acr |

Conclusión a validar con Bernard: **renombrar el REPO/sistema a `server-bot`,
pero el Container App de la plomería de Discord debería QUEDARSE con nombre
Discord** (p.ej. `discord-gateway`), no volverse `server-bot`. El "server"
genérico es el host (`demux_ai`), que ya tiene su propio nombre.

## Canonical path to reuse (Art. 6)

Ya hay precedente exacto: **RENAME-1b** (`insult-bot` → `discord-bot`,
v3.9.30, 2026-05-14). Documentado en `.claude/rules/architecture.md`
§ Nomenclature. La mecánica de rename de Container App fue
scale-to-0 → create new → delete old, con ~30s de downtime Discord-visible.
Clonar ESE runbook, no inventar uno nuevo.

Superficies que toca un rename de este tipo (del runbook RENAME-1b):
- Azure Container App (nombre físico) + FQDN nuevo
- Referencias en `cd.yml` / `ci.yml` (`az containerapp ...`, `az acr build --image ...`)
- Filtros KQL (`ContainerAppName_s in ("insult-bot","discord-bot", ...)` — sumar el nuevo durante la ventana de retención de logs ~30d)
- Memorias + `reference_debug_endpoint` (FQDN de prod)
- `.claude/rules/{architecture,testing,workflow}.md` (todas citan el nombre)
- `CLAUDE.md`
- El repo en GitHub (rename del repo NO rompe, GitHub redirige, pero actualizar remotes locales)

## The decision that's the owner's (Bernard)

- **Alcance del rename:** ¿solo el repo/sistema? ¿también el Container App?
  ¿el módulo de plomería? (recomendación arriba: repo sí, gateway de Discord
  no — déjalo Discord-named).
- **Timing:** un rename de Container App tiene downtime Discord-visible (~30s
  por el runbook). No hacerlo en medio de una conversación viva
  (regla del blob/conversación en `workflow.md`).
- **Nombre exacto del repo:** `server-bot` vs algo que distinga repo-vs-host
  (el host ya es `demux_ai`).

## Status / next step

No construido — capturado el día que Bernard lo propuso. Desbloquea cuando
él dé el go + decida el alcance. Subordinado a: terminar el host del demux
(`demux_ai` pasos 1–6) primero — renombrar antes de que exista el host real
sería renombrar una cosa que aún está mutando.

Relacionado: `p6-acr` del checklist (renombrar la imagen ACR legacy
`insult-bot:<sha>`) — mismo tipo de operación, conviene agrupar.
