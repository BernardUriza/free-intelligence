# Cadenas cortadas por la purga de `personas/` — triage revivir/congelar

Status: Triaged (2026-07-15)
Proposed: 2026-07-14 by la autopsia 10-agentes; decidido 2026-07-15 by Bernard+Claude

La purga de `personas/` (2f8d9ad) mató el `debug_server` y varios scripts de tooling
que eran el DISPARADOR de superficies auxiliares. En cada caso la capa de DATOS
sobrevivió en `khimeras_shared`; lo que murió fue el trigger/HTTP/tooling. Decisión
por superficie, calibrada al blast radius real (bot de ~1 usuario, Art. proportional-rigor).

## 1. html_artifacts — ✅ REVIVIDO (2026-07-15, 3fea06b + e3ddbbf)

El bot minteaba URLs `/a/{id}` a un FQDN muerto (nicecliff NXDOMAIN, greendune
escalado a 0). Ahora el **runner sirve `/a/{id}`** él mismo (`persona_runner/api/
artifacts.py` → `get_artifact` → HTMLResponse), `ARTIFACT_BASE_URL` apunta a su
propio FQDN, y `publish_html_artifact` falla en voz alta si no está configurado en
vez de mintear un cadáver. Cerrado.

## 2. dashboard SWA — ❄️ CONGELADO

`dashboard/` (Brython + HTML estático, su propio Azure Static Web App) leía su feed
del `debug_server` que vivía en `personas/insult` — muerto. La capa de datos (Postgres)
vive; el endpoint que el dashboard consumía, no. Para 1 usuario, un dashboard de ops
no vale re-cablear ahora. **Congelado**: si se revive, su feed debe apuntar a un
endpoint nuevo en el runner o el gateway (no al `debug_server` muerto).

## 3. sync SerenityOps — ❄️ CONGELADO

El repo `khimeras_shared/memory/repositories/serenityops.py` (snapshots + sync tokens)
SOBREVIVIÓ, pero el endpoint HTTP que creaba/resolvía los tokens vivía en el
`debug_server` muerto. Sin superficie para disparar el sync. **Congelado**: revivir =
exponer las operaciones de sync token como rutas del runner. Bajo valor a 1 usuario.

## 4. RAG re-poblado — ❄️ CONGELADO (el corpus está VIVO)

`khimeras_shared/corpus/` (animal_liberation, film_criticism, vegan_gastronomy) + `pg_rag.py`
+ `rag.py` están VIVOS — el corpus se consulta bien. Lo que murió son los `ingest_*`
scripts (re-poblado del `deep_memory_chunks`). El corpus es contenido estático que no
necesita re-poblado frecuente. **Congelado**: los ingest scripts viven en git
(`2f8d9ad^:scripts/ingest_*`); resucitar solo si se agrega corpus nuevo.

## Cómo descongelar

Cada "❄️" es reversible: la capa de datos existe, solo falta re-cablear el disparador
a una ruta viva (runner/gateway). Ninguna es urgente a la escala actual.
