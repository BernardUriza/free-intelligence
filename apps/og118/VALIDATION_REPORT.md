# fi-glass validation report — from og118 (a fresh app, not aurity)

**Purpose.** og118 is the first app built ON fi-glass *from scratch* — not the
source it was extracted from (aurity/insult_ai). It exists to prove the
contracts (`ChatHook`, the lean primitives, later `AgentHook`) are implementable
cleanly by a NEW consumer. Where a contract feels forced, that is a fi-glass
design defect — recorded here, **not patched in og118**.

Status: **v0 "hello chat" — PASSED.** "hola" round-trips end-to-end in the
browser (og118 → `useOg118Chat`/ChatHook → SSE → fi-runner → Claude OAuth →
fi-glass `Composer` + `messages` primitives render the reply). Local-only.

---

## What validated CLEAN ✅
- **`fi-glass/theme.css`** — imported from a fresh Next app via the package
  `exports` subpath; glassmorphism tokens (`--glass-blur`, `--glass-border`)
  applied with zero friction. First proof of "1 build → N consumers" outside aurity.
- **`fi-glass/composer` `Composer`** — genuinely lean: `message`/`onMessageChange`/
  `onSend` + className props. No baggage, no implicit deps. Model primitive.
- **core `ChatHook`** — minimal required surface (`messages`, `loading`,
  `isTyping`, `sendMessage`); everything else optional. The from-scratch impl is
  ~80 lines. The contract is honest.
- **SSE → ChatHook mapping** — fi-runner's `run_stream` events map nearly 1:1
  onto the text path; the implementation is small and obvious.

## Defects / frictions (scheduled fixes — do NOT block v0)

### #1 (HARD) — `ChatWidgetProps` requires ~12 props for features a consumer may not have
`fi-glass/shell` `<ChatWidget>` makes **required** (no `?`): `voiceState`/
`onVoiceStart`/`onVoiceStop`, `uploadFile`/`uploadStatus`/`isUploadActive`/
`onAttach`/`onCancelUpload`, `responseMode`/`selectedPersona`/`personaName`/
`onResponseModeToggle`/`onPersonaChange`. **Real use-case that exposes it:** og118
v0 is a hello-chat with NO voice, NO personas, NO upload — yet to render the
widget it would have to stub all of them. This **contradicts `ChatHook`**, which
already makes those capabilities optional. The extraction from aurity (which HAS
those features) fossilized the contract to aurity's shape.
**Fix (scheduled):** make voice/persona/upload/responseMode props optional in
`ChatWidgetProps` + guard their use in `ChatContent`; rebuild dist.
**v0 workaround (not a patch):** og118 composes the lean primitives
(`composer` + `messages`) directly — the honest minimal path.

### #2 (SECONDARY) — no full-page `<ChatSurface>`; ChatWidget is a floating widget
`<ChatWidget>` renders a `FloatingButton` when closed and carries view-modes
(minimize/maximize/dense). **Real use-case:** og118 is **chat-first at `/`** (the
chat IS the page), not a bubble in a corner. It is embeddable (`embedded` +
`initialOpen`) but remains widget-shaped.
**Fix (scheduled):** add a `<ChatSurface>` full-page composition to `fi-glass/shell`
for chat-first apps (the primitives already support it; it just isn't packaged).

### #3 (MEDIUM) — `fi-glass/messages` has an implicit Tailwind dependency
`messageStyles`/`markdownStyles` emit **Tailwind utility classes**
(`py-3 px-4`, `bg-white/[0.02]`, `text-slate-300`, …) baked into the dist. A
consumer must (a) have Tailwind, and (b) configure its `content` to scan
fi-glass's **dist** (Tailwind ignores `node_modules`, so the workspace path must
be globbed explicitly). **Real use-case:** og118 started with zero Tailwind; the
message primitives rendered unstyled until Tailwind was added with
`content: ['../../packages/fi-glass/dist/**/*.{js,mjs}']`. The "material-agnostic"
claim has an undocumented Tailwind coupling.
**Fix (scheduled):** either ship a compiled CSS for the message primitives, or
document the Tailwind requirement + the dist content-glob in fi-glass's README.

