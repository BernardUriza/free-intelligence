'use client';

import {
  useEdgeSwipe,
  useMediaQuery
} from "./chunk-TZYRBKX6.js";
import {
  AudioVisualizer,
  ComposerMicSlot,
  useDictation
} from "./chunk-NKH57TOL.js";
import {
  Composer,
  ComposerActions,
  ComposerFrame,
  ComposerImageChips,
  ensureDensityStyle,
  useComposerActionStyle,
  useComposerImages,
  useDensityStyle,
  useImagePicker,
  withComposerAction
} from "./chunk-VR5XNHGN.js";
import {
  CopyButton,
  MessageAuthorHeader,
  MessageBubble,
  MessageContent,
  MessageImages,
  MessageReactions,
  defaultMessageBadge,
  defaultMessageHeader
} from "./chunk-6Z6QRICA.js";
import {
  glassTokens
} from "./chunk-LO4SF24V.js";
import {
  FI_TOUCH_TARGET_CLASS,
  useTouchTargetStyle,
  withTouchTarget
} from "./chunk-SMPLGG7E.js";
import {
  FI_MOBILE_QUERY,
  FI_TOUCH_QUERY
} from "./chunk-HJ2CVNCV.js";

// src/agent/icons.ts
import {
  AlertTriangle,
  BookOpen,
  Bot,
  ExternalLink,
  FileText,
  Globe,
  ListChecks,
  Loader2,
  Receipt,
  Search,
  Terminal,
  Wrench
} from "lucide-react";

// src/agent/toolClassify.ts
function classifyTool(name) {
  const n = name.toLowerCase();
  if (n.includes("search")) return "search";
  if (n.includes("scrape") || n.includes("fetch") || n.includes("unlock")) return "scrape";
  if (n.includes("browser")) return "browser";
  if (n.includes("document") || n.includes("rag")) return "rag";
  if (n === "bash" || n.endsWith("__bash")) return "bash";
  if (n.includes("listmcp") || n.includes("listtool")) return "introspect";
  return "generic";
}
function shortToolName(name) {
  return name.replace(/^mcp__[^_]+__/, "");
}
function stepStatusKey(isError) {
  if (isError === null) return "pending";
  return isError ? "error" : "done";
}
function latestOpenToolIndex(steps) {
  return steps.reduce(
    (latest, step, index) => step.isError === null ? index : latest,
    -1
  );
}
function toolVisualStatus(step, index, latestOpenIndex, live) {
  const raw = stepStatusKey(step.isError);
  if (raw === "error") return "error";
  if (raw === "done") return "done";
  if (!live) return "done";
  return index === latestOpenIndex ? "active" : "sent";
}

// src/agent/icons.ts
var defaultAgentIcons = {
  plan: ListChecks,
  warning: AlertTriangle,
  spinner: Loader2,
  bot: Bot,
  sources: Receipt,
  external: ExternalLink,
  tools: {
    search: Search,
    scrape: FileText,
    browser: Globe,
    rag: BookOpen,
    bash: Terminal,
    introspect: ListChecks,
    generic: Wrench
  }
};
function resolveIcons(overrides) {
  if (!overrides) return defaultAgentIcons;
  return {
    ...defaultAgentIcons,
    ...overrides,
    tools: { ...defaultAgentIcons.tools, ...overrides.tools ?? {} }
  };
}
function toolIcon(icons, name) {
  return icons.tools[classifyTool(name)];
}

// src/agent/PlanChecklist.tsx
import { jsx, jsxs } from "react/jsx-runtime";
function PlanChecklist({
  plan,
  classNames,
  icons,
  renderGuardBanner
}) {
  if (!plan || plan.steps.length === 0) return null;
  const ic = resolveIcons(icons);
  const PlanIcon = ic.plan;
  const WarnIcon = ic.warning;
  const card = classNames?.card ?? "";
  const hint = classNames?.hint ?? "";
  const done = plan.steps.filter((s) => s.status === "done").length;
  const total = plan.steps.length;
  const rejection = plan.rejection ?? null;
  const matchedIndexes = new Set(rejection?.matched.map((m) => m.index) ?? []);
  const outcome = plan.outcome ?? null;
  const outcomeBadge = outcome === "completed" ? { label: "completed", tone: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" } : outcome === "failed" ? { label: "failed", tone: "border-red-500/30 bg-red-500/10 text-red-300" } : outcome === "cancelled" ? { label: "cancelled", tone: "border-zinc-500/30 bg-zinc-500/10 text-zinc-400" } : null;
  const amended = plan.amended ?? null;
  const amendedLabel = amended === "replan" ? "re-planned" : amended === "insert" ? "revised" : null;
  return /* @__PURE__ */ jsxs("div", { className: `${card} mb-2 text-sm`.trim(), children: [
    /* @__PURE__ */ jsxs("div", { className: "flex items-center justify-between gap-2 text-zinc-300", children: [
      /* @__PURE__ */ jsxs("span", { className: "inline-flex items-center gap-2 font-medium", children: [
        /* @__PURE__ */ jsx(PlanIcon, { className: "h-4 w-4 text-zinc-400", "aria-hidden": true }),
        "plan",
        amendedLabel && /* @__PURE__ */ jsx("span", { className: "rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-amber-300", children: amendedLabel }),
        outcomeBadge && /* @__PURE__ */ jsx("span", { className: `rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${outcomeBadge.tone}`, children: outcomeBadge.label })
      ] }),
      /* @__PURE__ */ jsxs("span", { className: `${hint} text-xs tabular-nums`.trim(), children: [
        done,
        " / ",
        total
      ] })
    ] }),
    rejection && (renderGuardBanner ? renderGuardBanner(rejection) : /* @__PURE__ */ jsxs("div", { className: "mt-2 flex items-start gap-2 rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-200", children: [
      /* @__PURE__ */ jsx(
        WarnIcon,
        {
          className: "mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400",
          "aria-hidden": true
        }
      ),
      /* @__PURE__ */ jsxs("div", { className: "flex flex-col gap-0.5", children: [
        /* @__PURE__ */ jsx("span", { className: "font-medium", children: "A guard blocked this plan" }),
        /* @__PURE__ */ jsx("span", { className: "text-amber-200/80", children: rejection.reason }),
        rejection.guard && /* @__PURE__ */ jsxs(
          "span",
          {
            className: `${hint} text-[10px] uppercase tracking-wide text-amber-300/60`.trim(),
            children: [
              "guard: ",
              rejection.guard
            ]
          }
        )
      ] })
    ] })),
    /* @__PURE__ */ jsx("ol", { className: "mt-2 space-y-1.5", children: plan.steps.map((step, i) => {
      const isRunning = step.status === "running";
      const isPending = step.status === "pending";
      const isDone = step.status === "done";
      const isFailed = step.status === "failed";
      const isCancelled = step.status === "cancelled";
      const isRejected = matchedIndexes.has(i);
      const labelTone = isRejected ? "text-amber-300 line-through decoration-amber-500/60" : isFailed ? "text-red-400" : isCancelled ? "text-zinc-500 line-through decoration-zinc-600" : isDone ? "text-zinc-300" : isRunning ? "text-zinc-100" : "text-zinc-500";
      const railTone = isFailed ? "text-red-400" : isCancelled ? "text-zinc-500 bg-zinc-500" : isDone ? "text-emerald-400 bg-emerald-400" : isRunning ? "text-amber-300 bg-amber-300" : "text-zinc-600 bg-zinc-700";
      return /* @__PURE__ */ jsxs("li", { className: "flex flex-col gap-0.5", children: [
        /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-2 text-xs", children: [
          /* @__PURE__ */ jsx(
            "span",
            {
              className: `h-5 w-1 shrink-0 rounded-full ${railTone} ${isRunning ? "shadow-[0_0_10px_rgb(251_191_36/0.45)]" : ""}`,
              "aria-label": step.status
            }
          ),
          /* @__PURE__ */ jsx("span", { className: `flex-1 truncate ${labelTone}`, children: step.label }),
          isPending && /* @__PURE__ */ jsx("span", { className: `${hint} text-[10px] uppercase tracking-wide`.trim(), children: "queued" }),
          isRunning && /* @__PURE__ */ jsx("span", { className: "text-[10px] uppercase tracking-wide text-amber-300", children: "running" }),
          isCancelled && /* @__PURE__ */ jsx("span", { className: `${hint} text-[10px] uppercase tracking-wide`.trim(), children: "cancelled" })
        ] }),
        step.summary && isDone && /* @__PURE__ */ jsx("div", { className: `${hint} pl-5 font-mono text-[11px] text-zinc-500`.trim(), children: step.summary }),
        step.error && isFailed && /* @__PURE__ */ jsx("div", { className: "pl-5 font-mono text-[11px] text-red-400/80", children: step.error }),
        step.error && isCancelled && /* @__PURE__ */ jsx("div", { className: "pl-5 font-mono text-[11px] text-zinc-500", children: step.error }),
        step.note && /* @__PURE__ */ jsxs("div", { className: "pl-5 text-[11px] italic text-zinc-400", children: [
          "note: ",
          step.note
        ] })
      ] }, i);
    }) })
  ] });
}

