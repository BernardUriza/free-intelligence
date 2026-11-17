# 55 — A project keeps its research in AIRE, versioned, and two MCP servers reach it

Status: **In progress** — built and tested on a dev box 2026-11-16, PR open, NOT deployed
Proposed: 2026-11-16 by Bernard (*"explora muy bien Free Intelligence … si necesitas mejorar el MCP, hazlo.
Sobre todo el de persona … que también haya otro para manejar archivos, proyectos y también chats, que
puedan leer esos proyectos"*)

## What it is

videopipe is going public, and its research (`corpus/casos/<tema>/sources-<id>.md`, `corpus/backlog.md`,
`corpus/lore.md`, `editorial/`) must leave git. AIRE already had a corpus (#46, #47) — Postgres full-text,
owner-scoped, written through a door and searched by a tool — but four things were missing for a project
to KEEP its files there, and for an agent outside a turn to use them:

1. **The exact text back.** `aire_corpus_chunk` is an index: chunking drops the blank lines it splits on,
   and `ingest` deletes the old chunks. Nothing could hand a document back as stored, or say what it said
   before the last edit.
2. **A project's chats as conversations.** `recall` searches the transcript for words, from inside a
   turn. Nothing listed a project's sessions or read one back as turns.
3. **Codex could not search a corpus.** Since #54 a Codex turn mounts `memory` over stdio; `rag_store`
   was refused (`CODEX-TOOL-UNSUPPORTED`), so Astra could not read videopipe's expedientes.
4. **No MCP for Claude Code.** server-bot's `persona_mcp` reaches the persona-runner's Discord personas
   (Frugívoro, Insult), not AIRE's casitas; the videopipe coagent called the door with raw HTTP.

## What shipped (dev box, 476 tests green; baseline 451)

- `aire/corpus_versions.py` — `aire_corpus_version`, append-only: every write is a row with its sha256 and
  exact body, an unchanged text appends nothing, a delete is a tombstone row. `corpus.ingest` writes it
  first (one write path for door and tool); `corpus.put` reports `{chunks, version, sha256, changed}`.
- `aire/document_door.py` — `GET /projects/{p}/corpus` (corpora), `GET …/corpus/{c}/text/{doc_id:path}`
  (`?version=`), `GET …/corpus/{c}/history/{doc_id:path}`. The delete route takes slashed doc ids too.
- `aire/transcripts.py` + `aire/chat_door.py` — `GET /projects`, `GET /projects/{p}/sessions`,
  `GET /projects/{p}/sessions/{s}/transcript`: both tables (`claude_session_store`, `aire_agent_log`),
  spoken text only, by name or UUID.
- `intake.owners_only` — every new read refuses an invited key (403). Constant tokens only.
- `agent_sdk/codex_mcp.py` — `CODEX_TOOLS = {memory, rag_store}`.
- `apps/aire-server/mcp/` (client side, never rides to the droplet): `projects_mcp.py` (11 tools),
  `persona_mcp.py` (4 tools), `sync.py` (push/pull a tree), stdlib only.
- Tests: `test_corpus_versions.py`, `test_document_door.py`, `test_chat_door.py`, `test_codex_corpus.py`,
  `test_mcp_clients.py` (the MCP tools through the real app, local Postgres and a fake-model Codex turn
  that searches its expediente, resumes, and is read back as a chat).

## The rule this widens — Bernard ratifies or vetoes

[[write-only-daemon]]: the new reads pass the test that rule states ("does the caller own the rows?" and
"does the result feed an agent?"): a constant token reads its own project's documents and chats as JSON,
for the agent working on it. The transcript read is the closest to the front's job; if Bernard vetoes it
in the daemon, `chat_door.py` moves to the front behind `aire_reader` and the MCP points there.

## Deploying (one decision, Bernard's)

Merge → `aire-server-deploy-server.yml` ships to the droplet; `corpus_versions.ensure()` creates the table
at startup as role `aire`. No env var changes. Then, from the Mac: register the two servers in videopipe's
`.mcp.json`, `sync.py push` the trees, and one real Astra turn with `tools: ["rag_store"]`.

## Open

- Binary receipts (PNG/PDF) have no durable home in AIRE: the corpus holds text, artifacts live on the
  mortal droplet disk.
- Structured rows (Verified/Fragile/Never lines, insert spans, backlog status) stay markdown; parsers on
  the reader side, no typed table yet.
- A real erasure (a private name that must vanish) needs a purge verb; today a delete keeps history.
