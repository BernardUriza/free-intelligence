// src/agent/state.ts
function initialAgentTurnState() {
  return {
    plan: null,
    steps: [],
    text: "",
    sources: [],
    meta: null,
    author: null,
    heartbeats: 0,
    status: "thinking"
  };
}
function applyAgentEvent(state, event) {
  const streamingStatus = state.status === "thinking" ? "streaming" : state.status;
  switch (event.type) {
    case "open":
      return state;
    case "plan":
      return {
        ...state,
        plan: {
          steps: event.steps.map((label) => ({ label, status: "pending" })),
          rejection: null,
          amended: null,
          outcome: null
        },
        status: streamingStatus
      };
    case "plan_rejected":
      return state.plan ? { ...state, plan: { ...state.plan, rejection: event.rejection } } : { ...state, plan: { steps: [], rejection: event.rejection } };
    case "step_started": {
      if (!state.plan) return state;
      const idx = event.index;
      if (idx < 0 || idx >= state.plan.steps.length) return state;
      const steps = state.plan.steps.map((s, i) => {
        if (i < idx && (s.status === "pending" || s.status === "running")) {
          return { ...s, status: "done" };
        }
        if (i === idx) return { ...s, status: "running" };
        return s;
      });
      return { ...state, plan: { ...state.plan, steps } };
    }
    case "step_done": {
      if (!state.plan) return state;
      const idx = event.index;
      if (idx < 0 || idx >= state.plan.steps.length) return state;
      const steps = state.plan.steps.map((s, i) => {
        if (i !== idx) return s;
        const patch = { ...s, status: event.status };
        if (event.status === "done") {
          if (event.summary) patch.summary = event.summary;
        } else if (event.error) {
          patch.error = event.error;
        }
        return patch;
      });
      return { ...state, plan: { ...state.plan, steps } };
    }
    case "step_noted": {
      if (!state.plan) return state;
      const idx = event.index;
      if (idx < 0 || idx >= state.plan.steps.length) return state;
      const steps = state.plan.steps.map(
        (s, i) => i === idx ? { ...s, note: event.note } : s
      );
      return { ...state, plan: { ...state.plan, steps } };
    }
    case "plan_amended":
      return state.plan ? { ...state, plan: { ...state.plan, amended: event.action } } : state;
    case "plan_cancelled": {
      if (!state.plan) return state;
      const steps = state.plan.steps.map(
        (s) => s.status === "pending" || s.status === "running" ? { ...s, status: "cancelled" } : s
      );
      return { ...state, plan: { ...state.plan, steps, outcome: "cancelled" } };
    }
    case "plan_completed":
      return state.plan ? { ...state, plan: { ...state.plan, outcome: "completed" } } : state;
    case "plan_failed":
      return state.plan ? { ...state, plan: { ...state.plan, outcome: "failed" } } : state;
    case "tool_call": {
      const existing = event.call.id != null ? state.steps.findIndex((c) => c.id === event.call.id) : -1;
      const steps = existing >= 0 ? state.steps.map((c, i) => i === existing ? event.call : c) : [...state.steps, event.call];
      return { ...state, steps, status: streamingStatus };
    }
    case "text":
      return {
        ...state,
        text: state.text + event.delta,
        status: streamingStatus
      };
    case "result": {
      const text = event.text.trim() ? event.text : state.text;
      const plan = state.plan ? {
        ...state.plan,
        steps: state.plan.steps.map(
          (s) => s.status === "pending" || s.status === "running" ? { ...s, status: "done" } : s
        )
      } : state.plan;
      return {
        ...state,
        text,
        plan,
        sources: event.sources ?? state.sources,
        meta: event.meta ?? state.meta,
        status: "done"
      };
    }
    case "author":
      return { ...state, author: event.author };
    case "ping":
      return { ...state, heartbeats: state.heartbeats + 1 };
    case "meta":
      return { ...state, meta: event.meta };
    case "error":
      return { ...state, status: "error", errorMessage: event.message };
    case "done":
      return state.status === "thinking" || state.status === "streaming" ? { ...state, status: "done" } : state;
    default:
      return state;
  }
}

