# runner-base aún embarca Node + Claude CLI + la credencial OAuth que el runner ya no usa

Status: Done — 2026-08-28, v4.35.2 (`c972579`), mismo día que se propuso
Proposed: 2026-08-28 by Claude (hallazgo del borrado de la etapa 2, v4.35.0)

## Cómo se cerró (recibos)

La investigación previa al corte: el mapa del rotador (verificado 2026-08-03)
tenía a persona-runner como consumidor #1; host y gateway montan khimeras-base,
no runner-base; y `grep` de los cinco env vars muertos sobre persona_runner/ +
shared/ + khimeras_shared/ dio **0 lectores**. Con eso:

- `entrypoint.sh` ya no materializa `credentials.json`; `runner-base.Dockerfile`
  BORRADO (sin Node/CLI/Playwright era byte-idéntica a khimeras-base — Art. 6) y
  el job "Build khimeras-runner-base" salió de cd.yml
- De la Container App salieron `CLAUDE_CODE_OAUTH_TOKEN`,
  `CLAUDE_CODE_STREAM_CLOSE_TIMEOUT`, `ANTHROPIC_BASE_URL`,
  `ANTHROPIC_CUSTOM_HEADERS` y `TURN_BACKEND`, y la secret `claude-oauth-token`
  se removió de insult-rg (revisión 195)
- El rotador y la regla del playbook (`claude-max-oauth-single-token.md`) ya no
  listan a persona-runner; la sonda final del rotador (/v1/turn) sigue válida —
  ejercita el mismo token vía AIRE, a un salto
- Recibo vivo: Insult contestó en #general a las 11:42 AM corriendo la revisión
  195 con footer ᵛ⁴·³⁵·² — "sin Node, sin CLI, sin la OAuth de flota adentro"

## Qué es

Con el borrado de la etapa 2 (`fc0944a`), `persona-runner` ya no hosteda el
Claude Agent SDK: cero subprocesos Node, cero lecturas de
`/home/runner/.claude/.credentials.json`. Pero `runner-base.Dockerfile` sigue
instalando `nodejs>=22` + `@anthropic-ai/claude-code`, y
`infra/azure/entrypoint.sh` sigue aprovisionando la credencial OAuth Max al
arranque. Peso muerto en la imagen y una credencial de flota montada en un
contenedor que ya no la consume — superficie de exposición gratis.

## La decisión que es del dueño

La credencial OAuth de la flota tiene un ROTADOR con consumidores registrados
(ver og118-oauth-secret y claude-max-oauth-single-token en el playbook).
Quitarla del runner toca ese mapa: ANTES de borrar, verificar qué consumidores
lista el rotador y que ninguno dependa de que persona-runner la monte. Es un
cambio de infra + secretos, no un `git rm` — decisión de Bernard.

## Camino canónico (Art. 6)

El mismo patrón del borrado de etapa 2: capas fuera de runner-base.Dockerfile
(el hash dispara el rebuild solo), entrypoint.sh sin el paso de credenciales,
y el criterio de terminado es el grep + un boot verificado en vivo.
