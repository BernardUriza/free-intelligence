# Embeddings sin deployment: la memoria profunda y el corpus no recuperan nada

Status: Dropped (decisión de Bernard, 2026-11-04: se queda apagada)
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
- `scripts/ingest_corpus.py`: el camino de escritura. Lectura y escritura se mueven juntas
  ([[both-ends-of-the-data-path]]).

## The decision that's the owner's

- **MiniLM local:** USD 0 y sin Azure. Cambia `deep_memory_chunks` de `vector(1536)` a
  `vector(384)`, re-embebe desde `chunk_text` y obliga a recalibrar los pisos de similitud
  (hoy 0.78 en el corpus, medidos con ada-002). Calidad en español sin medir.
- **Deployment en `aire-openai`:** conserva los vectores si el modelo es ada-002, cuesta por
  uso, y Azure bloquea deployments nuevos con `715-123420` (ticket 2610260040002112).

## Status / next step

Bernard eligió dejarla apagada el 2026-11-04. Nada se migra ni se crea. `deep_memory_embed_failed` sigue saliendo en los logs: es este estado conocido, no un incidente nuevo. El defecto de `deep_memory_corpus_no_hits` queda sin corregir mientras esto siga apagado.
