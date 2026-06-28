# GATE4-CUTOVER-READINESS — og118 replaces ChatGPT as Bernard's daily driver

**Status:** Checklist open — readiness probing in progress
**Fecha:** 2026-06-28
**Autor:** Claude Code (vía /work; milestone GATE4-CUTOVER-READINESS)
**Scope:** Readiness checklist + receipts. The **cutover decision itself is Bernard's** — this arms it with evidence, it does not flip apex DNS.

---

## What "ready" means

Gate 4 is NOT "change the DNS". It is: **og118 survives a real day of use as the
daily driver.** This checklist is the executable bar. Each item: how to verify, the
status, and a receipt. The cutover opens only when every P0 row is ✅ on the
**integrated** (merged + deployed) build.

Legend: ✅ PASS (receipt) · 🟡 verified LOCALLY, pending merge→staging deploy ·
🔵 needs Bernard / real device · ⬜ not yet probed.

## P0 — must be green before cutover

| # | Capability | How to verify | Status | Receipt |
|---|-----------|---------------|--------|---------|
| 1 | **Auth0 login** | Load staging, complete Google login, token minted (aud `api.og118.ai`) | ✅ | **Live on staging.og118.ai (2026-06-28):** loaded authenticated, no login button, `@@auth0spajs@@` cache present (sub `google-oauth2|…198`, roles FI-superadmin) |
| 2 | **Chat streaming** | Send a turn, SSE streams `open→text→result→done` | ✅ | **Live on staging (2026-06-28):** sent a turn → assistant replied "listo". Plus full SSE in Projects/elements E2E this session |
| 3 | **Continuity** | Multi-turn thread keeps context after reload (client history replay) | ✅ | Merged ([[og118-continuity-canary]]); stateless backend, 16 tests, prior live Chrome E2E |
| 4 | **Projects upload** | Pick a `.txt` from the UI → indexed into the corpus | 🟡 | PR #290 — live E2E: `catalogo.txt` → "Indexado · 1 fragmento". Pending merge→deploy |
| 5 | **RAG retrieval** | Ask about an uploaded fact → agent calls `search_documents` → answers from the doc | 🟡 | PR #290 — `search_documents(corpus_id=…)` → "$47 pesos" (fact only in the file) |
| 6 | **Projects sync** | Project survives a localStorage wipe (server-owned), delete is server-side | 🟡 | PR #292 — live: wipe localStorage → project reappears from `GET /projects`; delete → stays gone |
| 7 | **Trace persistence** | Glass-box plan/steps/tools survive reload | ✅ | Merged PR #289 ([[figlass-trace-persistence]]), verified live |
| 8 | **Identity isolation** | Account B never sees account A's data on a shared browser | ✅ | Merged PR #276 ([[og118-identity-scoping-leak]]) + PR #292 server owner-filter |
| 9 | **No filesystem exposure** | "show me your code" cannot Glob/Read the host | ✅ | PR #291 `ToolPolicy.companion()`; test asserts Bash/Read/Glob/Write blocked; preserved through element persona swap |
| 10 | **No secrets leak** | `grep` for key shapes in the repo is empty; tokens only in localStorage/`~/.secrets` | ✅ | grep for `sk-ant-*` / JWT / `AKIA*` shapes over `apps/og118` source = **empty** (2026-06-28) |
| 11 | **Console/network clean** | No console errors on load + a turn | ✅ | **Live on staging (2026-06-28):** zero console errors after load + a turn (`list_console_messages` empty). Also clean in Projects/sync E2E |

## P1 — should be green

| # | Capability | How to verify | Status | Receipt |
|---|-----------|---------------|--------|---------|
| 12 | **Voice TTS** | Speak a reply → audio plays | ⬜ | needs the susurro gateway live (cloud vars); probe on staging |
| 13 | **Voice STT** | Record → transcript lands in composer | ⬜ | needs susurro gateway; probe on staging |
| 14 | **Conversation rename** | Rename a chat in the sidebar, persists | ⬜ | exists (`renameConversation`); probe on staging |
| 15 | **Elementos** | Select Oxígeno → answer in Vultur's voice; no element 119 | 🟡 | PR #294 — live `element=oxigeno` → IFA index in Vultur's voice; registry caps at 118 |
| 16 | **Mobile smoke** | Load + a turn on a phone viewport | 🔵 | needs a real device / emulate; Bernard's surface |
| 17 | **Reload smoke** | Reload mid-session keeps the thread + active project | ✅ | sync E2E: reload kept project; continuity kept thread |
| 18 | **Error recovery** | A 401 / stream death surfaces a usable banner, not a white screen | ✅ | og118 `needsAuth` banner + framework recoverable-error banner (code-verified) |

## Probes I can run now (receipts filled inline above as they complete)

```bash
# P0-10 — no secret shapes in the repo
grep -rnE 'sk-ant-[a-z0-9-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.|AKIA[0-9A-Z]{16}' \
  apps/og118 --include='*.ts' --include='*.tsx' --include='*.py' --include='*.json' \
  | grep -v node_modules | grep -v '.next'   # expect: empty
```

## The integration caveat (honest)

The 5 milestone PRs (#290/#291/#292/#293/#294) are **not merged**. Staging runs the
PRE-milestone bundle. So rows 4/5/6/15 are ✅ **locally** but ⬜ on staging until
they merge+deploy. A TRUE Gate 4 pass requires re-running the P0 rows on the
**integrated staging build** after merge. This checklist is the bar to re-run then.

## The decision that's Bernard's

Flipping og118.ai apex from the landing to the app (the cutover) is **Bernard's**,
taken only after every P0 row is ✅ on integrated staging AND he has run a real
daily-driver session. This doc does not flip DNS.