// src/agent/StepsPanel.tsx
import { useEffect, useState } from "react";
import { jsx as jsx2, jsxs as jsxs2 } from "react/jsx-runtime";
function StepsPanel({
  steps,
  status,
  target,
  classNames,
  icons,
  enableSlowBanner = true,
  slowThresholdMs = 12e3
}) {
  const ic = resolveIcons(icons);
  const BotIcon = ic.bot;
  const SpinnerIcon = ic.spinner;
  const card = classNames?.card ?? "";
  const hint = classNames?.hint ?? "";
  const live = status === "thinking" || status === "streaming";
  const [openOverride, setOpenOverride] = useState(null);
  const open = openOverride ?? live;
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!live || !enableSlowBanner) {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const t = setInterval(() => setElapsed(Date.now() - start), 500);
    return () => clearInterval(t);
  }, [live, enableSlowBanner]);
  const showSlowBanner = live && enableSlowBanner && elapsed >= slowThresholdMs;
  if (steps.length === 0 && status === "done") return null;
  const shortTarget = target && target.length > 36 ? `${target.slice(0, 33).trim()}\u2026` : target;
  const summary = status === "thinking" ? shortTarget ? `Unlocking ${shortTarget}\u2026` : "thinking\u2026" : status === "streaming" && steps.length === 0 ? "writing\u2026" : `${steps.length} ${steps.length === 1 ? "step" : "steps"}`;
  const latestPendingIndex = live ? latestOpenToolIndex(steps) : -1;
  return /* @__PURE__ */ jsxs2("div", { className: `${card} mb-2 text-sm`.trim(), children: [
    /* @__PURE__ */ jsxs2(
      "button",
      {
        type: "button",
        onClick: () => setOpenOverride(!open),
        className: "flex w-full items-center justify-between gap-2 text-left text-zinc-300 hover:text-zinc-100",
        "aria-expanded": open,
        children: [
          /* @__PURE__ */ jsxs2("span", { className: "inline-flex items-center gap-2 font-medium", children: [
            /* @__PURE__ */ jsx2(BotIcon, { className: "h-4 w-4 text-zinc-400", "aria-hidden": true }),
            summary
          ] }),
          /* @__PURE__ */ jsx2("span", { className: `${hint} text-xs`.trim(), children: open ? "hide" : "show" })
        ]
      }
    ),
    showSlowBanner && /* @__PURE__ */ jsxs2(
      "div",
      {
        className: "mt-2 inline-flex items-center gap-2 rounded-lg border border-sky-700/40 bg-sky-950/30 p-2.5 text-xs text-sky-200",
        role: "status",
        "aria-live": "polite",
        children: [
          /* @__PURE__ */ jsx2(
            SpinnerIcon,
            {
              className: "h-3.5 w-3.5 shrink-0 animate-spin text-sky-400",
              "aria-hidden": true
            }
          ),
          /* @__PURE__ */ jsx2("span", { children: "Still working. This can take a second." })
        ]
      }
    ),
    open && steps.length > 0 && /* @__PURE__ */ jsx2("ol", { className: "mt-2 space-y-1", children: steps.map((s, i) => {
      const ToolIcon = toolIcon(ic, s.name);
      const statusKey = toolVisualStatus(s, i, latestPendingIndex, live);
      const errored = statusKey === "error";
      const active = statusKey === "active";
      return /* @__PURE__ */ jsxs2(
        "li",
        {
          className: `flex items-center gap-2 font-mono text-xs ${errored ? "text-red-400" : "text-zinc-400"}`,
          children: [
            /* @__PURE__ */ jsx2(ToolIcon, { className: "h-3.5 w-3.5 shrink-0", "aria-hidden": true }),
            /* @__PURE__ */ jsx2("span", { className: "truncate", children: shortToolName(s.name) }),
            s.server && s.server !== "brightdata" && /* @__PURE__ */ jsxs2("span", { className: `${hint} text-[10px] uppercase`.trim(), children: [
              "\xB7 ",
              s.server
            ] }),
            /* @__PURE__ */ jsx2(
              "span",
              {
                className: `ml-auto rounded-full border px-1.5 py-0.5 text-[9px] uppercase tracking-wide ${active ? "border-amber-400/30 bg-amber-400/10 text-amber-300" : statusKey === "sent" ? "border-zinc-500/25 bg-zinc-500/10 text-zinc-400" : errored ? "border-red-400/30 bg-red-400/10 text-red-300" : "border-emerald-400/25 bg-emerald-400/10 text-emerald-300"}`,
                "aria-label": statusKey,
                children: statusKey
              }
            )
          ]
        },
        s.id ?? `${s.name}-${i}`
      );
    }) })
  ] });
}

// src/agent/SourcesPanel.tsx
import { jsx as jsx3, jsxs as jsxs3 } from "react/jsx-runtime";
function splitSource(url) {
  try {
    const u = new URL(url);
    const host = u.host.replace(/^www\./, "");
    const rest = `${u.pathname}${u.search}${u.hash}`;
    return { host, rest: rest === "/" ? "" : rest };
  } catch {
    return { host: url, rest: "" };
  }
}
function SourcesPanel({
  sources,
  classNames,
  icons,
  label = "Sources"
}) {
  if (sources.length === 0) return null;
  const ic = resolveIcons(icons);
  const SourcesIcon = ic.sources;
  const ExternalIcon = ic.external;
  const card = classNames?.card ?? "";
  const hint = classNames?.hint ?? "";
  const row = classNames?.sourceRow ?? "bg-zinc-500/10 hover:border-zinc-400/40 hover:bg-zinc-500/20";
  return /* @__PURE__ */ jsxs3("div", { className: `${card} text-sm`.trim(), children: [
    /* @__PURE__ */ jsxs3("h2", { className: "mb-3 inline-flex items-center gap-2 font-medium text-zinc-200", children: [
      /* @__PURE__ */ jsx3(SourcesIcon, { className: "h-4 w-4 text-zinc-400", "aria-hidden": true }),
      label,
      /* @__PURE__ */ jsxs3("span", { className: `${hint} ml-1 text-xs tabular-nums`.trim(), children: [
        "(",
        sources.length,
        ")"
      ] })
    ] }),
    /* @__PURE__ */ jsx3("ul", { className: "flex flex-col gap-1.5 text-sm", children: sources.map((u) => {
      const { host, rest } = splitSource(u);
      return /* @__PURE__ */ jsx3("li", { children: /* @__PURE__ */ jsxs3(
        "a",
        {
          href: u,
          target: "_blank",
          rel: "noopener noreferrer",
          className: `group flex items-center gap-2 rounded-lg border border-transparent px-3 py-2 transition ${row}`,
          children: [
            /* @__PURE__ */ jsxs3("span", { className: "truncate", children: [
              /* @__PURE__ */ jsx3("span", { className: "font-semibold text-zinc-100", children: host }),
              rest && /* @__PURE__ */ jsx3("span", { className: "ml-0.5 font-mono text-xs text-zinc-500", children: rest })
            ] }),
            /* @__PURE__ */ jsx3(
              ExternalIcon,
              {
                className: "ml-auto h-3.5 w-3.5 shrink-0 text-zinc-400 opacity-0 transition group-hover:opacity-100",
                "aria-hidden": true
              }
            )
          ]
        }
      ) }, u);
    }) })
  ] });
}

// src/agent/AgentPanel.tsx
import { Fragment, jsx as jsx4, jsxs as jsxs4 } from "react/jsx-runtime";
function AgentPanel({
  turn,
  target,
  classNames,
  icons,
  enableSlowBanner,
  slowThresholdMs,
  renderSources,
  renderGuardBanner
}) {
  return /* @__PURE__ */ jsxs4(Fragment, { children: [
    /* @__PURE__ */ jsx4(
      PlanChecklist,
      {
        plan: turn.plan,
        classNames,
        icons,
        renderGuardBanner
      }
    ),
    /* @__PURE__ */ jsx4(
      StepsPanel,
      {
        steps: turn.steps,
        status: turn.status,
        target,
        classNames,
        icons,
        enableSlowBanner,
        slowThresholdMs
      }
    ),
    renderSources ? renderSources(turn.sources) : /* @__PURE__ */ jsx4(SourcesPanel, { sources: turn.sources, classNames, icons })
  ] });
}