// src/agent/transcript.ts
function makeUserMessage(text, author, images) {
  return {
    role: "user",
    author,
    content: text,
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    ...images && images.length > 0 ? { images } : {}
  };
}
function snapshotTrace(turn) {
  const hasPlan = turn.plan != null && turn.plan.steps.length > 0;
  const hasTools = turn.steps.length > 0;
  const hasSources = turn.sources.length > 0;
  const model = turn.meta?.model?.trim() || void 0;
  if (!hasPlan && !hasTools && !hasSources && !model) return void 0;
  return {
    ...hasPlan ? { plan: turn.plan } : {},
    ...hasTools ? { tools: turn.steps } : {},
    ...hasSources ? { sources: turn.sources } : {},
    ...model ? { model } : {}
  };
}
function foldAssistantTurn(turn, defaultAuthor) {
  const trace = snapshotTrace(turn);
  return {
    role: "assistant",
    author: turn.author ?? defaultAuthor,
    content: turn.text,
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    ...trace ? { trace } : {}
  };
}

// src/agent/conversation-state.ts
function initialConversationState(seed = []) {
  return {
    messages: seed,
    pending: false,
    failure: null,
    timedOut: false,
    unsent: { text: null, images: null },
    lastSent: null,
    // The mount seed is not a confirmed turn.
    skipPersist: true
  };
}
var NO_DRAFT = { text: null, images: null };
function revertOptimistic(state, controlled) {
  if (controlled) return state;
  const last = state.messages[state.messages.length - 1];
  if (last?.role !== "user") return state;
  return {
    ...state,
    messages: state.messages.slice(0, -1),
    unsent: {
      text: last.content,
      images: last.images && last.images.length > 0 ? last.images : null
    }
  };
}
function applyConversationEvent(state, event) {
  switch (event.type) {
    case "send": {
      const text = event.text.trim();
      const images = event.images && event.images.length > 0 ? event.images : void 0;
      if (!text && !images) return state;
      const next = {
        ...state,
        pending: true,
        failure: null,
        timedOut: false,
        // A new send supersedes any draft still waiting to be recovered.
        unsent: NO_DRAFT,
        lastSent: { text, ...images ? { images } : {} },
        // The optimistic push is not a confirmed turn.
        skipPersist: true
      };
      if (event.controlled) return next;
      return {
        ...next,
        messages: [...state.messages, makeUserMessage(text, event.author, images)]
      };
    }
    case "turn_settled": {
      if (!state.pending) return state;
      const base = { ...state, pending: false };
      if (event.controlled || !event.turn.text) return base;
      return {
        ...base,
        messages: [...state.messages, foldAssistantTurn(event.turn, event.author)],
        // A settled turn IS confirmed — this one gets persisted.
        skipPersist: false
      };
    }
    case "turn_failed": {
      if (!state.pending) return state;
      const reverted = revertOptimistic({ ...state, pending: false }, event.controlled);
      if (event.appHandled) return reverted;
      return {
        ...reverted,
        failure: {
          kind: "stream",
          message: event.message || "La respuesta fall\xF3. Intenta de nuevo."
        }
      };
    }
    case "turn_timeout": {
      if (!state.pending || state.timedOut) return state;
      return {
        ...revertOptimistic({ ...state, pending: false }, event.controlled),
        timedOut: true,
        failure: { kind: "timeout", message: "La respuesta tard\xF3 demasiado. Intenta de nuevo." }
      };
    }
    case "dismiss_failure":
      return state.failure === null ? state : { ...state, failure: null, timedOut: false };
    case "clear_unsent":
      return state.unsent.text === null && state.unsent.images === null ? state : { ...state, unsent: NO_DRAFT };
    case "hydrate":
      return { ...initialConversationState(event.messages), lastSent: state.lastSent };
    case "persist_skip_consumed":
      return state.skipPersist ? { ...state, skipPersist: false } : state;
    default:
      return state;
  }
}