### SSE mapping notes (not defects — doc/UX observations)
- fi-runner `text` event uses key `text`; core `AgentStreamEvent` uses `delta`. Trivial rename.
- fi-runner re-sends the full text in `result` (already sent via `text`) → the
  hook must finalize from `result` WITHOUT re-appending or it double-renders.
  The core contract doesn't flag this; worth a doc note.
- With `ClaudeCodeBackend`, the reply arrived as a SINGLE `text` event (not
  incremental). Backend streaming granularity, not a fi-glass issue — but the
  "streaming" UX is one-shot until/unless the backend chunks.

## Step 4 — AgentHook + dedup-by-id re-validation ✅ (PASSED, browser-verified)

og118 implements `useOg118Agent` (AgentHook): maps fi-runner's native SSE →
`AgentStreamEvent` → `applyAgentEvent` (Berkelio's pure reducer) → `AgentTurnState`
→ `fi-glass/agent` `<AgentPanel>` (PlanChecklist + StepsPanel + Sources). A real
agentic turn (task_tracker MCP) flows plan → steps → tool_call → text live in the
browser.

**Dedup-by-id — re-validated with the REAL fi-runner mix** (parsed from a live turn):
- 9 `tool_call` events; **all 9 carry a stable id** (`toolu_…`); **0 with `id==null`**;
  **0 duplicate ids**; 0 dropped. Each unique id appends once; `step_index` 0/1/2
  map 1:1 (no off-by-one). `step_done` summaries flowed and rendered.
- **The `id:null` collision path did NOT trigger** — `ClaudeCodeBackend` always
  pairs a `tool_use_id`, so it never emits a null-id tool_call. Same outcome as
  Berkelio's Test B. The null-id branch (reducer appends, never collides) remains
  validated by **code inspection only**, not a live null stream — this backend
  cannot produce one. (A Codex/other backend that emits pending null-id calls
  would be the real null-path test.)

### Step-4 contract findings (scheduled — do NOT patch in og118)
- **#4 — `AgentStreamEvent` is narrower than fi-runner's actual stream.** fi-runner
  emits `step_noted`, `plan_amended` (insert_step/replan), `plan_cancelled`,
  `plan_completed`, `plan_failed`; core's union has no variants for these → the
  og118 hook **drops them** (lossy). **Use-case:** an agent that re-plans
  mid-turn (replan) or annotates a step (note_step) loses that signal in the UI.
  Fix: extend the union (or document the supported subset).
- **#5 — `step_done` status mismatch.** fi-runner emits `done | failed | cancelled`;
  core's `step_done.status` is only `done | failed`. og118 folds `cancelled →
  failed` (lossy). Fix: add `'cancelled'` to core's `StepStatus`/`step_done`.
- **Rename surface (trivial):** fi-runner wraps plan/step payloads under `data:{…}`
  and uses `tool`/`text`/`step_index`; core uses flat `steps`/`call`/`delta`/`index`.
  The hook remaps in ~10 lines — no friction, but worth a doc note in core.

### Clean from scratch ✅
`AgentHook` (data+actions, no UI), `applyAgentEvent` (pure, immutable), and the
`AgentPanel` (turn-as-prop, sub-panels self-hide) all consumed cleanly from a
fresh app. The reducer's catch-up/bounds guards held against the real stream.

---

## Canary — fi-glass v1.1.0 + @free-intelligence/core v1.1.0 (loop closure)

og118 reported defects #1–#5 as a fresh consumer; the packages were bumped to
v1.1.0 to fix them; og118 then re-validated against the new dist. This is the
loop: **the fresh app reported the debt → the substrate fixed it → the fresh app
proves the fix.** Browser e2e, local servers, real fi-runner agentic turns.
Screenshots in `.canary-screens/`.

### RESOLVED ✅ (verified live in the browser)

- **#4 (AgentStreamEvent too narrow) — FIXED + RENDERED.** core v1.1.0 models
  `step_noted` / `plan_amended` / `plan_cancelled` / `plan_completed` /
  `plan_failed`; `useOg118Agent.mapEvent` now maps them (it previously dropped
  them with `default: return null` — updating it WAS the real adoption, not just
  the version bump). A real lifecycle turn (note_step → cancel_step → insert_step
  → finalize_plan) rendered live: `note:` annotations, a struck **cancelled**
  step with its reason, a **REVISED** (amended) header badge, and a **COMPLETED**
  (outcome) header badge. None of it dropped. (`06-lifecycle-full.png`)
- **#5 (step_done lacks cancelled) — FIXED + RENDERED.** The cancelled step shows
  struck + a CANCELLED badge + its reason, distinct from failed (red) and pending
  (hollow). No longer folded to failed, no longer empty. Zero console errors.
- **#1 (ChatWidget over-required props) — FIXED.** A `/chat` ChatHook hello-chat
  mounted `<ChatSurface>` with ONLY `chatHook` + `message`/`onMessageChange`/
  `onSend`. The toolbar rendered with ONLY the send button — voice/upload/persona/
  response-mode hid themselves (feature-off by absence works, no dead buttons,
  render does not break). (`07-chatsurface.png`)
- **#2 (no full-page ChatSurface) — FIXED.** `<ChatSurface>` exists, mounts
  always-open + full-page, no FloatingButton, reuses ChatWidgetContainer.
- **#3 (messages Tailwind coupling) — DOCUMENTED.** fi-glass README now documents
  the content-glob requirement (v3 + v4).

### NEW residual defects (surfaced BY the canary — do NOT patch in og118)

The canary did its job: fixing one layer exposed the next.

- **#6 — the SHELL carries an undocumented `chat-*` CSS coupling, wider than #3.**
  `<ChatSurface>` rendered structurally correct but **unstyled** in og118:
  ChatContent/ChatToolbar/ChatWidgetContainer emit semantic classes
  (`chat-container-embedded`, `chat-toolbar`, `chat-input-wrapper`,
  `chat-toolbar-btn`, …) that live in aurity's `chat.css`. A fresh app inherits
  them empty. #3 documented the messages coupling; this is the same disease in
  the shell, larger and undocumented. Fix: ship a base shell stylesheet with
  fi-glass (or document the required classes), like a future compiled-CSS option.
- **#7 — `ChatStartScreen` ships aurity-specific marketing copy.** The default
  empty state rendered "IA offline para tu desarrollo profesional / Licencias
  piloto / Ir a Descargas" — aurity's wording fossilized as the framework
  default. Fix: neutralize the default copy and/or make it a required slot.
- **#8 — there is NO full-page composition for the AgentHook glass-box.**
  `<ChatSurface>` is a ChatHook surface; og118's PRODUCTION view is the agentic
  glass-box (`AgentPanel`), which still hand-rolls its own flex layout
  (`Og118AgentChat`). ChatSurface does not fit it — adopting it for `/` would be
  forced (wrong model). The chat-first packaging exists for ChatHook but not for
  the agentic turn. Candidate: an `<AgentSurface>` (or an `agentPanel` mode on
  ChatSurface) that packages Composer + AgentPanel full-page. **The most
  substantive of the three — but build it ONLY when og118 gets polished for
  production and the hand-rolled layout is the REAL bottleneck, not speculatively.**

### Disposition — BACKLOG, not an imminent fix loop

og118 already WORKS on v1.1.0: the glass-box runs, the new lifecycle states
render, the e2e passes. #6/#7/#8 are framework PACKAGING improvements, not app
blockers. They are deliberately **backlogged**, not turned into another bump loop
now — entering one risks the "one more layer before launch" infinite cycle. They
get picked up when a real consumer need (not speculation) makes each the
bottleneck: #6/#7 when a fresh app ships a styled ChatHook surface; #8 when
og118's production polish makes the hand-rolled agentic layout the actual pain.

### Verdict

The fixes resolved exactly the friction og118 reported in v0 (#1–#5). og118's
PRODUCTION surface (agentic) adopts the core fix via the hook and renders the new
lifecycle states live — that is the canary that matters. ChatSurface fits the
ChatHook model cleanly (props/feature-off proven) but is not og118's production
shape, and probing it surfaced the next layer (#6–#8), now backlogged. Loop
closed.