// src/agent/useAgentConversation.ts
import { useCallback, useEffect as useEffect2, useReducer, useRef, useState as useState2 } from "react";
import {
  applyConversationEvent,
  initialConversationState,
  foldAssistantTurn
} from "@free-intelligence/core";
var DEFAULT_USER_AUTHOR = { id: "user", name: "T\xFA", symbol: "T\xFA" };
var DEFAULT_PERSIST_ERROR = "No se pudo guardar esta conversaci\xF3n. Sigue en pantalla, pero podr\xEDas perderla al recargar.";
var DEFAULT_TURN_TIMEOUT_MS = 6e4;
function sameThread(a, b) {
  if (a.length !== b.length) return false;
  return a.every((m, i) => {
    const o = b[i];
    return m.role === o.role && m.content === o.content && m.timestamp === o.timestamp;
  });
}
function useAgentConversation(agent, options) {
  const {
    author,
    userAuthor = DEFAULT_USER_AUTHOR,
    externalMessages,
    conversationId,
    initialMessages,
    seedVersion,
    onMessagesChange,
    onTurnStart,
    turnTimeoutMs = DEFAULT_TURN_TIMEOUT_MS,
    isAppHandledError
  } = options;
  const controlled = externalMessages !== void 0;
  const [convo, dispatch] = useReducer(
    applyConversationEvent,
    void 0,
    () => initialConversationState(initialMessages ?? [])
  );
  const convoRef = useRef(convo);
  convoRef.current = convo;
  const messages = convo.messages;
  const turnError = convo.failure;
  const turnNotice = convo.notice;
  const timedOut = convo.timedOut;
  const controlledRef = useRef(controlled);
  const stoppedRef = useRef(false);
  controlledRef.current = controlled;
  const authorRef = useRef(author);
  authorRef.current = author;
  const userAuthorRef = useRef(userAuthor);
  userAuthorRef.current = userAuthor;
  const onMessagesChangeRef = useRef(onMessagesChange);
  onMessagesChangeRef.current = onMessagesChange;
  const onTurnStartRef = useRef(onTurnStart);
  onTurnStartRef.current = onTurnStart;
  const [persistError, setPersistError] = useState2(null);
  const unsaved = useRef(null);
  const runPersist = useCallback(async (thread, conversationId2) => {
    if (!onMessagesChangeRef.current) return;
    try {
      await onMessagesChangeRef.current(thread, conversationId2);
      unsaved.current = null;
      setPersistError(null);
    } catch (cause) {
      unsaved.current = { thread, conversationId: conversationId2 };
      setPersistError({
        message: cause instanceof Error && cause.message ? cause.message : DEFAULT_PERSIST_ERROR,
        cause
      });
    }
  }, []);
  const retryPersist = useCallback(() => {
    const failed = unsaved.current;
    if (!failed) return;
    setPersistError(null);
    void runPersist(failed.thread, failed.conversationId);
  }, [runPersist]);
  const dismissPersistError = useCallback(() => setPersistError(null), []);
  const clearUnsent = useCallback(() => dispatch({ type: "clear_unsent" }), []);
  const messagesRef = useRef(messages);
  messagesRef.current = externalMessages ?? messages;
  const agentRef = useRef(agent);
  agentRef.current = agent;
  const appHandledRef = useRef(isAppHandledError);
  appHandledRef.current = isAppHandledError;
  const initialRef = useRef(initialMessages);
  initialRef.current = initialMessages;
  const mounted = useRef(false);
  const hydratedFor = useRef(conversationId);
  const awaitResolver = useRef(null);
  const abandonAwaited = useCallback((reason) => {
    const r = awaitResolver.current;
    awaitResolver.current = null;
    r?.reject(new Error(reason));
  }, []);
  const send = useCallback(
    (text, images) => {
      const t = text.trim();
      const imgs = images && images.length > 0 ? images : void 0;
      if (!t && !imgs || agent.isStreaming) return false;
      dispatch({
        type: "send",
        text: t,
        images: imgs,
        author: userAuthorRef.current,
        controlled
      });
      onTurnStartRef.current?.(hydratedFor.current ?? void 0);
      void agent.send(t, { history: messagesRef.current, ...imgs ? { images: imgs } : {} });
      return true;
    },
    [agent, controlled]
  );
  const sendAndAwait = useCallback(
    (text) => {
      const t = text.trim();
      if (!t) return Promise.resolve("");
      if (agent.isStreaming) return Promise.reject(new Error("a turn is already streaming"));
      return new Promise((resolve, reject) => {
        abandonAwaited("superseded by a newer turn");
        awaitResolver.current = { resolve, reject };
        if (!send(t)) abandonAwaited("the turn could not be sent");
      });
    },
    [agent.isStreaming, send, abandonAwaited]
  );
  const stop = useCallback(() => {
    if (!agentRef.current.isStreaming) return;
    stoppedRef.current = true;
    agentRef.current.abort?.();
  }, []);
  const retry = useCallback(() => {
    const last = convoRef.current.lastSent;
    if (last) send(last.text, last.images);
  }, [send]);
  const dismissError = useCallback(() => dispatch({ type: "dismiss_failure" }), []);
  const dismissNotice = useCallback(() => dispatch({ type: "dismiss_notice" }), []);
  useEffect2(() => {
    if (agent.isStreaming || !convoRef.current.pending) return;
    if (agent.turn.status === "error") {
      const r = awaitResolver.current;
      awaitResolver.current = null;
      r?.reject(new Error(agent.turn.errorMessage || "turn failed"));
      dispatch({
        type: "turn_failed",
        message: agent.turn.errorMessage,
        controlled: controlledRef.current,
        appHandled: appHandledRef.current?.(agent.turn)
      });
      return;
    }
    const finalText = agent.turn.text || "";
    dispatch({
      type: "turn_settled",
      turn: agent.turn,
      author: authorRef.current,
      controlled: controlledRef.current,
      stopped: stoppedRef.current
    });
    stoppedRef.current = false;
    const resolver = awaitResolver.current;
    awaitResolver.current = null;
    resolver?.resolve(finalText);
  }, [agent.isStreaming, agent.turn]);
  useEffect2(() => {
    if (turnTimeoutMs <= 0) return;
    if (!agent.isStreaming || !convoRef.current.pending || timedOut) return;
    const timer = setTimeout(() => {
      agentRef.current.abort?.();
      const r = awaitResolver.current;
      awaitResolver.current = null;
      r?.reject(new Error("turn timed out"));
      dispatch({ type: "turn_timeout", controlled: controlledRef.current });
    }, turnTimeoutMs);
    return () => clearTimeout(timer);
  }, [agent.isStreaming, agent.turn, timedOut, turnTimeoutMs]);
  useEffect2(() => {
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    if (controlledRef.current) return;
    const origin = hydratedFor.current;
    const switched = origin !== conversationId;
    hydratedFor.current = conversationId;
    const seed = initialRef.current ?? [];
    if (!switched) {
      if (convoRef.current.pending) {
        dispatch({ type: "merge_seed", messages: seed });
        return;
      }
      if (sameThread(seed, convoRef.current.messages)) return;
    }
    if (convoRef.current.pending) {
      const live = agentRef.current.turn;
      const said = live.text !== "" || live.reactions.length > 0;
      const thread = said ? [...convoRef.current.messages, foldAssistantTurn(live, authorRef.current)] : convoRef.current.messages;
      agentRef.current.abort?.();
      abandonAwaited("the conversation changed before the turn finished");
      void runPersist(thread, origin ?? void 0);
    }
    dispatch({ type: "hydrate", messages: seed });
    if (switched) agent.reset?.();
  }, [conversationId, seedVersion]);
  useEffect2(() => {
    if (controlledRef.current) return;
    if (convoRef.current.skipPersist) {
      dispatch({ type: "persist_skip_consumed" });
      return;
    }
    void runPersist(messages, hydratedFor.current ?? void 0);
  }, [messages]);
  const newConversation = useCallback(() => {
    abandonAwaited("a new conversation was started");
    dispatch({ type: "hydrate", messages: [] });
    agent.reset?.();
  }, [agent, controlled, abandonAwaited]);
  return {
    messages: externalMessages ?? messages,
    turn: agent.turn,
    author,
    isStreaming: agent.isStreaming && !timedOut,
    canSend: !agent.isStreaming,
    turnError,
    turnNotice,
    dismissNotice,
    persistError,
    retryPersist,
    dismissPersistError,
    unsentText: convo.unsent.text,
    unsentImages: convo.unsent.images,
    clearUnsent,
    send,
    sendAndAwait,
    stop: agent.abort ? stop : void 0,
    retry,
    dismissError,
    newConversation
  };
}

// src/agent/conversation-surface/components/transcript/TurnErrorBanner.tsx
import { jsx as jsx5, jsxs as jsxs5 } from "react/jsx-runtime";
var TONES = {
  error: { border: "rgba(248,113,113,0.35)", background: "rgba(248,113,113,0.08)", text: "#fca5a5" },
  info: { border: "rgba(96,165,250,0.35)", background: "rgba(96,165,250,0.08)", text: "#93c5fd" }
};
var BUTTON_STYLE = {
  padding: "0.35rem 0.75rem",
  borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.2)",
  background: "transparent",
  color: "#e2e8f0",
  fontSize: "0.8rem",
  cursor: "pointer"
};
function TurnErrorBanner({
  error,
  onRetry,
  onDismiss,
  tone = "error",
  className,
  retryLabel = "Reintentar",
  dismissLabel = "Descartar",
  retryButtonClassName,
  dismissButtonClassName
}) {
  useTouchTargetStyle();
  const colors = TONES[tone];
  return /* @__PURE__ */ jsxs5(
    "div",
    {
      role: tone === "info" ? "status" : "alert",
      className,
      style: {
        marginTop: "1rem",
        padding: "0.75rem 1rem",
        borderRadius: 10,
        border: `1px solid ${colors.border}`,
        background: colors.background,
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "0.75rem"
      },
      children: [
        /* @__PURE__ */ jsx5("span", { style: { color: colors.text, fontSize: "0.85rem", flex: 1, minWidth: 0 }, children: error.message }),
        onRetry && /* @__PURE__ */ jsx5(
          "button",
          {
            type: "button",
            onClick: onRetry,
            className: withTouchTarget(retryButtonClassName),
            style: retryButtonClassName ? void 0 : BUTTON_STYLE,
            children: retryLabel
          }
        ),
        /* @__PURE__ */ jsx5(
          "button",
          {
            type: "button",
            onClick: onDismiss,
            className: withTouchTarget(dismissButtonClassName),
            style: dismissButtonClassName ? void 0 : { ...BUTTON_STYLE, opacity: 0.7 },
            children: dismissLabel
          }
        )
      ]
    }
  );
}

// src/agent/AgentConversationSurface.tsx
import { useEffect as useEffect5, useState as useState3 } from "react";

// src/agent/conversation-surface/hooks/useComposerFocus.ts
import { useCallback as useCallback2, useEffect as useEffect3, useRef as useRef2 } from "react";
function useComposerFocus(options) {
  const { isStreaming, isTranscribing } = options;
  const inputRef = useRef2(null);
  const refocusComposer = useCallback2(() => {
    const el = inputRef.current;
    if (!el || el.disabled) return;
    const active = document.activeElement;
    const isOtherTextEntry = active instanceof HTMLElement && active !== el && (active.tagName === "INPUT" || active.tagName === "TEXTAREA" || active.isContentEditable);
    if (isOtherTextEntry) return;
    el.focus();
  }, []);
  const wasStreaming = useRef2(false);
  useEffect3(() => {
    if (wasStreaming.current && !isStreaming) refocusComposer();
    wasStreaming.current = isStreaming;
  }, [isStreaming, refocusComposer]);
  const wasTranscribing = useRef2(false);
  useEffect3(() => {
    if (wasTranscribing.current && !isTranscribing) refocusComposer();
    wasTranscribing.current = isTranscribing;
  }, [isTranscribing, refocusComposer]);
  return inputRef;
}

// src/agent/conversation-surface/hooks/useSurfaceDictation.ts
import { useRef as useRef3 } from "react";
function useSurfaceDictation(options) {
  const { voiceAdapter, input, setInput, onVoiceError } = options;
  const micAvailable = typeof voiceAdapter?.transcribe === "function";
  const baseInputRef = useRef3("");
  const dictation = useDictation(voiceAdapter, {
    onTranscriptUpdate: (full) => {
      const base = baseInputRef.current;
      setInput(base ? `${base} ${full}` : full);
    },
    onError: onVoiceError
  });
  return {
    micAvailable,
    isRecording: dictation.isRecording,
    isTranscribing: dictation.isTranscribing,
    bands: dictation.bands,
    startDictation: () => {
      baseInputRef.current = input;
      void dictation.startRecording();
    },
    stopDictation: () => void dictation.stopRecording()
  };
}

// src/agent/conversation-surface/hooks/useComposerAppend.ts
import { useEffect as useEffect4 } from "react";
function useComposerAppend(options) {
  const { composerAppend, onComposerAppendConsumed, setInput } = options;
  useEffect4(() => {
    if (!composerAppend) return;
    setInput((prev) => prev ? `${prev} ${composerAppend}` : composerAppend);
    onComposerAppendConsumed?.();
  }, [composerAppend]);
}

