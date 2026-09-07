# Dashboard: data plane fósil — nadie escribe los blobs desde el retiro del plumbing

Status: In progress — fake-green ELIMINADO (2026-08-06, `34bf41c`); el fork recablear/congelar sigue siendo de Bernard
Proposed: 2026-07-20 by Claude (hallazgo del refactor v4.28.1 + /cruel-critic)
Updated: 2026-08-06 by Claude (verificación con evidencia + fix del indicador, dashboard v2.4.0)
Re-verificado: 2026-09-07

## Re-chequeo 2026-09-07 (auditoría del backlog)

- El blob sigue fósil: `curl -sI https://insultstorage.blob.core.windows.net/
  insult-bot/metrics.json` → `HTTP/1.1 200 OK`, `Last-Modified: Thu, 25 Jun 2026
  04:59:30 GMT` — el mismo segundo que el 08-06, ya 74 días.
- El fork NO se decidió: `git log --since=2026-08-06 --oneline -- dashboard/`
  no trae ningún commit sobre el data plane ni sobre el workflow SWA.
- **Pero la superficie no está congelada**: en ese mismo rango `dashboard/`
  ganó el portal de nómina de Alex (`dbccf0d` v4.32.48 *"Alex ya puede ver lo
  que va ganando sin preguntarle a nadie"*) y cinco commits `docs(nomina)`
  después. O sea que la ruta 2 (congelar el SWA) ya no es gratis: el SWA hoy
  sirve una página viva junto al fósil. Si Bernard elige congelar, hay que
  separar `dashboard/nomina/` antes.
- El pill sigue siendo el de v2.4.0 (`dashboard/py/freshness.py` sin cambios
  desde `34bf41c`).

## What it is

El dashboard (`dashboard/`, SWA `insult-dashboard` = brave-ground-0c804e410.6)
lee 4 blobs de `insultstorage/insult-bot` (`metrics.json`, `logs.json`,
`traces.json`, `facts.json`) + `alice-bot/metrics.json`. Grep verificado
2026-07-20: **cero uploaders en todo el repo** — los escribía el container
`discord-bot` retirado (scale 0, cutover 2026-07-15). Evidencia en la
superficie desplegada: uptime congelado "3d 5h", traces con la tool
`invoke_alice` (muerta), logs con eventos pre-cutover.

El pill de status decía "connected" en verde porque el blob responde 200 —
liveness del BLOB, no del bot: exactamente la clase proxy-que-miente del
incidente 2026-06-13 (`is_ready:true` con bot muerto).

## Verificación 2026-08-06 (evidencia dura, no inferencia)

| Prueba | Comando | Resultado |
|---|---|---|
| ¿Cuándo se escribieron los blobs? | `curl -D - -o /dev/null https://insultstorage.blob.core.windows.net/insult-bot/{metrics,logs,traces,facts}.json` | Los 4: `Last-Modified: Thu, 25 Jun 2026 04:59:30 GMT` — **42 días** de antigüedad, idénticos al segundo |
| ¿El payload se fecha a sí mismo? | `curl .../metrics.json` | `timestamp: 1782363570.82` = 2026-06-25T04:59:30Z, `uptime_seconds: 280323` = el "3d 5h" congelado |
| ¿Existe el productor? | `az containerapp replica list --name discord-bot -g insult-rg --revision discord-bot--0000072` | `[]` — **cero réplicas** (min=0, imagen legacy `insult-bot:d6fa36c`) |
| ¿Queda algún uploader? | `grep -rn "insultstorage\|upload_blob\|BlobServiceClient\|metrics.json" --include='*.py' --include='*.yml' .` | Solo `dashboard/py/config.py` (el consumidor). **Cero productores.** |
| ¿Y el blob de ALICE? | `curl -D - .../alice-bot/metrics.json` | **HTTP 404** — el blob ya ni existe (alice-bot fue eliminado) |

**Corrección al hallazgo original:** la escritura murió el **2026-06-25**, no en
el cutover del 2026-07-15. El productor llevaba tres semanas muerto antes de que
el retiro se formalizara — el dashboard estuvo verde sobre fósiles ese tiempo
extra sin que nada lo señalara.

**Test del indicador decorativo** ("si la fuente estuviera completamente muerta
ahora mismo, ¿esto se pondría rojo?"): la fuente **está** completamente muerta
ahora mismo y el pill estaba en **verde**. No hacía falta razonarlo — era
observable. El `req.status == 200` de un blob estático no puede fallar mientras
el archivo exista, así que el pill era estructuralmente incapaz de ponerse rojo.
Decorativo, demostrado empíricamente.

## Qué se hizo (dashboard v2.4.0)

El fake-green se mató **sin decidir el fork de Bernard**: el indicador ahora se
deriva del `timestamp` que el propio productor escribe dentro de `metrics.json`,
no del status HTTP. Es data-driven en ambas direcciones — si algún día un
productor vuelve a publicar, el banner se apaga solo y el pill se pone verde con
razón; si nadie publica, grita.

- `dashboard/py/freshness.py` (nuevo) — clasifica la edad del dato:
  `fresh` (≤5 min) · `stale` (≤1 h) · `dead` (>1 h) · `undated` (payload sin
  timestamp) · `unreachable` (no-200).
- `dashboard/py/views/monitor/stats.py` — `report_data()` / `report_unreachable()`
  sustituyen al viejo `update_status("live", "connected")`. El pill muestra la
  **antigüedad real** (`sin productor · 42d 13h`) y el banner explica desde
  cuándo y por qué, apuntando a KQL/Postgres como la observabilidad real.
- Prosa separada por estado a propósito: la nota "no hay productor" sólo sale en
  `dead`. En `stale` dice "el productor viene atrasado" — para no crear una
  mentira nueva en sentido contrario si el gateway se recablea y sólo se retrasa.
- `dashboard/css/styles.css` — pill ámbar/rojo, banner, y `.data-stale` que
  atenúa los números fósiles y apaga el pulso verde del `.logo-dot`.
- `dashboard/py/views/monitor/alice.py` — el 404 del blob de ALICE ya no se
  disfraza de "ALICE no ha reportado todavía"; dice que el blob no existe.

Verificado en el navegador real (Brython servido en localhost, Chrome debug):
pill `status-dead` con `sin productor · 42d 13h`, banner rojo visible, `.bento`
a `opacity 0.55`, `.logo-dot` rojo sin animación. Los 5 estados se ejercitaron
contra el payload live (incluido el caso verde con timestamp fresco, para probar
que el indicador también puede ponerse verde y no quedó clavado en rojo).

## Canonical path to reuse (Art. 6)

Si se recablea: el emisor natural es `persona_gateway` (dueño del turn path);
subir metrics/traces/logs agregados al blob con el mismo shape que el
dashboard ya parsea (los renders son data-driven, no habría que tocar
`dashboard/py/`) **incluyendo el campo `timestamp` de nivel raíz, que es de lo
que ahora depende el semáforo**. Los filtros de logs del HTML
(`llm/preset/flow/...`) tendrían que re-mapearse a los nombres de evento
post-purga (`persona_gateway_*`). Si se congela: regla del mismo día (Art. 6),
freeze del workflow SWA + nota en architecture.md.

## The decision that's the owner's

Fork de Bernard, dos rutas mutuamente excluyentes:
1. **Recablear** — el gateway publica métricas al blob (feature nueva, con
   costo de mantener la superficie viva de verdad), o
2. **Congelar** — el dashboard se archiva como superficie superseded (la
   observabilidad real ya vive en KQL + Postgres + Discord mismo, per
   testing.md).

El fix de hoy **no elige** por él: sólo quita la mentira mientras decide. La
superficie sigue deployada y ahora se auto-denuncia como fósil.

## Lo que NO se arregló (deuda visible, dicha en voz alta)

- **Los contenidos siguen siendo fósiles.** Traces, logs y facts se renderizan
  tal cual (con `invoke_alice` y eventos pre-purga). El banner los enmarca y el
  atenuado los desmarca de "vivos", pero nadie los borró.
- **El selector de filtros de logs** (`llm`, `preset`, `flow`, `whisper`) apunta
  a nombres de evento que ya no existen post-purga (`persona_gateway_*`).
  Re-mapearlo sólo tiene sentido en la ruta 1.
- **Los umbrales (5 min / 1 h) son una suposición** sobre la cadencia del
  productor muerto: `metrics.json` se escribía junto al `health_check`. Si se
  recablea con otra cadencia, ajustar `FRESH_MAX_AGE_SECONDS` /
  `STALE_MAX_AGE_SECONDS` en `dashboard/py/config.py`.
- **La antigüedad se calcula con el reloj del cliente** contra el timestamp del
  productor. Un reloj desfasado en la máquina que abre el dashboard desfasa la
  lectura. Aceptable para una superficie de ops; no lo es para una alerta.
- **Esto no es un monitor.** Sólo dice la verdad a quien abre la página. Nadie
  se entera de que el dato murió si nadie mira — el `#canary` retirado sigue
  siendo el hueco real de production-trust (ver architecture.md).

## Status / next step

Fake-green cerrado. Next: GO de Bernard por la ruta 1 (recablear el emisor en
`persona_gateway`) o la 2 (congelar la superficie y el workflow SWA).
