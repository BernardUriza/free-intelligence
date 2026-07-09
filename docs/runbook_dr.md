# Runbook DR — reconstruir el compute de Khimeras

**Criterio de este documento:** otra persona reconstruye el compute sin depender
de la memoria de un chat. Si un paso aquí exige "preguntarle a Claude qué pasó",
el paso está mal escrito.

Nace del incidente del **2026-06-25**: una suspensión por facturación destruyó
todo el compute de la suscripción (invoice G163074988, $131.25). El data plane
sobrevivió; el resto hubo que rehacerlo a mano. El germen de este runbook fue
`~/.secrets/discord-bot-RECOVERY-STATE.md` (breadcrumb escrito durante el
incidente, ya stale: nombra `vultur-gateway` y `alice-bot`, que ya no existen).

## Regla cero — el inventario no vive en este archivo

Un inventario a mano rota el día que Bernard toca infra. La verdad se imprime:

```bash
./scripts/dr_inventory.sh            # estado real: apps, jobs, data plane, alertas, secretos
./scripts/dr_inventory.sh secrets    # solo la auditoría de secretos (fingerprints, nunca valores)
```

Este documento solo carga lo que una query **no puede** saber: el orden de
reconstrucción, las trampas, y cómo se verifica de verdad.

## Lo que se pierde y lo que no

| Capa | ¿Sobrevive a una suspensión? | Reconstruible |
|---|---|---|
| Postgres `development-pg-n66dz` (memoria longitudinal, facts) | sobrevivió en 2026-06-25 | **NO — es el único recurso irreemplazable** |
| Container Apps + `prod-env` + Jobs | no | sí, ~2h con este runbook |
| Imágenes en ACR `insultacr` | sí | sí (`az acr build` o el CD) |
| Secretos dentro de los Container Apps | **no** | solo si hay backup — ver abajo |

### El riesgo que este runbook NO cubre (y que nadie decidió aún)

`development-pg-n66dz` es **Standard_B1ms Burstable, backup 7 días,
geo-redundancia Disabled, HA Disabled**, y su nombre dice `development` aunque
sea la base de producción. Guarda la memoria longitudinal de Insult y los facts
clínicos de Alex. El compute se rehace en dos horas; **esto no se rehace nunca**.

Un incidente que toque el servidor (borrado accidental, región caída, suspensión
que sí alcance al data plane) pierde todo lo anterior a la ventana de 7 días.
Subir `geoRedundantBackup` exige recrear el servidor; `backupRetentionDays` sube
en caliente hasta 35. **Decisión de Bernard, no del agente** — es gasto recurrente.

## Orden de reconstrucción (por dependencia, no por importancia)

1. **Resource group + `prod-env`** (managed environment, `eastus2`).
   El env define el workspace de Log Analytics; sin él, cero observabilidad.
2. **Postgres** — si sobrevivió, no se toca. Confirmar que responde antes de
   seguir: un runner sin DB arranca y miente.
3. **ACR** — las imágenes suelen sobrevivir. Si no, `git push` a `main` y deja
   que el CD las construya (`az acr build` local está roto en el Mac; ver `~/CLAUDE.md`).
4. **`persona-runner`** — el cerebro. Sin él, ninguna persona contesta.
   Necesita el storage del env `insult-workspace` (→ share `insult-data` de la
   cuenta `insultstorage`, ReadWrite) montado como volumen `workspace` en
   `/data/insult-workspace`, con el `CLAUDE.md` del repo en la raíz del share.
5. **`discord-bot`** — la plomería. Depende del runner (`PERSONA_RUNNER_URL`).
6. **`persona-gateway`** — las personas hermanas. Depende del runner y del `.env`
   completo (un token faltante → esa persona simplemente no arranca).
7. **Jobs** (`insult-canary`, `fact-consolidation`) — no bloquean a nadie.
8. **Alertas + action group** — `docs/runbook_alerts.md`.

## Los secretos: qué puede el agente y qué te necesita a ti

`./scripts/dr_inventory.sh secrets` audita los 12 secretos vivos contra su
backup en `~/.secrets/`, comparando fingerprints SHA-256 (nunca valores). Un
`❌ BACKUP STALE` significa que esa credencial **se perdería con la suscripción**.

- **Recuperables sin Bernard:** `acr-password` (`az acr credential show`),
  `azure-openai-key` (`az cognitiveservices account keys list`).
- **Regenerables por el agente** (pero deben coincidir entre apps):
  `debug-token`, `insult-to-alice-token`, `insult-agent-runner-token`.
- **Requieren a Bernard — login + MFA, y regenerar INVALIDA el vivo:**
  todos los `*-discord-token` (Discord Developer Portal) y el
  `claude-oauth-token` (OAuth Claude Max).