// src/agent/conversation-surface/hooks/useSurfaceLayout.ts
function useSurfaceLayout(layout) {
  const isMobileViewport = useMediaQuery(FI_MOBILE_QUERY);
  const contentInset = isMobileViewport ? "100%" : "calc(100% - 60px)";
  const rootStyle = layout === "contained" ? { display: "flex", flexDirection: "column", height: "100%", minHeight: 0, overflow: "hidden" } : { display: "flex", flexDirection: "column", height: "100dvh" };
  return { rootStyle, contentInset };
}

// src/agent/conversation-surface/components/transcript/TranscriptRegion.tsx
import { useStickToBottom } from "use-stick-to-bottom";

// src/agent/ScrollToBottomButton.tsx
import { ChevronDown } from "lucide-react";
import { jsx as jsx6 } from "react/jsx-runtime";
var placement = {
  position: "absolute",
  bottom: 12,
  left: "50%",
  transform: "translateX(-50%)"
};
var skin = {
  width: 32,
  height: 32,
  borderRadius: 9999,
  border: "1px solid rgba(255,255,255,0.15)",
  background: "rgba(15,23,42,0.85)",
  color: "#e2e8f0",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  cursor: "pointer",
  backdropFilter: "blur(4px)",
  WebkitBackdropFilter: "blur(4px)",
  boxShadow: "0 2px 8px rgba(0,0,0,0.35)"
};
function ScrollToBottomButton({
  onClick,
  label = "Ir al final",
  className,
  iconClassName
}) {
  useTouchTargetStyle();
  return /* @__PURE__ */ jsx6(
    "button",
    {
      type: "button",
      onClick,
      "aria-label": label,
      className: className ? `fi-scroll-to-bottom ${FI_TOUCH_TARGET_CLASS} ${className}` : `fi-scroll-to-bottom ${FI_TOUCH_TARGET_CLASS}`,
      style: className ? placement : { ...placement, ...skin },
      children: /* @__PURE__ */ jsx6(ChevronDown, { size: 16, className: iconClassName, "aria-hidden": true })
    }
  );
}

// src/agent/conversation-surface/components/transcript/TranscriptMessages.tsx
import { Fragment as Fragment2 } from "react";

// src/agent/conversation-surface/persistedTraceTurn.ts
function persistedTraceTurn(message) {
  const trace = message.trace;
  if (!trace) return null;
  const hasContent = (trace.plan?.steps.length ?? 0) > 0 || (trace.tools?.length ?? 0) > 0 || (trace.sources?.length ?? 0) > 0;
  if (!hasContent) return null;
  return {
    plan: trace.plan ?? null,
    steps: trace.tools ?? [],
    text: message.content,
    sources: trace.sources ?? [],
    reactions: message.reactions ?? [],
    meta: null,
    author: message.author ?? null,
    heartbeats: 0,
    deferred: false,
    status: "done"
  };
}

// src/agent/conversation-surface/components/transcript/TranscriptMessages.tsx
import { jsx as jsx7, jsxs as jsxs6 } from "react/jsx-runtime";
function TranscriptMessages({
  messages,
  turn,
  isStreaming,
  agentAuthor,
  userAuthor,
  showPersistedTrace,
  agentPanelProps,
  showCopyAction,
  renderHeader,
  messageLocale,
  renderBadge,
  renderActions,
  resolveBubbleClass,
  collapseUserMessages,
  collapseMaxHeight,
  showMoreLabel,
  showLessLabel,
  collapseToggleClassName
}) {
  return /* @__PURE__ */ jsxs6("div", { style: { display: "flex", flexDirection: "column", gap: "var(--fi-transcript-gap, 1rem)" }, children: [
    messages.map((m, i) => {
      const traceTurn = showPersistedTrace && m.role === "assistant" ? persistedTraceTurn(m) : null;
      return /* @__PURE__ */ jsxs6(Fragment2, { children: [
        traceTurn && /* @__PURE__ */ jsx7(AgentPanel, { turn: traceTurn, ...agentPanelProps }),
        /* @__PURE__ */ jsxs6(
          MessageBubble,
          {
            role: m.role,
            header: renderHeader ? renderHeader(m) : defaultMessageHeader(m, agentAuthor, userAuthor ?? DEFAULT_USER_AUTHOR, messageLocale),
            badge: renderBadge ? renderBadge(m) : defaultMessageBadge(m),
            actions: renderActions?.(m) ?? (showCopyAction ? /* @__PURE__ */ jsx7(CopyButton, { content: m.content }) : void 0),
            isLatest: i === messages.length - 1,
            className: resolveBubbleClass(m),
            children: [
              /* @__PURE__ */ jsx7(MessageImages, { images: m.images }),
              /* @__PURE__ */ jsx7(
                MessageContent,
                {
                  isUser: m.role === "user",
                  content: m.content,
                  collapsible: collapseUserMessages && m.role === "user",
                  collapsedMaxHeight: collapseMaxHeight,
                  showMoreLabel,
                  showLessLabel,
                  collapseToggleClassName
                }
              ),
              /* @__PURE__ */ jsx7(MessageReactions, { reactions: m.reactions })
            ]
          }
        )
      ] }, `${m.timestamp}-${i}`);
    }),
    isStreaming && /* @__PURE__ */ jsxs6("div", { style: { display: "flex", flexDirection: "column", gap: "var(--fi-transcript-gap, 1rem)" }, children: [
      /* @__PURE__ */ jsx7("div", { "data-fi-live-trace": "", style: { position: "sticky", top: 0, zIndex: 1 }, children: /* @__PURE__ */ jsx7(AgentPanel, { turn, ...agentPanelProps }) }),
      turn.text && /* @__PURE__ */ jsx7(
        MessageBubble,
        {
          role: "assistant",
          header: /* @__PURE__ */ jsx7(MessageAuthorHeader, { author: turn.author ?? agentAuthor }),
          className: resolveBubbleClass({
            role: "assistant",
            content: turn.text,
            timestamp: ""
          }),
          children: /* @__PURE__ */ jsx7(MessageContent, { isUser: false, content: turn.text, isStreaming: true })
        }
      )
    ] })
  ] });
}

// src/agent/conversation-surface/components/transcript/TranscriptRegion.tsx
import { jsx as jsx8, jsxs as jsxs7 } from "react/jsx-runtime";
function TranscriptRegion({ surface, conversation, contentInset }) {
  const {
    messages,
    turn,
    author,
    isStreaming,
    turnError,
    turnNotice,
    dismissNotice,
    retry,
    dismissError,
    persistError,
    retryPersist,
    dismissPersistError
  } = conversation;
  const {
    emptyState,
    agentPanelProps,
    renderHeader,
    renderBadge,
    renderActions,
    messageLocale,
    messageBubbleClassName,
    collapseMaxHeight,
    showMoreLabel,
    showLessLabel,
    collapseToggleClassName,
    errorClassName,
    noticeClassName,
    retryButtonClassName,
    dismissButtonClassName,
    scrollToBottomClassName,
    scrollToBottomIconClassName,
    showPersistedTrace = true,
    showCopyAction = false,
    collapseUserMessages = true,
    autoScroll = true,
    retryLabel = "Reintentar",
    dismissLabel = "Descartar",
    persistRetryLabel = "Reintentar guardar",
    scrollToBottomLabel = "Ir al final"
  } = surface;
  const resolveBubbleClass = (message) => typeof messageBubbleClassName === "function" ? messageBubbleClassName(message) : messageBubbleClassName;
  const idle = messages.length === 0 && !isStreaming && turn.status === "thinking" && !turn.plan && turn.steps.length === 0 && !turn.text;
  const stick = useStickToBottom({ initial: "instant", resize: "smooth" });
  return (
    // Relative anchor: hosts the scroll area + the floating jump-to-latest
    // button, so the button stays glued to the transcript's bottom edge.
    /* @__PURE__ */ jsxs7("div", { style: { position: "relative", flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }, children: [
      /* @__PURE__ */ jsx8(
        "div",
        {
          ref: autoScroll ? stick.scrollRef : void 0,
          className: "fi-transcript-scroll",
          style: { flex: 1, overflowY: "auto", padding: "var(--fi-transcript-pad, 1.25rem 1rem)" },
          children: /* @__PURE__ */ jsxs7(
            "div",
            {
              ref: autoScroll ? stick.contentRef : void 0,
              style: { maxWidth: contentInset, margin: "0 auto", width: "100%" },
              children: [
                idle ? emptyState : /* @__PURE__ */ jsx8(
                  TranscriptMessages,
                  {
                    messages,
                    turn,
                    agentAuthor: author,
                    isStreaming,
                    showPersistedTrace,
                    agentPanelProps,
                    showCopyAction,
                    renderHeader,
                    messageLocale,
                    renderBadge,
                    renderActions,
                    resolveBubbleClass,
                    collapseUserMessages,
                    collapseMaxHeight,
                    showMoreLabel,
                    showLessLabel,
                    collapseToggleClassName
                  }
                ),
                turnError && /* @__PURE__ */ jsx8(
                  TurnErrorBanner,
                  {
                    error: turnError,
                    onRetry: retry,
                    onDismiss: dismissError,
                    className: errorClassName,
                    retryLabel,
                    dismissLabel,
                    retryButtonClassName,
                    dismissButtonClassName
                  }
                ),
                turnNotice && !turnError && /* @__PURE__ */ jsx8(
                  TurnErrorBanner,
                  {
                    error: turnNotice,
                    tone: "info",
                    onDismiss: dismissNotice,
                    className: noticeClassName ?? errorClassName,
                    dismissLabel,
                    dismissButtonClassName
                  }
                ),
                persistError && /* @__PURE__ */ jsx8(
                  TurnErrorBanner,
                  {
                    error: persistError,
                    onRetry: retryPersist,
                    onDismiss: dismissPersistError,
                    className: errorClassName,
                    retryLabel: persistRetryLabel,
                    dismissLabel,
                    retryButtonClassName,
                    dismissButtonClassName
                  }
                )
              ]
            }
          )
        }
      ),
      autoScroll && !stick.isAtBottom && /* @__PURE__ */ jsx8(
        ScrollToBottomButton,
        {
          onClick: () => void stick.scrollToBottom(),
          label: scrollToBottomLabel,
          className: scrollToBottomClassName,
          iconClassName: scrollToBottomIconClassName
        }
      )
    ] })
  );
}

