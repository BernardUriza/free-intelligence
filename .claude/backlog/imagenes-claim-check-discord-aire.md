# Imágenes por referencia: Discord → AIRE, el pipeline sólo carga la URL firmada

**Status:** Done (2026-09-25) — construido en los tres repos (aire-server `5cd1cee`, cerrado allá en `3a5c5ce`; fi-runner 0.22.0 PR #495; este repo v4.41.0, más `job_id` en logs y el aviso de más de 4 fotos en voz de la persona en #100, v4.41.2). Idea de Bernard. Cross-repo: aire-server + fi-runner + este repo.

**Recibo del probe en #general (2026-09-25):** a las 22:35 UTC se mandó `@Vultur` con
`probe-50.png` ("MANGO 5082" en amarillo sobre verde, círculo magenta). A las 22:37
Vultur describió la imagen correctamente y firmó `ᵛ⁴·⁴¹·¹`, con gateway y runner en
`d4bc23b`: la imagen hizo Discord → gateway → runner → AIRE → Claude por referencia.

**Cerrado después (2026-09-25):** el camino base64 de imágenes se borró en #105
(v4.41.4). Los PDFs y archivos de texto viajan por el mismo Claim Check desde v4.42.0:
AIRE `6b59010` (`documents: [{url, title?}]`, tipo detectado), fi-runner 0.23.0
(`TurnDocument`, `documents_attached`, PR #496). Hoyo #4 cerrado. Ya no queda base64 en
el cable del consumer: la fila de `turn_jobs` guarda todas las referencias.

## Lo que entró (2026-09-25)

- **Gateway** (`khimeras_shared/attachments.py`): una imagen ya no se descarga; sale como
  bloque `{"type":"image","source":{"type":"url","url":<firmada>}}`. Se borraron el
  compresor de 2048 px (violaba la regla de 2000 px) y `MAX_IMAGE_B64_CHARS`: el tope de
  bytes de imagen tiene un solo dueño, AIRE. Topes locales: 10 MB por imagen (el de fetch
  de AIRE) y 4 por mensaje — las de más se nombran en personaje, el turno no muere
  (hoyo #3 cerrado).
- **Runner** (`aire_route.images_from_attachments`): la referencia se vuelve
  `TurnImage(url=...)`; `attachments_lost` es terminal (500).
- **fi-runner 0.22.0**: compara `images_attached` contra lo enviado y truena con
  `attachments_lost` si no cuadra.
- **`turn_jobs`**: la fila guarda las referencias (cientos de bytes), así que un job
  reanudado trae la imagen por construcción. Texto/PDF inline siguen `not_resumable`.

**Desviación del plan, a propósito:** el runner NO re-firma con `refresh-urls`. Eso le
habría dado al runner un token de bot de Discord, y una credencial se queda en la
superficie a la que se entregó. Como la firma dura 24 h y una reanudación ocurre en
minutos, al reanudar se revisa el `ex` de la URL: si ya venció, el job es
`not_resumable: image references expired`, en voz alta. Si algún día hace falta
reanudar más de 24 h después, el lugar para re-firmar es el gateway, que ya tiene el token.

## El problema

Hoy la imagen viaja embebida en base64 por cuatro saltos (Discord → gateway →
runner → AIRE → Claude) y ningún salto verifica que lo que sale es lo que llega.
Formas medidas en que se perdieron o se pueden perder (sesión 2026-09-25):

| # | Qué pasa | Estado |
|---|---|---|
| 1 | El job del runner se armaba desde la fila de `turn_jobs`, que no guarda la imagen | 23→25-sep; arreglado en #92 (v4.40.21) |
| 2 | Imágenes de 3.7–5 MB → 422 de AIRE, turno muerto (18 turnos, 8→19-sep) | arreglado 18-sep, pero con `5_000_000` copiado a mano en dos repos |
| 3 | Un mensaje con ≥5 fotos: el gateway no tiene tope, AIRE `MAX_IMAGES=4` → 422 | cerrado v4.41.0 (tope de 4 en el gateway) |
| 4 | PDFs y archivos de texto: el runner los tira en silencio porque AIRE sólo acepta imágenes | cerrado v4.42.0 (documentos por referencia) |
| 5 | Ni gateway ni runner loggean `job_id` → no hay cómo cruzar una pérdida | cerrado v4.41.2 (#100) |

## La decisión: Claim Check con Discord como almacén

No es un bypass: por el pipeline viaja la **referencia** (URL firmada completa,
tamaño, `content_type`), no los bytes. AIRE, el último salto, baja la imagen del
CDN. La fila de `turn_jobs` guarda la referencia, así que un job reanudado o
reconstruido desde la fila trae la imagen **por construcción** — la clase del #92
deja de poder existir en vez de detectarse.

Recibos del 2026-09-25 (desde el droplet, `ssh root@159.203.84.13`):
- `curl` a la URL firmada del probe KIWI → `200`, 17,795 bytes, `image/png`.
- La misma URL sin `ex/is/hm` → `404`: la referencia es la URL completa, no el path.
- `ex - is = 86400`: la firma dura **24 h**. Sobra contra el presupuesto de 600 s
  del turno; NO es almacén durable (una reanudación de >24 h no la encuentra).
- **Las 24 h se cierran re-firmando, no guardando** (verificado 2026-09-25, token
  de Insult): el path sin firma de un adjunto real de #general → `404`; ese mismo
  path por `POST /api/v10/attachments/refresh-urls` (`{"attachment_urls": [...]}`)
  → URL firmada nueva → `200`, 2,677,920 bytes. O sea: **la fila de `turn_jobs`
  guarda el PATH** y el runner lo re-firma justo antes de cada envío, reanudaciones
  incluidas. Un job reanudado días después sigue trayendo la imagen.
- **Re-firmar es trabajo de ESTE repo**, no de AIRE: pide el token del bot y AIRE
  no carga credenciales de sus clientes.
- Después del turno la imagen ya es durable: el transcript de AIRE guarda el bloque
  `image` en base64 (85 entradas en `claude_session_store` al 2026-09-25). Sin OCR
  ni vectores.

## Lo que tiene que llevar (si no, se abren hoyos nuevos)

1. **Allowlist de hosts en AIRE** (`cdn.discordapp.com`, `media.discordapp.net`).
   AIRE es un servicio genérico con otros clientes; bajar URLs arbitrarias es SSRF.
2. **La compresión >3.7 MB se muda a AIRE**, junto a `MAX_IMAGES` y
   `MAX_IMAGE_B64` (`aire/engine/vision.py:15-16`): un solo dueño de los topes, y
   el `5_000_000` duplicado en este repo se borra. La caja tiene 512 MB: procesar
   de una en una, nunca las 4 en paralelo.
3. **AIRE reporta cuántas adjuntó** en el `TurnResult`; el runner compara contra
   las referencias que mandó y si no cuadra el turno truena con `attachments_lost`
   (rojo, nunca contestar a ciegas).
4. **Tope en el gateway**: más de `MAX_IMAGES` → aviso en personaje, no turno muerto.
5. **PDFs por el mismo mecanismo** (AIRE los baja como bloque `document`); texto
   plano sigue como texto en el mensaje.
6. **`job_id` en los logs** de gateway y runner para poder cruzar.
7. **El camino base64 queda vivo** durante el rollout (otros clientes de AIRE y
   rolling updates a medias) y se borra al terminar ([[migrations-end-with-deletion]]).

**Descartado por ahora:** mandar la URL directo a Anthropic (`source: url`). No
verificado que funcione con el Agent SDK + OAuth Max, y se pierde la compresión y
el control del error.

## Orden

1. aire-server: `images` acepta `{url}` además de `{data}` + allowlist + compresión + conteo en `TurnResult` (tests: resistencia a host fuera de allowlist, a URL vencida → error declarado, no turno mudo).
2. Este repo: gateway manda referencias (+ tope), runner persiste el path en la fila, lo re-firma con `refresh-urls` antes de cada envío y verifica el conteo.
3. Probe en #general con imagen (tipo "KIWI 7431") antes de declarar Done.
4. Borrar el camino base64 y el `5_000_000` local.