**Gotcha que ningún doc registraba:** el `canary-token` del job `insult-canary`
**es el token de Vultur** — el probe postea como Vultur vía REST, sin abrir un
segundo IDENTIFY. Rotar el token de Vultur rompe el canary en silencio.

**Gotcha 2:** el `DISCORD_TOKEN` de Insult vivía SOLO en el `.env` (gitignored) y
dentro de Azure. Respaldado el 2026-07-08 en
`~/.secrets/discord-bot-insult-discord-token.txt`. El backup del `claude-oauth-token`
en `~/secrets/insult-oauth-token.txt` estaba **stale** — el vivo se respaldó en
`~/.secrets/discord-bot-claude-oauth-token.txt` el mismo día.

## Trampas del incidente real (no las redescubras)

- **Capacidad de región.** Recrear el env en `eastus` FALLÓ (AKS heavy-usage).
  Se recreó en `eastus2` → todos los FQDN cambiaron de `nicecliff-*` a
  `greendune-53f1f4af.eastus2`. El dominio viejo es NXDOMAIN. Hay que barrer
  `cd.yml`, `ARTIFACT_BASE_URL`, `ALICE_INVITE_URL` y las memorias.
- **Un env `Failed` ocupa el slot.** Bórralo antes de recrear con el mismo nombre.
- **Recrear un Container App "de memoria" pierde env vars secundarios en
  silencio, y `/health` verde los tapa.** En 2026-06-25 se perdieron
  `ALICE_INVITE_URL` + `INSULT_TO_ALICE_TOKEN` (failover a ALICE muerto) y
  `ARTIFACT_BASE_URL` (artifacts publicando al FQDN muerto). Ambos con el bot
  "sano". Compara el env contra `dr_inventory.sh`, no contra tu recuerdo.
- **COPY-gap del Dockerfile.** Cada `Dockerfile.*` tiene su allowlist de `COPY`;
  un paquete top-level nuevo que no esté ahí → `ModuleNotFoundError` al boot.
  Lo guarda `tests/arch/test_runner_dockerfile_copies_imports.py` — corre la
  suite antes de culpar a la infra.
- **`fact-consolidation` importa `personas.insult.config.settings`**, que exige
  `discord_token`. El job necesita el secret `discord-token` + su env aunque no
  hable con Discord. Sin él: `Failed` al primer run.
- **`az containerapp job create --command "python" "-m" ...` con flags falla.**
  Usa YAML con `command` como lista.
- **`az acr build` está roto en el Mac** (pyexpat de Homebrew). Deja que el CD
  construya en el runner de GitHub. Detalle y fix en `~/CLAUDE.md`.

## Verificación — el `/health` no prueba nada

La jerarquía de rigor está en `engineering-playbook/rules/verify-before-assuming.md`.
Aplicada aquí, servicio por servicio:

| Servicio | Prueba que NO se puede falsear |
|---|---|
| `persona-runner` | `POST /v1/turn` real devuelve texto en la voz correcta (200 + `end_turn`) |
| `discord-bot` | mandar un mensaje en **#general** y ver a Insult responder con el `VERSION_TAG` esperado |
| `persona-gateway` | dirigirse a una persona (`frugi, …`) en **#general** y ver que contesta **en su propia voz** |
| `insult-canary` | un run `Succeeded` con `canary_probe_sent` → `canary_probe_ok` |
| `fact-consolidation` | un run `Succeeded` (falla ruidosamente si le falta `DISCORD_TOKEN`) |

Un `/health` 200 y un `serving:true` son **proxies que pueden mentir** — es
exactamente la clase de fake-green que costó 14 minutos de bot muerto el
2026-06-13. Nunca cierres un DR sin el round-trip real en `#general`
(nunca en el DM de Insult: el DM es el path que nunca falla).

**El boot honesto ya es código.** Desde v4.22.14 el gateway bindea su puerto
ANTES de Postgres y de los logins de Discord, supervisa cada persona por separado
y su `/health` distingue liveness de `serving`/`personas_ready`/`personas_down`.
Ver `reference_activationfailed_gateway_hang`.

## Estado no cubierto por el compute

- El share AzureFile `insult-data` (cuenta `insultstorage`, expuesto al env como
  storage `insult-workspace`) debe traer el `CLAUDE.md` del repo en la raíz, o el
  runner arranca sin contexto de proyecto.
- `insult-dashboard` (Static Web App, `centralus`) se despliega por su propio
  workflow, path-scoped a `dashboard/**`.
- `susurro-gateway` vive en este mismo RG pero es otro producto (TTS/STT);
  su dominio `sus.bernarduriza.com` no se tocó en el recovery.