// src/agent/conversation-surface/components/composer/ComposerRegion.tsx
import { ImagePlus } from "lucide-react";

// src/agent/conversation-surface/components/composer/ComposerControls.tsx
import { Send, Loader2 as Loader22, Square } from "lucide-react";
import { Fragment as Fragment3, jsx as jsx9, jsxs as jsxs8 } from "react/jsx-runtime";
function ComposerControls({
  dictation,
  micSlotOverride,
  micSlotClassName,
  micButtonClassName,
  voiceVisualizerClassName,
  voiceVisualizerBarClassName,
  showSendButton,
  canSend,
  isStreaming,
  onSend,
  onStop,
  sendLabel = "Enviar mensaje",
  stopLabel = "Detener respuesta",
  sendButtonClassName,
  sendButtonIconClassName,
  stopButtonClassName
}) {
  useComposerActionStyle();
  const stopping = isStreaming && onStop != null;
  return /* @__PURE__ */ jsxs8(Fragment3, { children: [
    micSlotOverride == null && dictation.micAvailable && dictation.isRecording && /* @__PURE__ */ jsx9(
      AudioVisualizer,
      {
        levels: dictation.bands,
        active: dictation.isRecording,
        variant: "bars",
        label: "Nivel del micr\xF3fono",
        className: voiceVisualizerClassName,
        barClassName: voiceVisualizerBarClassName
      }
    ),
    micSlotOverride != null ? micSlotOverride : dictation.micAvailable && /* @__PURE__ */ jsx9(
      ComposerMicSlot,
      {
        available: true,
        recording: dictation.isRecording,
        busy: dictation.isTranscribing,
        onStart: dictation.startDictation,
        onStop: dictation.stopDictation,
        className: micSlotClassName,
        buttonClassName: micButtonClassName
      }
    ),
    showSendButton && // Explicit send affordance (mirrors the shell/AURITY composer). Enter
    // still sends; this is the visible button. Disabled until there's
    // trimmed text and nothing is streaming.
    //
    // While streaming, a transport that can abort turns this into a live
    // STOP button — the primary control must never be a spinner the user
    // can only watch. Without abort support it falls back to that spinner.
    /* @__PURE__ */ jsx9(
      "button",
      {
        type: "button",
        onClick: stopping ? onStop : onSend,
        disabled: stopping ? false : !canSend,
        "aria-label": stopping ? stopLabel : sendLabel,
        "data-fi-composer-send-state": stopping ? "stop" : isStreaming ? "busy" : "send",
        className: [
          FI_TOUCH_TARGET_CLASS,
          withComposerAction("primary"),
          sendButtonClassName,
          stopping ? stopButtonClassName : void 0
        ].filter(Boolean).join(" "),
        children: stopping ? /* @__PURE__ */ jsx9(Square, { className: sendButtonIconClassName, fill: "currentColor", "aria-hidden": true }) : isStreaming ? /* @__PURE__ */ jsx9(
          Loader22,
          {
            className: sendButtonIconClassName ? `${sendButtonIconClassName} animate-spin` : "animate-spin",
            "aria-hidden": true
          }
        ) : /* @__PURE__ */ jsx9(Send, { className: sendButtonIconClassName, "aria-hidden": true })
      }
    )
  ] });
}

// src/agent/conversation-surface/components/composer/NewChatButton.tsx
import { jsx as jsx10 } from "react/jsx-runtime";
function NewChatButton({ onClick, disabled, label = "New chat" }) {
  return /* @__PURE__ */ jsx10("div", { style: { display: "flex", justifyContent: "flex-end", marginBottom: "0.5rem" }, children: /* @__PURE__ */ jsx10(
    "button",
    {
      onClick,
      disabled,
      style: {
        padding: "0.35rem 0.75rem",
        borderRadius: 8,
        border: "1px solid rgba(255,255,255,0.15)",
        background: "transparent",
        color: "#94a3b8",
        fontSize: "0.8rem",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1
      },
      children: label
    }
  ) });
}

// src/agent/conversation-surface/components/composer/ComposerRegion.tsx
import { Fragment as Fragment4, jsx as jsx11, jsxs as jsxs9 } from "react/jsx-runtime";
function ComposerRegion({ surface, state, contentInset }) {
  const {
    input,
    setInput,
    onSend,
    canSend,
    inputRef,
    dictation,
    isStreaming,
    onStop,
    hasThread,
    newConversation,
    images
  } = state;
  const {
    aboveComposer,
    composerHeader,
    composerHeaderClassName,
    composerFooterStart,
    composerFooterStartClassName,
    composerBoxClassName,
    composerAreaClassName,
    composerTextareaClassName,
    composerControlsClassName,
    composerPlaceholder,
    micSlotOverride,
    micSlotClassName,
    micButtonClassName,
    voiceVisualizerClassName,
    voiceVisualizerBarClassName,
    sendButtonClassName,
    sendButtonIconClassName,
    stopButtonClassName,
    showNewChatButton = true,
    newChatLabel = "New chat",
    showSendButton = true,
    sendLabel = "Enviar mensaje",
    stopLabel = "Detener respuesta",
    attachImageLabel = "Adjuntar imagen",
    composerActions,
    composerActionsLabel,
    composerActionsMenuClassName,
    composerActionsItemClassName,
    attachImageButtonClassName,
    imageChipsClassName
  } = surface;
  const imageChips = images && images.drafts.length > 0 ? /* @__PURE__ */ jsx11(
    ComposerImageChips,
    {
      drafts: images.drafts,
      onRemove: images.remove,
      disabled: isStreaming,
      className: imageChipsClassName
    }
  ) : null;
  const imagePicker = useImagePicker((files) => void (images && images.addFiles(files)));
  const actions = [
    ...images ? [
      {
        id: "attach-image",
        label: attachImageLabel,
        icon: /* @__PURE__ */ jsx11(ImagePlus, { size: 16, "aria-hidden": true }),
        onSelect: imagePicker.open
      }
    ] : [],
    ...composerActions ?? []
  ];
  const attachButton = actions.length > 0 ? /* @__PURE__ */ jsxs9(Fragment4, { children: [
    images ? imagePicker.input : null,
    /* @__PURE__ */ jsx11(
      ComposerActions,
      {
        actions,
        disabled: isStreaming,
        label: composerActionsLabel,
        className: attachImageButtonClassName,
        menuClassName: composerActionsMenuClassName,
        itemClassName: composerActionsItemClassName
      }
    )
  ] }) : null;
  const header = imageChips || composerHeader ? /* @__PURE__ */ jsxs9(Fragment4, { children: [
    imageChips,
    composerHeader
  ] }) : void 0;
  const footerStart = attachButton || composerFooterStart ? /* @__PURE__ */ jsxs9(Fragment4, { children: [
    attachButton,
    composerFooterStart
  ] }) : void 0;
  const footer = showSendButton || micSlotOverride != null || dictation.micAvailable ? /* @__PURE__ */ jsx11(
    ComposerControls,
    {
      dictation,
      micSlotOverride,
      micSlotClassName,
      micButtonClassName,
      voiceVisualizerClassName,
      voiceVisualizerBarClassName,
      showSendButton,
      canSend,
      isStreaming,
      onSend,
      onStop,
      sendLabel,
      stopLabel,
      sendButtonClassName,
      sendButtonIconClassName,
      stopButtonClassName
    }
  ) : null;
  return /* @__PURE__ */ jsx11(
    "div",
    {
      style: {
        // The composer is the surface's bottom edge, so it is what a notched
        // phone's home indicator overlaps once the app runs full-bleed
        // (`viewport-fit=cover` / an installed standalone PWA). env() resolves
        // to 0px everywhere else, so the desktop padding is unchanged.
        paddingTop: "var(--fi-composer-bar-pt, 0.75rem)",
        paddingBottom: "calc(var(--fi-composer-bar-pb, 1.25rem) + env(safe-area-inset-bottom, 0px))",
        paddingLeft: "calc(var(--fi-composer-bar-px, 1rem) + env(safe-area-inset-left, 0px))",
        paddingRight: "calc(var(--fi-composer-bar-px, 1rem) + env(safe-area-inset-right, 0px))",
        borderTop: "1px solid rgba(255,255,255,0.06)"
      },
      children: /* @__PURE__ */ jsxs9("div", { style: { maxWidth: contentInset, margin: "0 auto", width: "100%", containerType: "inline-size", containerName: "fi-composer" }, children: [
        hasThread && showNewChatButton && /* @__PURE__ */ jsx11(NewChatButton, { onClick: newConversation, disabled: isStreaming, label: newChatLabel }),
        aboveComposer && /* @__PURE__ */ jsx11("div", { className: "fi-surface-above-composer", style: { marginBottom: "0.5rem" }, children: aboveComposer }),
        /* @__PURE__ */ jsx11(
          ComposerFrame,
          {
            className: composerBoxClassName,
            header,
            headerClassName: composerHeaderClassName,
            footerClassName: composerControlsClassName,
            footerStart,
            footerStartClassName: composerFooterStartClassName,
            footer,
            children: /* @__PURE__ */ jsx11(
              Composer,
              {
                message: input,
                loading: isStreaming,
                placeholder: composerPlaceholder,
                onMessageChange: setInput,
                onSend,
                onPaste: images ? (e) => {
                  if (images.handlePaste(e)) e.preventDefault();
                } : void 0,
                areaClassName: composerAreaClassName,
                textareaClassName: composerTextareaClassName,
                wrapperStyle: { flex: "1 1 0%", minWidth: 0 },
                textareaRef: inputRef
              }
            )
          }
        )
      ] })
    }
  );
}

