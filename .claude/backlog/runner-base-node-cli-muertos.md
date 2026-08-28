# runner-base aún embarca Node + Claude CLI + la credencial OAuth que el runner ya no usa

Status: Proposed
Proposed: 2026-08-28 by Claude (hallazgo del borrado de la etapa 2, v4.35.0)

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
