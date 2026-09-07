# AIRE gateway — etapa 1: todo el tráfico Anthropic sale por la puerta relay

Status: **Superseded por la etapa 2** (2026-08-28) — el relay `ANTHROPIC_BASE_URL`
ya no existe en el runner; la única ruta Anthropic es la puerta engine
([[aire-engine-stage2]], retirada como Done). Queda UNA acción: limpiar
`docs/runbook_dr.md` paso 4, que sigue listando los dos env vars muertos.
Proposed: 2026-08-12 por Bernard (aire-server backlog #33) · Auditado: 2026-08-22 ·
Re-verificado: 2026-09-07

## Re-chequeo 2026-09-07 (auditoría del backlog)

El mecanismo de esta etapa era *"el CLI spawneado por el Agent SDK hereda
`ANTHROPIC_BASE_URL`"*. Ese CLI murió con el borrado de la etapa 2 (`fc0944a`,
v4.35.0) y los env vars salieron de la Container App con el cierre de
[[runner-base-node-cli-muertos]] (`c972579`, v4.35.2, revisión 195):

- `az containerapp show -n persona-runner -g insult-rg --query
  "properties.template.containers[0].env[].name"` → `POSTGRES_URL
  PERSONA_RUNNER_TOKEN ARTIFACT_BASE_URL AIRE_GATE_URL AIRE_AUTH_TOKEN
  RUNNER_MCP_TOKEN RUNNER_MCP_BASE`. **Ni `ANTHROPIC_BASE_URL` ni
  `ANTHROPIC_CUSTOM_HEADERS`.** `AIRE_GATE_URL=https://gate.bernarduriza.com`.
- `grep -rn "ANTHROPIC_BASE_URL\|ANTHROPIC_CUSTOM_HEADERS" --include='*.py'
  --include='*.md' --include='*.yml' .` (fuera de este folder) → sólo
  `docs/runbook_dr.md:60` y `:62`. **El runbook está rancio**: describe un
  cableado que la revisión 195 quitó. Fuera del alcance de esta auditoría
  (sólo `.claude/backlog/`); pendiente para el hilo principal.
- El "espejo pendiente" (un turno en `aire_gateway_log`) nunca se verificó y
  hoy es moot: con la puerta engine el turno entero vive en AIRE (casita +
  topic), no como relay byte-por-byte.
- La fila del mapa de call sites sobre el host también envejeció a medias:
  `2150ca0` (v4.36.0, 2026-08-29) migró `demux_ai/host_llm.py::HostRouterLLM` a
  `AIREBackend`, pero el host VIVO sigue arrancando `DirectAzureLLMRouter`
  (Azure OpenAI directo, `demux_ai/__main__.py:25`; el env de `khimeras-host`
  no lleva `AIRE_GATE_URL`). Sigue siendo cierto que el host no tiene
  credencial Anthropic.

Este archivo se conserva por el mapa de call sites y el rollback documentado,
que siguen siendo la referencia de por dónde sale el tráfico Anthropic del repo.

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
