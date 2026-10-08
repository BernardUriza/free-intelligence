# Rename `discord-bot` → `server-bot`

Status: **REPO RENOMBRADO 2026-09-23** (`gh repo rename server-bot`, go de Bernard
tras la investigación de /histerical-search) — queda sólo el RG, que no es rename
sino reconstrucción (abajo). Registry: **`serverbotacr` ya no existe, las
imágenes viven en GHCR desde 2026-08-12** bajo el path `ghcr.io/bernarduriza/discord-bot/*`,
que se QUEDA (namespace libre, no ligado al nombre del repo; cero riesgo de deploy).
Proposed: 2026-06-18 by Bernard
Re-verificado: 2026-09-09 (`az containerapp list`, `az acr list`, `az containerapp job list`)

## Hecho 2026-09-23 — el repo ya es `server-bot`

Alcance ejecutado (mínimo, decidido por Bernard): el repo en GitHub. NO se tocó:
el folder local (`~/Documents/discord-bot` — la memoria de Claude Code de este
proyecto está atada al nombre del folder, `~/.claude/projects/-Users-…-discord-bot`;
renombrarlo sin mover esa carpeta deja la sesión amnésica), `REGISTRY` en `cd.yml`,
las Container Apps ni los filtros KQL.

Recibos del mismo día:
- `gh repo view BernardUriza/server-bot` → `server-bot`, default `main`.
- `git ls-remote https://github.com/BernardUriza/discord-bot.git main` → resuelve
  (redirect de git para el nombre viejo, como dice la doc de GitHub).
- `git remote set-url origin https://github.com/BernardUriza/server-bot.git` aquí;
  Alex (`ferux485`, única colaboradora) recibe el mismo comando por #general.
- Referencias literales al slug viejo en código: `REGISTRY` (se queda), un
  comentario en `ai-gatekeep.yml` (actualizado), dos constantes de test
  (cosméticas). Ningún Dockerfile lleva `org.opencontainers.image.source`, así que
  no hay liga paquete↔repo que romper. Las URLs históricas a issues/PRs en
  backlog, `dashboard/nomina` y `training-contributors/` redirigen solas; no se
  reescriben.
- Regla dura de GitHub: **nunca volver a crear un repo llamado `discord-bot`** —
  mataría los redirects.
- `.claude/constitution.toml` sigue con `[repo] id = "discord-bot"`: es el id del
  lock de agent-constitution, no el slug de GitHub; cambiarlo es re-lockear y es
  decisión aparte.

## Re-chequeo 2026-09-09 — sin cambios

`az acr list` → sólo `insultacr`, con los dos inquilinos de siempre: la app
retirada `discord-bot` (Running, min=0, `insult-bot:d6fa36c`) y `rancho-studio`.
Las tres apps del repo, más `susurro-gateway` y `aire-front`, pullean de GHCR.
`az containerapp job list -g insult-rg` → vacío. RG→`server-rg` sigue agendado.


## Re-chequeo 2026-09-07 (auditoría del backlog)

El bloque del 08-06 de abajo quedó rancio en tres afirmaciones. Estado real:

- **`serverbotacr` está BORRADO.** `az acr list -g insult-rg --query "[].name"`
  → sólo `insultacr`. El 2026-08-12 el registry se movió a GHCR
  (`cd.yml:69`: *"GHCR replaced serverbotacr on 2026-08-12"*, `REGISTRY:
  ghcr.io/bernarduriza/discord-bot`); la razón vive en
  `.claude/rules/architecture.md` § Registry.
- **Las 3 apps del repo pullean de GHCR**, no de `serverbotacr`
  (`az containerapp list -g insult-rg` → `ghcr.io/bernarduriza/discord-bot/
  {persona-gateway,persona-runner,khimeras-host}:798ba774…`). Y
  **`susurro-gateway` también salió de `insultacr`**: hoy corre
  `ghcr.io/bernarduriza/susurro/gateway:6c70a25c…` — el CD del repo `susurro`
  ya migró solo.
- **`insultacr` sigue vivo con DOS inquilinos**, no con "3 proyectos ajenos + el
  job": la app retirada `discord-bot` (min 0, `insult-bot:d6fa36c7…`) y
  `rancho-studio` (`rancho-studio:973daa1`). `aire-front` también se fue a GHCR
  (`ghcr.io/bernarduriza/aire-server/front`). El job `fact-consolidation` ya no
  bloquea nada: `az containerapp job list -g insult-rg` → vacío (borrado
  2026-08-06, ver [[cadenas-cortadas-post-purga]]).
- Lo que sigue exactamente igual: `insult-rg` → `server-rg` es reconstrucción con
  downtime y sigue **agendado por Bernard, no ejecutado**; el repo sigue
  llamándose `discord-bot`.

Borrar `insultacr` hoy requiere: eliminar la app `discord-bot` (retirada, la
regla de arquitectura ya dice que el fix honesto es borrarla) y migrar o aceptar
tumbar `rancho-studio` (repo ajeno a éste).

## Estado real al 2026-08-06 (auditoría — dos cosas cambiaron desde el 07-25)

- **Las 3 apps del repo SÍ pullean de `serverbotacr`**: persona-gateway,
  persona-runner y khimeras-host corren `serverbotacr.azurecr.io/<app>:e4f38d7`.
- ⚠️ **`susurro-gateway` volvió a `insultacr`**: hoy corre
  `insultacr.azurecr.io/susurro-gateway:30ee47e5` (tiene ambos registries
  configurados). Se le repuntó el 07-25, pero su propio CD —que vive en el repo
  `susurro` y publica a `insultacr`— lo devolvió al ACR viejo en el siguiente
  deploy. Repuntar la app sin repuntar el CD del repo dueño es reversible por
  diseño: para que la migración pegue hay que tocar ESE workflow.
- ✅ **El job `insult-canary` YA NO EXISTE** — se borró hoy (v4.32.27, `ccea31e`,
  *"muere el canary zombie"*); `architecture.md` llevaba seis semanas afirmando
  que estaba borrado y era falso. `az containerapp job list -g insult-rg` ahora
  devuelve **un solo job**.
- ❌ **`fact-consolidation` sigue vivo y sigue apuntando a la imagen muerta**
  (`insultacr.azurecr.io/insult-bot:d6fa36c7`, cron `0 0 31 2 *` = 31-feb).
  Sigue siendo el bloqueador del borrado limpio de `insultacr`, junto con la app
  `discord-bot` retirada (min=0) y los 3 proyectos ajenos.
- `az acr list -g insult-rg` → **`insultacr` y `serverbotacr` coexisten**.

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
  **Actualización 2026-08-06:** `insult-canary` BORRADO (v4.32.27 `ccea31e`).
  `fact-consolidation` sigue ahí — su borrado cruza con el item
  [[cadenas-cortadas-post-purga]] #5 (es la maquinaria congelada por seguridad
  clínica de Alex: primero se re-hogar, después se borra el job viejo).
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