// src/conversation/helpers.ts
var CONVERSATION_SCHEMA_VERSION = 1;
var DEFAULT_TITLE = "New chat";
var TITLE_MAX = 60;
var PREVIEW_MAX = 120;
function truncate(text, max) {
  const t = text.trim().replace(/\s+/g, " ");
  if (t.length <= max) return t;
  return `${t.slice(0, Math.max(0, max - 1)).trimEnd()}\u2026`;
}
function sanitizeConversationMessage(message) {
  return {
    role: message.role,
    content: message.content,
    timestamp: message.timestamp,
    ...message.author ? { author: message.author } : {},
    ...message.trace ? { trace: message.trace } : {},
    // Attached images are user-visible message CONTENT (OG118-IMAGE-UPLOAD-1),
    // not metadata — dropping them would blank the picture on reload the way
    // dropping `author` used to anonymize bubbles. Producers downscale before
    // encoding, so the persisted base64 stays within the record size caps.
    ...message.images && message.images.length > 0 ? { images: message.images.map((i) => ({ mediaType: i.mediaType, data: i.data })) } : {}
  };
}
function deriveConversationTitle(messages, max = TITLE_MAX) {
  const firstUser = messages.find(
    (m) => m.role === "user" && m.content.trim() !== ""
  );
  if (!firstUser) return DEFAULT_TITLE;
  return truncate(firstUser.content, max) || DEFAULT_TITLE;
}
function deriveConversationPreview(messages, max = PREVIEW_MAX) {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].content.trim() !== "") {
      return truncate(messages[i].content, max);
    }
  }
  return "";
}
function createConversationRecord(args) {
  const now = args.now ?? (/* @__PURE__ */ new Date()).toISOString();
  const messages = (args.messages ?? []).map(sanitizeConversationMessage);
  return {
    id: args.id,
    title: deriveConversationTitle(messages),
    createdAt: now,
    updatedAt: now,
    messages,
    preview: deriveConversationPreview(messages),
    schemaVersion: CONVERSATION_SCHEMA_VERSION
  };
}
function resolveConversationTitle(messages, prev) {
  if (prev?.titleCustom && prev.title.trim() !== "") return prev.title;
  return deriveConversationTitle(messages);
}
function renameConversationRecord(record, rawTitle, now) {
  const trimmed = rawTitle.trim().replace(/\s+/g, " ");
  const ts = now ?? (/* @__PURE__ */ new Date()).toISOString();
  if (trimmed === "") {
    return {
      ...record,
      title: deriveConversationTitle(record.messages),
      titleCustom: false,
      updatedAt: ts
    };
  }
  return {
    ...record,
    title: trimmed.slice(0, TITLE_MAX),
    titleCustom: true,
    updatedAt: ts
  };
}
function setConversationPinned(record, pinned, now) {
  if (pinned) {
    const { archivedAt: _archivedAt, ...rest2 } = record;
    return { ...rest2, pinnedAt: now ?? (/* @__PURE__ */ new Date()).toISOString() };
  }
  const { pinnedAt: _pinnedAt, ...rest } = record;
  return rest;
}
function setConversationArchived(record, archived, now) {
  if (archived) {
    const { pinnedAt: _pinnedAt, ...rest2 } = record;
    return { ...rest2, archivedAt: now ?? (/* @__PURE__ */ new Date()).toISOString() };
  }
  const { archivedAt: _archivedAt, ...rest } = record;
  return rest;
}
function summarizeConversation(record) {
  return {
    id: record.id,
    title: record.title,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
    preview: record.preview,
    ...record.pinnedAt ? { pinnedAt: record.pinnedAt } : {},
    ...record.archivedAt ? { archivedAt: record.archivedAt } : {}
  };
}
function normalizeForSearch(text) {
  return text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}
function filterConversationSummaries(summaries, query) {
  const terms = normalizeForSearch(query).split(/\s+/).filter(Boolean);
  if (terms.length === 0) return summaries;
  return summaries.filter((s) => {
    const haystack = normalizeForSearch(`${s.title} ${s.preview}`);
    return terms.every((t) => haystack.includes(t));
  });
}
function organizeConversationSummaries(summaries) {
  const pinned = [];
  const active = [];
  const archived = [];
  for (const s of summaries) {
    if (s.archivedAt) archived.push(s);
    else if (s.pinnedAt) pinned.push(s);
    else active.push(s);
  }
  pinned.sort((a, b) => (b.pinnedAt ?? "").localeCompare(a.pinnedAt ?? ""));
  active.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  archived.sort((a, b) => (b.archivedAt ?? "").localeCompare(a.archivedAt ?? ""));
  return { pinned, active, archived };
}
export {
  CONVERSATION_SCHEMA_VERSION,
  applyAgentEvent,
  applyConversationEvent,
  createConversationRecord,
  deriveConversationPreview,
  deriveConversationTitle,
  filterConversationSummaries,
  foldAssistantTurn,
  initialAgentTurnState,
  initialConversationState,
  makeUserMessage,
  organizeConversationSummaries,
  renameConversationRecord,
  resolveConversationTitle,
  sanitizeConversationMessage,
  setConversationArchived,
  setConversationPinned,
  summarizeConversation
};
//# sourceMappingURL=index.js.map