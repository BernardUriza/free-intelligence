# Dashboard: data plane fósil — nadie escribe los blobs desde el retiro del plumbing

Status: Proposed
Proposed: 2026-07-20 by Claude (hallazgo del refactor v4.28.1 + /cruel-critic)

## What it is

El dashboard (`dashboard/`, SWA `insult-dashboard` = brave-ground-0c804e410.6)
lee 4 blobs de `insultstorage/insult-bot` (`metrics.json`, `logs.json`,
`traces.json`, `facts.json`) + `alice-bot/metrics.json`. Grep verificado
2026-07-20: **cero uploaders en todo el repo** — los escribía el container
`discord-bot` retirado (scale 0, cutover 2026-07-15). Evidencia en la
superficie desplegada: uptime congelado "3d 5h", traces con la tool
`invoke_alice` (muerta), logs con eventos pre-cutover.

El pill de status dice "connected" en verde porque el blob responde 200 —
liveness del BLOB, no del bot: exactamente la clase proxy-que-miente del
incidente 2026-06-13 (`is_ready:true` con bot muerto). Hoy es un dashboard
verde sobre datos muertos.

## Canonical path to reuse (Art. 6)

Si se recablea: el emisor natural es `persona_gateway` (dueño del turn path);
subir metrics/traces/logs agregados al blob con el mismo shape que el
dashboard ya parsea (los renders son data-driven, no habría que tocar
`dashboard/py/`). Los filtros de logs del HTML (`llm/preset/flow/...`)
tendrían que re-mapearse a los nombres de evento post-purga
(`persona_gateway_*`). Si se congela: regla del mismo día (Art. 6), freeze
del workflow SWA + nota en architecture.md.

## The decision that's the owner's

Fork de Bernard, dos rutas mutuamente excluyentes:
1. **Recablear** — el gateway publica métricas al blob (feature nueva, con
   costo de mantener la superficie viva de verdad), o
2. **Congelar** — el dashboard se archiva como superficie superseded (la
   observabilidad real ya vive en KQL + Postgres + Discord mismo, per
   testing.md).

Mientras no se decida, el dashboard queda deployado y modular (v2.3.0,
refactor 0fc5b86) pero mostrando fósiles con pill verde.

## Status / next step

No decidido. Next: GO de Bernard por la ruta 1 o 2.