// src/agent/AgentConversationSurface.tsx
import { jsx as jsx12, jsxs as jsxs10 } from "react/jsx-runtime";
function AgentConversationSurface(props) {
  const {
    conversation,
    layout = "viewport",
    voiceAdapter,
    onVoiceError,
    composerAppend,
    onComposerAppendConsumed,
    imageAttachments = false,
    maxAttachedImages,
    onImageAttachmentError
  } = props;
  const {
    messages,
    turn,
    author,
    isStreaming,
    turnError,
    turnNotice,
    dismissNotice,
    persistError,
    retryPersist,
    dismissPersistError,
    send,
    canSend,
    stop,
    retry,
    dismissError,
    newConversation,
    unsentText,
    unsentImages,
    clearUnsent
  } = conversation;
  const [input, setInput] = useState3("");
  useTouchTargetStyle();
  const { rootStyle, contentInset } = useSurfaceLayout(layout);
  useComposerAppend({ composerAppend, onComposerAppendConsumed, setInput });
  const dictation = useSurfaceDictation({ voiceAdapter, input, setInput, onVoiceError });
  const inputRef = useComposerFocus({
    isStreaming,
    isTranscribing: dictation.isTranscribing
  });
  const images = useComposerImages({
    maxImages: maxAttachedImages,
    onError: onImageAttachmentError
  });
  const restoreImages = images.restore;
  useEffect5(() => {
    if (!unsentText && !unsentImages) return;
    if (unsentText) setInput((current) => current.trim() ? current : unsentText);
    if (imageAttachments && unsentImages && unsentImages.length > 0) {
      restoreImages(unsentImages);
    }
    clearUnsent();
  }, [unsentText, unsentImages, imageAttachments, restoreImages, clearUnsent]);
  const onSend = () => {
    const t = input.trim();
    if (imageAttachments && images.encoding) return;
    const attached = imageAttachments ? images.toMessageImages() : [];
    if (!t && attached.length === 0) return;
    if (!send(t, attached.length > 0 ? attached : void 0)) return;
    setInput("");
    images.clear();
  };
  return /* @__PURE__ */ jsxs10("div", { style: rootStyle, children: [
    /* @__PURE__ */ jsx12(
      TranscriptRegion,
      {
        surface: props,
        conversation: {
          messages,
          turn,
          author,
          isStreaming,
          turnError,
          turnNotice,
          dismissNotice,
          retry,
          dismissError,
          persistError,
          retryPersist,
          dismissPersistError
        },
        contentInset
      }
    ),
    /* @__PURE__ */ jsx12(
      ComposerRegion,
      {
        surface: props,
        state: {
          input,
          setInput,
          onSend,
          canSend: (input.trim().length > 0 || imageAttachments && images.drafts.length > 0) && !(imageAttachments && images.encoding) && canSend,
          inputRef,
          dictation,
          isStreaming,
          onStop: stop,
          hasThread: messages.length > 0 || isStreaming,
          newConversation,
          images: imageAttachments ? images : null
        },
        contentInset
      }
    )
  ] });
}

