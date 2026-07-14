# Elementos externos ignoran el Project activo (corpus nunca llega al engine remoto)

Status: Done 2026-07-14 — ruta 1 (aviso honesto) shipped y luego SUPERSEDIDA por ruta 2 (RAG server-side, greenlight de Bernard vía /ultra-lord): los elementos externos SÍ ven los documentos del Project
Proposed: 2026-07-14 by Claude (hallazgo colateral de PROJ-AUTOSEARCH-1)

## What it is

Los tres elementos activos de og118 (Oxígeno→vultur, Aluminio→alice, Yodo→insult)
corren en el engine externo (`external_http_engine`), y esa rama de
`/chat/stream` (`app.py`, branch `external`) NO pasa `corpus_id` —
`stream_external_turn` no tiene canal para él y el engine remoto no monta las
rag_store tools de og118. Resultado: con un Project activo y un elemento externo
seleccionado, los documentos del proyecto se ignoran EN SILENCIO — el usuario
cree que la persona ve sus documentos y no es así.

El fix de auto-búsqueda (PROJ-AUTOSEARCH-1, política search-first en
`fi_runner.active_corpus_binding`) solo cubre el runner LOCAL (el chat default);
para elementos externos el problema no es de prompt sino estructural.

## Canonical path to reuse (Art. 6)

Dos rutas honestas, en orden de costo:
1. **Honestidad barata (UI):** si hay Project activo + elemento externo, avisar
   en el stream (mismo patrón que el rechazo de imágenes en la rama external:
   error in-stream LOUD antes de proxear) o deshabilitar el selector de Project.
2. **Capacidad real:** hacer RAG del lado og118 antes del proxy (server busca el
   corpus y antepone los chunks al `user_text` del external turn) — reusa
   `rag.search` que ya existe en el server; no requiere tocar el engine remoto.

## The decision that's the owner's

Cuál de las dos rutas (o ambas: aviso ya, RAG-side después) y su prioridad —
depende de si Bernard quiere que los elementos externos participen de Projects o
queden explícitamente fuera.

## Status / next step

Done. Ruta 1 (rechazo LOUD) vivió unas horas y fue supersedida el mismo día por
ruta 2 con greenlight de Bernard: la rama external de `/chat/stream` hace RAG
server-side (`rag.search(corpus_id, message, top_k=4)`) y antepone los chunks al
`user_text` del proxy — el elemento externo fundamenta su respuesta en los
documentos del Project sin que el engine remoto conozca og118. Corpus sin hits →
texto intacto; fallo de retrieval → error honesto in-stream (nunca responder sin
los documentos que el usuario cree en juego).
