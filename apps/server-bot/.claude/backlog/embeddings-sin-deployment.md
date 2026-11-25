# Embeddings sin deployment: la memoria profunda y el corpus no recuperan nada

Status: Done (2026-11-20, PR #686, v4.52.1). Bernard la reabrió el 2026-11-19 al pedir el recetario de Love Veg «ya embebido» en el corpus de Frugívoro.

## Cómo se cerró

- Embeddings locales `intfloat/multilingual-e5-small` (384d) en el proceso, sin Azure. El 715-123420 seguía vivo el 2026-11-20 al reintentar el deployment en `aire-openai`.
- Migración idempotente: los vectores ada quedan en `embedding_ada002`; 6,889 filas re-embebidas con `scripts/reembed_deep_memory.py` (el `__chatgpt_archive__`, sin lector, se saltó).
- Cierre (2026-11-25, v4.62.6, aprobado por Bernard): `embedding_ada002` ya no existe, las 7,866 filas `__corpus_*` viejas se borraron (el corpus vive en `corpus_chunks`) y las 30,746 de `__chatgpt_archive__` pasaron a la tabla `chatgpt_archive_chunks`, sin vectores ni lector. La base bajó de 517 a 167 MB. Respaldos cifrados y restaurados: `~/Documents/backups/server-bot-corpus-2026-11-24.tar.gz.gpg` y `server-bot-chatgpt-archive-2026-11-25.tar.gz.gpg`. El script de re-embebido y `adopt` se borraron.
- Búsqueda exacta, sin índice aproximado: HNSW dejó vacías 12 de 21 búsquedas filtradas por persona, y un ivfflat viejo que revivió en el deploy, 3 de 21 (v4.52.2).
- Gate de relevancia con cross-encoder (`mmarco-mMiniLMv2`, piso −2.0): el coseno de e5 no separa lo relevante de lo ajeno.
- Recibo en prod: `turn_pipeline_warm_ready corpus=true` (revisión 0018) y `deep_memory_corpus_refs_built` en `__corpus_vegan__` a las 14:10 UTC del 2026-11-20, el primero desde octubre.
Proposed: 2026-11-04 by Claude, buscando bugs por orden de Bernard

## What it is

`persona_core/corpus/pg_rag.py` pide `text-embedding-ada-002` a `AZURE_OPENAI_ENDPOINT`.
El runner apunta a `northcentralus.api.cognitive.microsoft.com` y la llave responde
401 *Access denied*, también con `tts` como control, así que la llave o el endpoint están
muertos para todo.

Medido el 2026-11-04:

- KQL: 15 `deep_memory_embed_failed` y 15 `deep_memory_corpus_no_hits` en los últimos 60 días,
  del 20-oct al 4-nov, sólo en `persona-runner`. Ni un `deep_memory_prefetched`.
- Las cuentas de la suscripción sólo tienen `gpt-5.4-mini` (`aire-openai`) y `tts` + `whisper`
  (`susurro-openai`). Ningún deployment de embeddings.
- Desde v4.49.9 el log trae el traceback: `openai.AuthenticationError: Error code: 401`.

Consecuencia: `build_user_memory_block` y `build_references_block` no devuelven nada, y el
turno sigue como si no hubiera memoria que encontrar. Los dos dependen de la misma llamada.

Sin probar: que el origen sea el borrado de `insult-openai` del 16-oct (el primer evento es
del 20-oct y no sabemos cuánto retiene el workspace), y cuántos chunks hay en
`deep_memory_chunks`. El clasificador de permisos negó esa lectura de producción.

Defecto aparte, abierto: `deep_memory_corpus_no_hits` también se loguea cuando el embedding
falló, y ahí no hubo búsqueda. Se corrige junto con esto.

## Canonical path to reuse

- `persona_core/vectors.py` y `persona_core/memory/minilm_embedder.py`: MiniLM local de 384
  dimensiones, ya cargado en el runner para los facts. Sin red y sin costo por llamada.
- `scripts/corpus_sync.py` (sustituyó a `ingest_corpus.py` en v4.62.0): el camino de escritura. Lectura y escritura se mueven juntas
  ([[both-ends-of-the-data-path]]).

## The decision that's the owner's

- **MiniLM local:** USD 0 y sin Azure. Cambia `deep_memory_chunks` de `vector(1536)` a
  `vector(384)`, re-embebe desde `chunk_text` y obliga a recalibrar los pisos de similitud
  (hoy 0.78 en el corpus, medidos con ada-002). Calidad en español sin medir.
- **Deployment en `aire-openai`:** conserva los vectores si el modelo es ada-002, cuesta por
  uso, y Azure bloquea deployments nuevos con `715-123420` (ticket 2610260040002112).

## Status / next step

Bernard eligió dejarla apagada el 2026-11-04. Nada se migra ni se crea. `deep_memory_embed_failed` sigue saliendo en los logs: es este estado conocido, no un incidente nuevo. El defecto de `deep_memory_corpus_no_hits` queda sin corregir mientras esto siga apagado.