// src/agent/AgentWorkspaceShell.tsx
import { useCallback as useCallback3, useEffect as useEffect6, useId, useLayoutEffect, useMemo, useRef as useRef4, useState as useState4, useInsertionEffect } from "react";
import { Menu } from "lucide-react";
import { jsx as jsx13, jsxs as jsxs11 } from "react/jsx-runtime";
var TOGGLE_STYLE_ID = "fi-aws-toggle-style";
function ensureToggleStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(TOGGLE_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = TOGGLE_STYLE_ID;
  el.textContent = `
    .fi-aws-toggle {
      display: inline-flex; align-items: center; justify-content: center;
      width: 44px; height: 44px; min-width: 44px; min-height: 44px; border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(10,14,22,0.55);
      backdrop-filter: blur(var(--glass-blur-compact, 8px));
      color: #e2e8f0; cursor: pointer; padding: 0;
      transition: background 0.15s ease, border-color 0.15s ease;
    }
    .fi-aws-toggle:hover { background: rgba(255,255,255,0.08); }
    .fi-aws-toggle:active { background: rgba(255,255,255,0.12); }
    .fi-aws-toggle:focus-visible {
      outline: 2px solid var(--fi-accent, #34d399); outline-offset: 2px;
    }
    /* The floating toggle has no header row of its own: the transcript reserves its height. */
    .fi-aws-drawer .fi-transcript-scroll {
      padding-top: calc(0.6rem + 44px + 0.5rem) !important;
    }
  `;
  document.head.appendChild(el);
}
function AgentWorkspaceShell({
  visual = "aurora",
  density = "comfortable",
  header,
  conversation,
  rail,
  footer,
  sidebar,
  responsive = false,
  mobileQuery = FI_MOBILE_QUERY,
  sidebarWidth = 280,
  toggleLabel = "Conversaciones",
  swipe = true,
  swipeEdgeSize = 24,
  className,
  style
}) {
  useDensityStyle();
  const isMobile = useMediaQuery(mobileQuery);
  const [isOpen, setIsOpen] = useState4(false);
  const panelId = useId();
  const rootRef = useRef4(null);
  const panelRef = useRef4(null);
  const toggleRef = useRef4(null);
  const hasSidebar = sidebar != null;
  const drawerMode = hasSidebar && responsive && isMobile;
  const open = useCallback3(() => setIsOpen(true), []);
  const close = useCallback3(() => setIsOpen(false), []);
  const toggle = useCallback3(() => setIsOpen((v) => !v), []);
  const numericSidebarWidth = typeof sidebarWidth === "number" ? sidebarWidth : 280;
  const dragProgress = useEdgeSwipe({
    enabled: drawerMode && swipe,
    isOpen,
    containerRef: rootRef,
    panelRef,
    onOpen: open,
    onClose: close,
    edgeSize: swipeEdgeSize,
    fallbackWidth: numericSidebarWidth
  });
  const dragging = dragProgress !== null;
  useEffect6(() => {
    if (!drawerMode && isOpen) setIsOpen(false);
  }, [drawerMode, isOpen]);
  useEffect6(() => {
    if (!drawerMode || !isOpen) return;
    const onKey = (e) => {
      if (e.key === "Escape") setIsOpen(false);
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [drawerMode, isOpen]);
  const wasOpenRef = useRef4(false);
  useLayoutEffect(() => {
    if (!drawerMode) {
      wasOpenRef.current = false;
      return;
    }
    if (isOpen && !wasOpenRef.current) {
      panelRef.current?.focus();
    } else if (!isOpen && wasOpenRef.current) {
      const active = document.activeElement;
      if (!active || active === document.body || panelRef.current?.contains(active)) {
        toggleRef.current?.focus();
      }
    }
    wasOpenRef.current = isOpen;
  }, [drawerMode, isOpen]);
  useInsertionEffect(() => {
    if (drawerMode) ensureToggleStyle();
  }, [drawerMode]);
  const api = useMemo(
    () => ({ isOpen, isMobile, open, close, toggle }),
    [isOpen, isMobile, open, close, toggle]
  );
  const sidebarNode = useMemo(
    () => typeof sidebar === "function" ? sidebar(api) : sidebar,
    [sidebar, api]
  );
  const rootStyle = {
    display: "flex",
    flexDirection: "column",
    height: "100dvh",
    minHeight: 0,
    overflow: "hidden",
    // B3-FIGLASS-MOBILE-NATIVE-1: on an installed iOS PWA running
    // `apple-mobile-web-app-status-bar-style: black-translucent`, the web view is
    // full-bleed UNDER the clock. Pad the top by the safe-area inset so the
    // content (sidebar top, header) sits below the status bar while the BACKGROUND
    // still reaches the physical top edge — the native look. box-sizing keeps the
    // padding inside the 100dvh so nothing overflows the bottom. env() resolves to
    // 0 everywhere else, so desktop and non-translucent installs are unchanged.
    boxSizing: "border-box",
    paddingTop: "env(safe-area-inset-top, 0px)"
  };
  const mainStyle = {
    display: "grid",
    gridTemplateColumns: rail ? "minmax(0, 1fr) minmax(280px, 360px)" : "minmax(0, 1fr)",
    flex: "1 1 auto",
    minHeight: 0,
    overflow: "hidden"
  };
  const conversationStyle = { minHeight: 0, overflow: "hidden" };
  const railStyle = { minHeight: 0, overflowY: "auto" };
  const rootClassName = [
    "fi-agent-workspace",
    `fi-visual-${visual}`,
    `fi-density-${density}`,
    drawerMode ? "fi-aws-drawer" : null,
    className
  ].filter(Boolean).join(" ");
  const content = /* @__PURE__ */ jsxs11(
    "div",
    {
      "data-fi-workspace": "agent",
      "data-fi-visual": visual,
      "data-fi-density": density,
      className: rootClassName,
      inert: drawerMode && isOpen ? true : void 0,
      style: hasSidebar ? { ...rootStyle, flex: 1, minWidth: 0, height: "100%", ...style } : { ...rootStyle, ...style },
      children: [
        header != null && /* @__PURE__ */ jsx13("header", { "data-fi-slot": "header", children: header }),
        /* @__PURE__ */ jsxs11("main", { "data-fi-slot": "main", style: mainStyle, children: [
          /* @__PURE__ */ jsx13("div", { "data-fi-slot": "conversation", style: conversationStyle, children: conversation }),
          rail != null && /* @__PURE__ */ jsx13("aside", { "data-fi-slot": "rail", style: railStyle, children: rail })
        ] }),
        footer != null && /* @__PURE__ */ jsx13("footer", { "data-fi-slot": "footer", children: footer })
      ]
    }
  );
  if (!hasSidebar) return content;
  const widthCss = typeof sidebarWidth === "number" ? `${sidebarWidth}px` : sidebarWidth;
  const drawerOffset = dragging ? (dragProgress - 1) * 100 : isOpen ? 0 : -100;
  const sidebarContainerStyle = drawerMode ? {
    position: "fixed",
    top: 0,
    left: 0,
    bottom: 0,
    zIndex: 50,
    width: `min(${widthCss}, 85vw)`,
    display: "flex",
    flexDirection: "column",
    transform: drawerOffset === 0 ? "translateX(0)" : `translateX(${drawerOffset}%)`,
    // While the finger drives it there is no animation — the panel IS the
    // finger. The easing only returns for the settle after release.
    transition: dragging ? "none" : "transform 0.24s ease",
    willChange: "transform",
    touchAction: "pan-y",
    containerType: "inline-size",
    containerName: "fi-sidebar",
    // The drawer owns a FULLY opaque surface: a consumer's sidebar may be a
    // translucent glass panel (fine over the static desktop rail), but as an
    // off-canvas layer even 3% translucency lets large bright conversation
    // text ghost through and the list loses contrast. Token-overridable.
    background: "var(--fi-drawer-bg, rgb(10, 14, 22))",
    boxShadow: "var(--fi-drawer-shadow, 0 0 40px rgba(0, 0, 0, 0.55))",
    // The drawer is fixed to the physical top, so its own content also needs
    // the status-bar inset when the PWA runs full-bleed (MOBILE-NATIVE-1).
    boxSizing: "border-box",
    paddingTop: "env(safe-area-inset-top, 0px)",
    paddingBottom: "env(safe-area-inset-bottom, 0px)",
    paddingLeft: "env(safe-area-inset-left, 0px)"
  } : {
    width: widthCss,
    flexShrink: 0,
    display: "flex",
    flexDirection: "column",
    containerType: "inline-size",
    containerName: "fi-sidebar",
    boxSizing: "border-box",
    paddingBottom: "env(safe-area-inset-bottom, 0px)",
    paddingLeft: "env(safe-area-inset-left, 0px)"
  };
  return /* @__PURE__ */ jsxs11(
    "div",
    {
      ref: rootRef,
      "data-fi-workspace": "agent-with-sidebar",
      "data-fi-drawer-dragging": dragging ? "" : void 0,
      style: { display: "flex", height: "100dvh", position: "relative", overflowX: "hidden" },
      children: [
        drawerMode ? /* @__PURE__ */ jsx13(
          "div",
          {
            ref: panelRef,
            id: panelId,
            "data-fi-slot": "sidebar",
            role: "dialog",
            "aria-modal": "true",
            "aria-label": toggleLabel,
            tabIndex: -1,
            style: { ...sidebarContainerStyle, outline: "none" },
            "aria-hidden": !isOpen,
            inert: !isOpen ? true : void 0,
            children: /* @__PURE__ */ jsx13("nav", { "aria-label": toggleLabel, style: { display: "contents" }, children: sidebarNode })
          }
        ) : /* @__PURE__ */ jsx13("nav", { "data-fi-slot": "sidebar", "aria-label": toggleLabel, style: sidebarContainerStyle, children: sidebarNode }),
        drawerMode && /* @__PURE__ */ jsx13(
          "div",
          {
            onClick: close,
            "aria-hidden": true,
            style: {
              position: "fixed",
              inset: 0,
              zIndex: 40,
              background: "rgba(0,0,0,0.5)",
              opacity: dragging ? dragProgress : isOpen ? 1 : 0,
              pointerEvents: isOpen && !dragging ? "auto" : "none",
              transition: dragging ? "none" : "opacity 0.24s ease"
            }
          }
        ),
        drawerMode && /* @__PURE__ */ jsx13(
          "button",
          {
            ref: toggleRef,
            type: "button",
            className: "fi-aws-toggle",
            onClick: open,
            "aria-label": toggleLabel,
            "aria-expanded": isOpen,
            "aria-controls": panelId,
            inert: isOpen ? true : void 0,
            style: {
              position: "absolute",
              // The wrapper is full-bleed (100dvh, no top inset) so a bare `top`
              // anchors to the PHYSICAL top edge — under the iOS status bar on a
              // black-translucent PWA it collides with the clock. Consume the
              // safe-area inset so the floating toggle sits below the status bar,
              // the way a flow header would. env() resolves to 0 off-device, so
              // desktop and non-translucent installs are unchanged.
              top: "calc(0.6rem + env(safe-area-inset-top, 0px))",
              left: "calc(0.6rem + env(safe-area-inset-left, 0px))",
              zIndex: 30,
              opacity: dragging ? 1 - dragProgress : isOpen ? 0 : 1,
              transition: dragging ? "none" : "opacity 0.24s ease"
            },
            children: /* @__PURE__ */ jsx13(Menu, { size: 18, "aria-hidden": true })
          }
        ),
        content
      ]
    }
  );
}

// src/agent/AgentSidebarItem.tsx
import {
  useCallback as useCallback4,
  useRef as useRef5,
  useState as useState5
} from "react";

// src/agent/sidebarItemStyle.ts
import { useInsertionEffect as useInsertionEffect2 } from "react";
var FI_SIDEBAR_ITEM_CLASS = "fi-sidebar-item";
var FI_ITEM_BODY_CLASS = "fi-sidebar-item-body";
var FI_ITEM_TITLE_CLASS = "fi-sidebar-item-title";
var FI_ITEM_SUBTITLE_CLASS = "fi-sidebar-item-subtitle";
var FI_ITEM_META_CLASS = "fi-sidebar-item-meta";
var FI_ITEM_ACTION_CLASS = "fi-item-action";
var FI_ITEM_ACTION_DANGER_CLASS = "fi-item-action--danger";
var FI_RESOURCE_RENAME_INPUT_CLASS = "fi-resource-rename-input";
var SIDEBAR_ITEM_STYLE_ID = "fi-sidebar-item-style";
var CSS = `
.${FI_SIDEBAR_ITEM_CLASS} {
  display: flex;
  align-items: flex-start;
  gap: var(--fi-item-gap, ${glassTokens.itemGap});
  padding: var(--fi-item-padding, ${glassTokens.itemPadV} ${glassTokens.itemPadH});
  border-radius: ${glassTokens.itemRadius};
  border: 1px solid transparent;
  cursor: pointer;
  outline: none;
  transition: background 0.12s ease, border-color 0.12s ease;
}
.${FI_SIDEBAR_ITEM_CLASS}:hover {
  background: var(--fi-sidebar-item-hover-bg, ${glassTokens.itemHover});
}
.${FI_SIDEBAR_ITEM_CLASS}:focus-visible {
  box-shadow: 0 0 0 2px var(--glass-chat-accent-from, ${glassTokens.accentDeep});
}
.${FI_SIDEBAR_ITEM_CLASS}.is-selected {
  background: var(--fi-sidebar-item-selected-bg, ${glassTokens.itemSelectedBg});
  border-color: var(--fi-sidebar-item-selected-border, ${glassTokens.itemSelectedBorder});
  cursor: default;
}
.${FI_SIDEBAR_ITEM_CLASS}.is-editing {
  cursor: default;
}
.${FI_ITEM_BODY_CLASS} {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.${FI_ITEM_TITLE_CLASS} {
  font-size: ${glassTokens.itemTitleSize};
  color: var(--glass-chat-text, ${glassTokens.text});
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.${FI_ITEM_SUBTITLE_CLASS} {
  font-size: ${glassTokens.itemSubtitleSize};
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.${FI_ITEM_META_CLASS} {
  font-size: ${glassTokens.itemMetaSize};
  color: var(--fi-sidebar-item-meta-color, ${glassTokens.itemMeta});
}
.${FI_ITEM_ACTION_CLASS} {
  border: none;
  background: transparent;
  color: var(--fi-sidebar-item-action-color, ${glassTokens.itemAction});
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.2rem;
  opacity: 0;
  transition: opacity 0.12s ease, color 0.12s ease;
}
.${FI_SIDEBAR_ITEM_CLASS}:hover .${FI_ITEM_ACTION_CLASS},
.${FI_ITEM_ACTION_CLASS}:focus-visible {
  opacity: 1;
}
.${FI_ITEM_ACTION_CLASS}:disabled {
  cursor: not-allowed;
  opacity: 0;
}
.${FI_ITEM_ACTION_DANGER_CLASS}:hover:not(:disabled) {
  color: var(--fi-sidebar-item-danger, ${glassTokens.danger});
}
/* Same gate as the 44px minimum: a narrow window with a mouse got 44px actions it
   could not see, and they ate the title. Sized and revealed under one query. */
@media ${FI_TOUCH_QUERY} {
  .${FI_ITEM_ACTION_CLASS} {
    opacity: 1;
  }
  /* Touch has no hover to reveal actions, so they are always visible \u2014 but
     inline they steal the row's width (3 \xD7 44px targets left a ~90px title on a
     390px phone). Wrap them to their own right-aligned line under the body
     instead: full-width readable title, intact 44px targets. */
  .${FI_SIDEBAR_ITEM_CLASS} {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .${FI_ITEM_BODY_CLASS} {
    flex: 1 1 100%;
  }
}
@container fi-sidebar (max-width: 220px) {
  .${FI_SIDEBAR_ITEM_CLASS} {
    padding: var(--fi-item-padding-compact, 0.3rem 0.4rem);
    gap: var(--fi-item-gap-compact, 0.25rem);
  }
  .${FI_ITEM_META_CLASS} {
    display: none;
  }
}
.${FI_RESOURCE_RENAME_INPUT_CLASS} {
  font-size: ${glassTokens.itemTitleSize};
  color: var(--glass-chat-text, ${glassTokens.text});
  background: var(--glass-chat-bg-mid, ${glassTokens.bgMid});
  border: 1px solid var(--glass-chat-accent-from, ${glassTokens.accentDeep});
  border-radius: 4px;
  padding: 0.1rem 0.3rem;
  width: 100%;
  outline: none;
}
`;
function ensureSidebarItemStyle() {
  ensureDensityStyle();
  if (typeof document === "undefined") return;
  if (document.getElementById(SIDEBAR_ITEM_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = SIDEBAR_ITEM_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}
function useSidebarItemStyle() {
  useInsertionEffect2(() => {
    ensureSidebarItemStyle();
  }, []);
}

// src/agent/AgentSidebarItem.tsx
import { Fragment as Fragment5, jsx as jsx14, jsxs as jsxs12 } from "react/jsx-runtime";
function joinClasses(...parts) {
  return parts.filter(Boolean).join(" ");
}
function ItemActionSlot({
  label,
  onActivate,
  disabled = false,
  danger = false,
  className,
  children
}) {
  useTouchTargetStyle();
  const cls = withTouchTarget(
    joinClasses(FI_ITEM_ACTION_CLASS, danger && FI_ITEM_ACTION_DANGER_CLASS, className)
  );
  return /* @__PURE__ */ jsx14(
    "button",
    {
      type: "button",
      className: cls,
      "aria-label": label,
      disabled,
      onClick: (e) => {
        e.stopPropagation();
        if (!disabled) onActivate();
      },
      children
    }
  );
}
function DestructiveActionSlot(props) {
  return /* @__PURE__ */ jsx14(ItemActionSlot, { ...props, danger: true });
}
function useInlineRename(value, onRename, { maxLength, emptyPolicy = "revert" } = {}) {
  const [editing, setEditing] = useState5(false);
  const [draft, setDraft] = useState5("");
  const cancelledRef = useRef5(false);
  const start = useCallback4(() => {
    cancelledRef.current = false;
    setDraft(value);
    setEditing(true);
  }, [value]);
  const cancel = useCallback4(() => {
    cancelledRef.current = true;
    setEditing(false);
  }, []);
  const commit = useCallback4(() => {
    if (cancelledRef.current) {
      cancelledRef.current = false;
      setEditing(false);
      return;
    }
    if (draft.trim() === "" && emptyPolicy === "keep") {
      setEditing(false);
      return;
    }
    onRename(draft);
    setEditing(false);
  }, [draft, emptyPolicy, onRename]);
  return {
    editing,
    draft,
    start,
    cancel,
    inputProps: {
      value: draft,
      maxLength,
      autoFocus: true,
      onChange: (e) => setDraft(e.target.value),
      onBlur: commit,
      onClick: (e) => e.stopPropagation(),
      onKeyDown: (e) => {
        e.stopPropagation();
        if (e.key === "Enter") {
          e.preventDefault();
          commit();
        } else if (e.key === "Escape") {
          e.preventDefault();
          cancel();
        }
      }
    }
  };
}
function AgentSidebarItem({
  selected,
  onSelect,
  title,
  subtitle,
  meta,
  actions,
  disabled = false,
  editing = false,
  toggleable = false,
  ariaLabel,
  className
}) {
  useSidebarItemStyle();
  const interactive = !disabled && !editing && (toggleable || !selected);
  const titleNode = typeof title === "string" ? /* @__PURE__ */ jsx14("span", { className: FI_ITEM_TITLE_CLASS, children: title }) : title;
  return /* @__PURE__ */ jsxs12(
    "div",
    {
      className: joinClasses(
        FI_SIDEBAR_ITEM_CLASS,
        selected && "is-selected",
        editing && "is-editing",
        className
      ),
      role: "button",
      tabIndex: 0,
      "aria-current": selected,
      "aria-label": ariaLabel,
      onClick: () => interactive && onSelect(),
      onKeyDown: (e) => {
        if (e.target !== e.currentTarget) return;
        if ((e.key === "Enter" || e.key === " ") && interactive) {
          e.preventDefault();
          onSelect();
        }
      },
      children: [
        /* @__PURE__ */ jsxs12("div", { className: FI_ITEM_BODY_CLASS, children: [
          titleNode,
          subtitle != null && subtitle !== "" && /* @__PURE__ */ jsx14("span", { className: FI_ITEM_SUBTITLE_CLASS, children: subtitle }),
          meta != null && meta !== "" && /* @__PURE__ */ jsx14("span", { className: FI_ITEM_META_CLASS, children: meta })
        ] }),
        actions
      ]
    }
  );
}
function EditableResourceItem({
  title,
  selected,
  onSelect,
  onRename,
  subtitle,
  meta,
  actions,
  disabled = false,
  maxLength,
  emptyPolicy,
  renameLabel,
  renameInputLabel,
  renameGlyph = "\u270E",
  ariaLabel
}) {
  const rename = useInlineRename(title, onRename, { maxLength, emptyPolicy });
  const titleNode = rename.editing ? /* @__PURE__ */ jsx14(
    "input",
    {
      className: FI_RESOURCE_RENAME_INPUT_CLASS,
      "aria-label": renameInputLabel,
      ...rename.inputProps
    }
  ) : title;
  return /* @__PURE__ */ jsx14(
    AgentSidebarItem,
    {
      selected,
      onSelect,
      disabled,
      editing: rename.editing,
      ariaLabel,
      title: titleNode,
      subtitle,
      meta,
      actions: !rename.editing && /* @__PURE__ */ jsxs12(Fragment5, { children: [
        /* @__PURE__ */ jsx14(
          ItemActionSlot,
          {
            label: renameLabel,
            disabled,
            onActivate: rename.start,
            children: renameGlyph
          }
        ),
        actions
      ] })
    }
  );
}

// src/agent/sidebarSectionStyle.ts
import { useInsertionEffect as useInsertionEffect3 } from "react";
var FI_SIDEBAR_SECTION_CLASS = "fi-sidebar-section";
var FI_SECTION_HEAD_CLASS = "fi-sidebar-section-head";
var FI_SECTION_TITLE_CLASS = "fi-sidebar-section-title";
var FI_SECTION_CARD_CLASS = "fi-sidebar-section--card";
var FI_SECTION_FOOTER_CLASS = "fi-sidebar-section-footer";
var FI_SECTION_SCROLL_CLASS = "fi-sidebar-section-scroll";
var SIDEBAR_SECTION_STYLE_ID = "fi-sidebar-section-style";
var CSS2 = `
.${FI_SIDEBAR_SECTION_CLASS} {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.${FI_SECTION_HEAD_CLASS} {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--fi-section-head-gap, 0.5rem);
  padding: var(--fi-section-head-padding, 0.8rem 0.85rem 0.5rem);
  border-bottom: var(--fi-section-head-border, none);
}
.${FI_SECTION_TITLE_CLASS} {
  font-weight: 600;
  letter-spacing: -0.01em;
  font-size: var(--fi-section-title-size, inherit);
  color: var(--fi-section-title-color, inherit);
}
.${FI_SECTION_CARD_CLASS} {
  margin: var(--fi-section-card-margin, var(--fi-sidebar-gap, 0.5rem));
  padding: var(--fi-section-card-padding, var(--fi-space-2, 0.5rem));
  border: 1px solid var(--fi-section-card-border, rgba(255, 255, 255, 0.08));
  border-radius: var(--fi-radius-section, 12px);
  background: var(--fi-section-card-bg, transparent);
}
.${FI_SECTION_FOOTER_CLASS} {
  margin-top: var(--fi-section-footer-gap, var(--fi-section-gap, 0.5rem));
  padding-top: var(--fi-section-footer-gap, var(--fi-section-gap, 0.5rem));
  border-top: 1px solid var(--fi-section-divider, rgba(255, 255, 255, 0.06));
}
.${FI_SECTION_SCROLL_CLASS} {
  min-height: 0;
  overflow-y: auto;
  /* Content-aware: the list grows by content and only scrolls past this cap.
     rem-based (NOT vh) so a short viewport never crushes a few rows into a sliver
     \u2014 the bug 30vh caused. Overridable per-section via the --fi-section-scroll-max
     var (the maxBlockSize prop sets it inline). */
  max-block-size: var(--fi-section-scroll-max, 18rem);
}
`;
function ensureSidebarSectionStyle() {
  ensureDensityStyle();
  if (typeof document === "undefined") return;
  if (document.getElementById(SIDEBAR_SECTION_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = SIDEBAR_SECTION_STYLE_ID;
  el.textContent = CSS2;
  document.head.appendChild(el);
}
function useSidebarSectionStyle() {
  useInsertionEffect3(() => {
    ensureSidebarSectionStyle();
  }, []);
}

// src/agent/AgentSidebarSection.tsx
import { jsx as jsx15, jsxs as jsxs13 } from "react/jsx-runtime";
function joinClasses2(...parts) {
  return parts.filter(Boolean).join(" ");
}
function AgentSidebarSection({
  title,
  children,
  actionSlot,
  emptyState,
  count,
  headerSlot,
  variant = "plain",
  footerSlot,
  scrollBehavior = "none",
  maxBlockSize,
  ariaLabel,
  className
}) {
  useSidebarSectionStyle();
  const titleNode = typeof title === "string" ? /* @__PURE__ */ jsx15("span", { className: FI_SECTION_TITLE_CLASS, children: title }) : title;
  const showEmpty = count === 0 && emptyState != null;
  const body = showEmpty ? emptyState : children;
  const scrollStyle = maxBlockSize != null ? {
    ["--fi-section-scroll-max"]: typeof maxBlockSize === "number" ? `${maxBlockSize}px` : maxBlockSize
  } : void 0;
  return /* @__PURE__ */ jsxs13(
    "section",
    {
      className: joinClasses2(
        FI_SIDEBAR_SECTION_CLASS,
        variant === "card" && FI_SECTION_CARD_CLASS,
        className
      ),
      "aria-label": ariaLabel,
      children: [
        headerSlot ?? /* @__PURE__ */ jsxs13("div", { className: FI_SECTION_HEAD_CLASS, children: [
          titleNode,
          actionSlot
        ] }),
        scrollBehavior === "content" && !showEmpty ? /* @__PURE__ */ jsx15("div", { className: FI_SECTION_SCROLL_CLASS, style: scrollStyle, children: body }) : body,
        footerSlot != null && /* @__PURE__ */ jsx15("div", { className: FI_SECTION_FOOTER_CLASS, children: footerSlot })
      ]
    }
  );
}

export {
  classifyTool,
  shortToolName,
  latestOpenToolIndex,
  toolVisualStatus,
  defaultAgentIcons,
  resolveIcons,
  toolIcon,
  PlanChecklist,
  StepsPanel,
  SourcesPanel,
  AgentPanel,
  DEFAULT_TURN_TIMEOUT_MS,
  useAgentConversation,
  TurnErrorBanner,
  ScrollToBottomButton,
  AgentConversationSurface,
  AgentWorkspaceShell,
  FI_SIDEBAR_ITEM_CLASS,
  FI_ITEM_TITLE_CLASS,
  FI_ITEM_SUBTITLE_CLASS,
  FI_ITEM_META_CLASS,
  FI_ITEM_ACTION_CLASS,
  FI_RESOURCE_RENAME_INPUT_CLASS,
  ensureSidebarItemStyle,
  useSidebarItemStyle,
  ItemActionSlot,
  DestructiveActionSlot,
  useInlineRename,
  AgentSidebarItem,
  EditableResourceItem,
  FI_SIDEBAR_SECTION_CLASS,
  FI_SECTION_HEAD_CLASS,
  FI_SECTION_TITLE_CLASS,
  FI_SECTION_CARD_CLASS,
  FI_SECTION_FOOTER_CLASS,
  FI_SECTION_SCROLL_CLASS,
  ensureSidebarSectionStyle,
  useSidebarSectionStyle,
  AgentSidebarSection
};
//# sourceMappingURL=chunk-EE47ROZG.js.map