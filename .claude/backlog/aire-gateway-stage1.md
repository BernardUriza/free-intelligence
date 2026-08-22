# AIRE gateway — etapa 1: todo el tráfico Anthropic sale por la puerta relay

Status: **Wired + live** (env verificado contra el Container App 2026-08-22);
falta la verificación del espejo (un turno real de Discord apareciendo en
`aire_gateway_log`) — esa la cierra Bernard en el hilo principal, no este item.
Proposed: 2026-08-12 por Bernard (aire-server backlog #33) · Auditado: 2026-08-22

## Qué es

Todo el tráfico Anthropic de este repo sale por la puerta gateway de AIRE
(`https://gate.bernarduriza.com`, relay byte-por-byte de `/v1/*` hacia
`api.anthropic.com`) en vez de pegarle directo. AIRE espeja cada turno crudo a
Postgres (`aire_gateway_log`, visible en el front de AIRE). El runner viaja con
SU PROPIA credencial (`CLAUDE_CODE_OAUTH_TOKEN`) → pass-through puro: AIRE no
gasta nada, el comportamiento no cambia. Sin `x-aire-key`, sin préstamo de
credencial.

## El mapa de call sites Anthropic (auditado 2026-08-22)

| Superficie | Cómo le pega a Anthropic | ¿Cubierta por `ANTHROPIC_BASE_URL`? |
|---|---|---|
| `persona_runner` `/v1/turn` | CLI spawneado por el Agent SDK (`session_pool` + `fi_runner.ClaudeCodeBackend`) | ✅ sí — el CLI hereda el env del contenedor; fi_runner documenta el proxy vía `ANTHROPIC_BASE_URL` y no lo scrubbea |
| `persona_runner` `/v1/judge` | CLI fresco por juicio (mismo SDK) | ✅ sí — mismo env |
| `khimeras_shared/runner/{agent,judge}_client.py` | HTTP al runner (`PERSONA_RUNNER_URL`), NO a Anthropic | ✅ transitivo |
| `persona-gateway` / `khimeras-host` / `demux_ai` | cero credencial Anthropic (verificado en su env de Azure); el router del host es Azure OpenAI (`insult-openai`) | n/a — fuera del alcance de AIRE |
| `.github/workflows/ai-gatekeep.yml` | claude-code action en el runner de GitHub, directo a `api.anthropic.com` | ❌ NO ruteada — CI, no un deployable; rutearla metería el droplet como SPOF del gatekeeper. Decisión de Bernard si algún día se quiere el espejo ahí |

No existe ningún cliente `anthropic` directo en el código (cero
`import anthropic`); la dep `anthropic>=0.42.0` de `environment.yml` es
transitiva/sin consumidor propio.

## Dónde vive el cableado (env como código)

Este repo no tiene bicep: el CD (`cd.yml`) sólo actualiza imágenes, y los env
vars del Container App se guardan como código en **`docs/runbook_dr.md` § orden
de reconstrucción, paso 4** (persona-runner), que ya carga las dos líneas:

- `ANTHROPIC_BASE_URL=https://gate.bernarduriza.com`
- `ANTHROPIC_CUSTOM_HEADERS=x-aire-project: insult` (el runner se nombra ante
  AIRE; llena la columna app de la vista `/gateway` del front — NO es una llave)

Verificado en vivo 2026-08-22: `az containerapp show -n persona-runner -g
insult-rg` muestra ambos en `template.containers[0].env`.

## Rollback

Quitar los dos env vars y borrar las dos líneas del runbook (mismo commit):

```bash
az containerapp update -n persona-runner -g insult-rg \
  --remove-env-vars ANTHROPIC_BASE_URL ANTHROPIC_CUSTOM_HEADERS
```

El runner vuelve a `api.anthropic.com` directo en la siguiente revisión; nada
más cambia (la credencial siempre fue la propia).

## Siguiente paso

La etapa 2 (migración real a la puerta ENGINE de AIRE) es otro item:
[[aire-engine-stage2]]. Decisión de Bernard.
