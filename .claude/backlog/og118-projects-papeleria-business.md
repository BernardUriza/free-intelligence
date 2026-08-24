# og118 Projects — papelería business space

Status: **Done** en lo técnico (verificado 2026-08-23) — upload + corpus por turno + active_corpus_binding. La vertiente papelería quedó DROPPED: servir a terceros con el OAuth personal rompe el ToS
Proposed: 2026-06-19 by Bernard

## What it is

A small "Projects" section in og118 where a user can upload their own files and
open chats grounded on them. Driven by the real-world canary deployment: og118
staging is going live in Bernard's mom's papelería (see the
[[og118-papeleria-canary]] memory). Two distinct uses surfaced:

1. **Kids' homework (already greenlit, open account)** — ~2-3 investigaciones
   diarias, new chat per new topic. No files needed; pure chat. This is the
   canary traffic.
2. **Mom's business (this backlog item)** — back-to-school season: school
   supply lists (listas escolares) + price assignment (pricing). She wants to
   upload her own files (supplier lists, catálogos, prior price sheets) and ask
   questions about her negocio.

## Canonical path to reuse (Art. 6) — VERIFIED 2026-06-19 against real code

This is ~70% already-built framework, ~30% og118-consumer wiring. Do NOT
rebuild the chunker/embedder/store — they exist and are stable.

**fi-core (COMPLETE, reuse as-is):** `apps/packages/fi-core/fi_core/rag/`
- `store_service.py` → `RagStore`, multi-tenant by `corpus_id`
- `store_mcp_server.py` → MCP with 6 tools: `ingest_document`, `search_documents`,
  `list_documents`, `delete_document`, `delete_corpus`, `stats`
- `chunking.py` → token-aware (gotcha: `min_chunk_size=100` TOKENS → short text = 0 chunks)
- Backends pluggable by env: `FI_RAG_BACKEND` (hdf5|pgvector), `FI_RAG_EMBEDDER`
  (hashing|azure|sentence_transformers), `FI_RAG_STORE_PATH`.

**fi-runner (COMPLETE, reuse as-is):** `apps/packages/fi-runner/fi_runner/`
- `rag_store.py` → `RagStoreClient` (consumer boundary, NO fi-core import)
- `capabilities.py:106` → `rag_store()` capability already registered. Wiring og118
  = add `"rag_store"` to `Runner(capabilities=[...])` in `og118/server/runner.py`.

**fi-glass (PARTIAL, reuse + extend):** `apps/packages/fi-glass/src/shell/`
- EXISTS: `ChatFilePreview.tsx`, upload props on `ChatWidget` (`uploadFile`,
  `uploadStatus`, `onAttach`, `onCancelUpload`), `UploadStatus` type
  (selecting→uploading→processing→indexed→error). og118 is the FIRST consumer to
  exercise these speculative primitives → canary value = proving they work.
- MISSING (og118 builds, with extraction gate): `useChatUpload` state hook +
  file-picker UI. The picker is consumer-specific (each shell's UX); the lifecycle
  hook is a candidate to graduate to fi-glass per [[framework-first-canary]].

**og118 consumer (build):** `apps/og118/`
- `server/app.py` → add `POST /projects/{id}/upload` → parse text →
  `RagStoreClient.ingest(corpus_id=project_id, ...)`
- `server/runner.py` → add `"rag_store"` capability (the TRACER, ~2 lines)
- `web/` → useChatUpload + picker + Projects sidebar section + corpus_id wiring in
  `useOg118Agent`.

## Framework gap this canary surfaced (push UPSTREAM, don't patch in og118)

`corpus_id` is a TOOL ARGUMENT, so the agent must know which corpus to search per
turn. But `Runner` takes a static `persona` and og118's transport sends only
`{message, session_id}` — there is NO clean "active corpus per turn" binding.
This is the canary-driven framework increment: add a per-turn corpus binding as a
new configurable level in fi-runner ([[framework-first-canary]]). The wrong fix is
stuffing `corpus_id` into the message text in og118.

## The decision that's the owner's

**Account / privacy separation.** The kids' homework runs on an OPEN shared
account in a public store — anyone can read anyone's chats. If mom's business
files land on that SAME open account, kids (or anyone) could read her supplier
prices and business data. The Projects section for the business almost certainly
needs a SEPARATE space/account from the open kids' account. Bernard decides the
isolation model (separate account, auth-gated project space, or accept the leak).

## Status / next step

Not built yet. Kids' open-account chat canary ships first (no code needed beyond
the deployment). Projects/upload feature unblocks once Bernard greenlights it and
decides the account-separation model above.

Related: [[og118-papeleria-canary]], [[framework-first-canary]], the
`fi-core-rag-status` and `fi-glass-framework` memories.
