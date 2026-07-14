'use client';

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
      const isPending2 = step.status === "pending";
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
          isPending2 && /* @__PURE__ */ jsx("span", { className: `${hint} text-[10px] uppercase tracking-wide`.trim(), children: "queued" }),
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
import { useCallback, useEffect as useEffect2, useRef, useState as useState2 } from "react";
import {
  makeUserMessage,
  foldAssistantTurn
} from "@free-intelligence/core";
var DEFAULT_USER_AUTHOR = { id: "user", name: "T\xFA", symbol: "T\xFA" };
var DEFAULT_PERSIST_ERROR = "No se pudo guardar esta conversaci\xF3n. Sigue en pantalla, pero podr\xEDas perderla al recargar.";
var DEFAULT_TURN_TIMEOUT_MS = 6e4;
function useAgentConversation(agent, options) {
  const {
    author,
    userAuthor = DEFAULT_USER_AUTHOR,
    externalMessages,
    conversationId,
    initialMessages,
    onMessagesChange,
    turnTimeoutMs = DEFAULT_TURN_TIMEOUT_MS,
    isAppHandledError
  } = options;
  const controlled = externalMessages !== void 0;
  const [messages, setMessages] = useState2(
    initialMessages ?? []
  );
  const controlledRef = useRef(controlled);
  controlledRef.current = controlled;
  const authorRef = useRef(author);
  authorRef.current = author;
  const userAuthorRef = useRef(userAuthor);
  userAuthorRef.current = userAuthor;
  const onMessagesChangeRef = useRef(onMessagesChange);
  onMessagesChangeRef.current = onMessagesChange;
  const [turnError, setTurnError] = useState2(null);
  const [timedOut, setTimedOut] = useState2(false);
  const [persistError, setPersistError] = useState2(null);
  const [unsentText, setUnsentText] = useState2(null);
  const unsaved = useRef(null);
  const runPersist = useCallback(async (thread) => {
    if (!onMessagesChangeRef.current) return;
    try {
      await onMessagesChangeRef.current(thread);
      unsaved.current = null;
      setPersistError(null);
    } catch (cause) {
      unsaved.current = thread;
      setPersistError({
        message: cause instanceof Error && cause.message ? cause.message : DEFAULT_PERSIST_ERROR,
        cause
      });
    }
  }, []);
  const retryPersist = useCallback(() => {
    const thread = unsaved.current;
    if (!thread) return;
    setPersistError(null);
    void runPersist(thread);
  }, [runPersist]);
  const dismissPersistError = useCallback(() => setPersistError(null), []);
  const clearUnsentText = useCallback(() => setUnsentText(null), []);
  const pending = useRef(false);
  const messagesRef = useRef(messages);
  messagesRef.current = externalMessages ?? messages;
  const agentRef = useRef(agent);
  agentRef.current = agent;
  const appHandledRef = useRef(isAppHandledError);
  appHandledRef.current = isAppHandledError;
  const lastSent = useRef(null);
  const initialRef = useRef(initialMessages);
  initialRef.current = initialMessages;
  const skipPersist = useRef(true);
  const mounted = useRef(false);
  const revertOptimistic = useCallback(() => {
    if (controlledRef.current) return;
    const thread = messagesRef.current;
    const last = thread[thread.length - 1];
    if (last?.role !== "user") return;
    setUnsentText(last.content);
    setMessages((prev) => prev[prev.length - 1]?.role === "user" ? prev.slice(0, -1) : prev);
  }, []);
  const awaitResolver = useRef(null);
  const send = useCallback(
    (text, images) => {
      const t = text.trim();
      const imgs = images && images.length > 0 ? images : void 0;
      if (!t && !imgs || agent.isStreaming) return;
      lastSent.current = { text: t, images: imgs };
      setUnsentText(null);
      setTurnError(null);
      setTimedOut(false);
      if (!controlled) {
        skipPersist.current = true;
        setMessages((prev) => [...prev, makeUserMessage(t, userAuthorRef.current, imgs)]);
      }
      pending.current = true;
      void agent.send(t, { history: messagesRef.current, ...imgs ? { images: imgs } : {} });
    },
    [agent, controlled]
  );
  const sendAndAwait = useCallback(
    (text) => {
      const t = text.trim();
      if (!t) return Promise.resolve("");
      if (agent.isStreaming) return Promise.reject(new Error("a turn is already streaming"));
      return new Promise((resolve, reject) => {
        awaitResolver.current = { resolve, reject };
        send(t);
      });
    },
    [agent.isStreaming, send]
  );
  const stop = useCallback(() => {
    if (!agentRef.current.isStreaming) return;
    agentRef.current.abort?.();
  }, []);
  const retry = useCallback(() => {
    if (lastSent.current) send(lastSent.current.text, lastSent.current.images);
  }, [send]);
  const dismissError = useCallback(() => {
    setTurnError(null);
    setTimedOut(false);
  }, []);
  useEffect2(() => {
    if (agent.isStreaming || !pending.current) return;
    pending.current = false;
    if (agent.turn.status === "error") {
      revertOptimistic();
      const r = awaitResolver.current;
      awaitResolver.current = null;
      r?.reject(new Error(agent.turn.errorMessage || "turn failed"));
      if (!appHandledRef.current?.(agent.turn)) {
        setTurnError({
          kind: "stream",
          message: agent.turn.errorMessage || "La respuesta fall\xF3. Intenta de nuevo."
        });
      }
      return;
    }
    const finalText = agent.turn.text || "";
    if (!controlledRef.current && agent.turn.text) {
      skipPersist.current = false;
      setMessages((prev) => [...prev, foldAssistantTurn(agent.turn, authorRef.current)]);
    }
    const resolver = awaitResolver.current;
    awaitResolver.current = null;
    resolver?.resolve(finalText);
  }, [agent.isStreaming, agent.turn, revertOptimistic]);
  useEffect2(() => {
    if (turnTimeoutMs <= 0) return;
    if (!agent.isStreaming || !pending.current || timedOut) return;
    const timer = setTimeout(() => {
      pending.current = false;
      agentRef.current.abort?.();
      revertOptimistic();
      const r = awaitResolver.current;
      awaitResolver.current = null;
      r?.reject(new Error("turn timed out"));
      setTimedOut(true);
      setTurnError({
        kind: "timeout",
        message: "La respuesta tard\xF3 demasiado. Intenta de nuevo."
      });
    }, turnTimeoutMs);
    return () => clearTimeout(timer);
  }, [agent.isStreaming, agent.turn, timedOut, turnTimeoutMs, revertOptimistic]);
  useEffect2(() => {
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    if (controlledRef.current) return;
    skipPersist.current = true;
    pending.current = false;
    setTurnError(null);
    setTimedOut(false);
    setMessages(initialRef.current ?? []);
    agent.reset?.();
  }, [conversationId]);
  useEffect2(() => {
    if (controlledRef.current) return;
    if (skipPersist.current) {
      skipPersist.current = false;
      return;
    }
    void runPersist(messages);
  }, [messages]);
  const newConversation = useCallback(() => {
    skipPersist.current = true;
    setTurnError(null);
    setTimedOut(false);
    if (!controlled) setMessages([]);
    pending.current = false;
    agent.reset?.();
  }, [agent, controlled]);
  return {
    messages: externalMessages ?? messages,
    turn: agent.turn,
    author,
    isStreaming: agent.isStreaming && !timedOut,
    turnError,
    persistError,
    retryPersist,
    dismissPersistError,
    unsentText,
    clearUnsentText,
    send,
    sendAndAwait,
    stop: agent.abort ? stop : void 0,
    retry,
    dismissError,
    newConversation
  };
}

// src/agent/AgentConversationSurface.tsx
import { useEffect as useEffect21, useState as useState20 } from "react";

// src/shell/touchTarget.ts
import { useEffect as useEffect3 } from "react";
var FI_TOUCH_TARGET_CLASS = "fi-touch-target";
var TOUCH_TARGET_STYLE_ID = "fi-touch-target-style";
function ensureTouchTargetStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(TOUCH_TARGET_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = TOUCH_TARGET_STYLE_ID;
  el.textContent = `
    @media (pointer: coarse), (max-width: 768px) {
      .${FI_TOUCH_TARGET_CLASS} {
        min-width: 44px;
        min-height: 44px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
      }
    }
  `;
  document.head.appendChild(el);
}
function useTouchTargetStyle() {
  useEffect3(() => {
    ensureTouchTargetStyle();
  }, []);
}
function withTouchTarget(className) {
  return className ? `${FI_TOUCH_TARGET_CLASS} ${className}` : FI_TOUCH_TARGET_CLASS;
}

// src/composer/useComposerImages.ts
import { useCallback as useCallback2, useRef as useRef2, useState as useState3 } from "react";
var COMPOSER_IMAGE_MEDIA_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif"
];
var COMPOSER_IMAGE_ACCEPT = COMPOSER_IMAGE_MEDIA_TYPES.join(",");
var DEFAULT_MAX_IMAGES = 4;
var PASSTHROUGH_BYTES = 15e5;
var MAX_SIDE_PX = 2048;
var JPEG_QUALITY = 0.85;
var MAX_ENCODED_CHARS = 4 * 1024 * 1024;
function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("read failed"));
    reader.readAsDataURL(file);
  });
}
function splitDataUrl(dataUrl) {
  const match = /^data:([^;,]+);base64,(.+)$/.exec(dataUrl);
  return match ? { mediaType: match[1], data: match[2] } : null;
}
async function downscale(file) {
  if (typeof document === "undefined" || typeof createImageBitmap !== "function") return null;
  let bitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    return null;
  }
  try {
    const scale = Math.min(1, MAX_SIDE_PX / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", JPEG_QUALITY);
  } finally {
    bitmap.close();
  }
}
var nextDraftId = 0;
function useComposerImages(options = {}) {
  const { maxImages = DEFAULT_MAX_IMAGES, onError } = options;
  const [drafts, setDrafts] = useState3([]);
  const draftsRef = useRef2(drafts);
  draftsRef.current = drafts;
  const onErrorRef = useRef2(onError);
  onErrorRef.current = onError;
  const addFiles = useCallback2(
    async (files) => {
      let count = draftsRef.current.length;
      for (const file of files) {
        if (!COMPOSER_IMAGE_MEDIA_TYPES.includes(file.type)) {
          onErrorRef.current?.(
            "Solo im\xE1genes JPEG, PNG, WebP o GIF."
          );
          continue;
        }
        if (count >= maxImages) {
          onErrorRef.current?.(`M\xE1ximo ${maxImages} im\xE1genes por mensaje.`);
          return;
        }
        let dataUrl;
        try {
          if (file.size <= PASSTHROUGH_BYTES) {
            dataUrl = await readAsDataUrl(file);
          } else {
            const scaled = await downscale(file);
            if (!scaled) {
              onErrorRef.current?.(
                `La imagen "${file.name}" es muy grande y no se pudo reducir aqu\xED. Usa una m\xE1s peque\xF1a.`
              );
              continue;
            }
            dataUrl = scaled;
          }
        } catch {
          onErrorRef.current?.(`No se pudo leer la imagen "${file.name}".`);
          continue;
        }
        const parts = splitDataUrl(dataUrl);
        if (!parts || parts.data.length > MAX_ENCODED_CHARS) {
          onErrorRef.current?.(
            `La imagen "${file.name}" sigue siendo muy pesada despu\xE9s de reducirla.`
          );
          continue;
        }
        const draft = {
          id: `img-${++nextDraftId}`,
          mediaType: parts.mediaType,
          data: parts.data,
          dataUrl,
          name: file.name || "imagen"
        };
        count += 1;
        setDrafts((prev) => prev.length >= maxImages ? prev : [...prev, draft]);
      }
    },
    [maxImages]
  );
  const remove = useCallback2((id) => {
    setDrafts((prev) => prev.filter((d) => d.id !== id));
  }, []);
  const clear = useCallback2(() => setDrafts([]), []);
  const toMessageImages = useCallback2(
    () => draftsRef.current.map((d) => ({ mediaType: d.mediaType, data: d.data })),
    []
  );
  const handlePaste = useCallback2(
    (event) => {
      const items = event.clipboardData?.items;
      if (!items) return false;
      const files = [];
      for (const item of Array.from(items)) {
        if (item.kind === "file" && item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) files.push(file);
        }
      }
      if (files.length === 0) return false;
      void addFiles(files);
      return true;
    },
    [addFiles]
  );
  return { drafts, addFiles, remove, clear, toMessageImages, handlePaste };
}

// src/agent/conversation-surface/hooks/useComposerFocus.ts
import { useCallback as useCallback3, useEffect as useEffect4, useRef as useRef3 } from "react";
function useComposerFocus(options) {
  const { isStreaming, isTranscribing } = options;
  const inputRef = useRef3(null);
  const refocusComposer = useCallback3(() => {
    const el = inputRef.current;
    if (!el || el.disabled) return;
    const active = document.activeElement;
    const isOtherTextEntry = active instanceof HTMLElement && active !== el && (active.tagName === "INPUT" || active.tagName === "TEXTAREA" || active.isContentEditable);
    if (isOtherTextEntry) return;
    el.focus();
  }, []);
  const wasStreaming = useRef3(false);
  useEffect4(() => {
    if (wasStreaming.current && !isStreaming) refocusComposer();
    wasStreaming.current = isStreaming;
  }, [isStreaming, refocusComposer]);
  const wasTranscribing = useRef3(false);
  useEffect4(() => {
    if (wasTranscribing.current && !isTranscribing) refocusComposer();
    wasTranscribing.current = isTranscribing;
  }, [isTranscribing, refocusComposer]);
  return inputRef;
}

// src/agent/conversation-surface/hooks/useSurfaceDictation.ts
import { useRef as useRef10 } from "react";

// src/voice/recording/RecordingButton.tsx
import { forwardRef } from "react";
import { Loader2 as Loader22 } from "lucide-react";

// src/voice/recording/types.ts
var BUTTON_SIZES = {
  sm: {
    button: "rec-btn-sm",
    icon: "rec-icon-sm",
    ring: "rec-ring-sm"
  },
  md: {
    button: "rec-btn-md",
    icon: "rec-icon-md",
    ring: "rec-ring-md"
  },
  lg: {
    button: "rec-btn-lg",
    icon: "rec-icon-lg",
    ring: "rec-ring-lg"
  },
  xl: {
    button: "rec-btn-xl",
    icon: "rec-icon-xl",
    ring: "rec-ring-xl"
  }
};

// src/voice/recording/RecordingButton.tsx
import { jsx as jsx5 } from "react/jsx-runtime";
var RecordingButton = forwardRef(
  function RecordingButton2({
    size = "md",
    bgColor,
    icon: Icon,
    iconSpin = false,
    iconColor = "rec-icon-white",
    disabled = false,
    onClick,
    ariaLabel,
    className = "",
    borderStyle = "",
    animate = ""
  }, ref) {
    const sizeConfig = BUTTON_SIZES[size];
    const DisplayIcon = iconSpin ? Loader22 : Icon;
    return /* @__PURE__ */ jsx5(
      "button",
      {
        ref,
        onClick,
        disabled,
        "aria-label": ariaLabel,
        className: `fi-recording-btn-base ${sizeConfig.button} ${bgColor} ${borderStyle} ${animate} ${disabled ? "rec-btn-disabled" : "rec-btn-enabled"} ${className}`,
        children: /* @__PURE__ */ jsx5(
          DisplayIcon,
          {
            className: `${sizeConfig.icon} ${iconColor} ${iconSpin ? "rec-icon-spin" : ""}`
          }
        )
      }
    );
  }
);

// src/voice/recording/PulseRings.tsx
import { motion } from "framer-motion";
import { Fragment as Fragment2, jsx as jsx6, jsxs as jsxs5 } from "react/jsx-runtime";

// src/voice/recording/RecordingTimer.tsx
import { motion as motion2 } from "framer-motion";
import { jsx as jsx7, jsxs as jsxs6 } from "react/jsx-runtime";

// src/voice/recording/StatusText.tsx
import { Loader2 as Loader23 } from "lucide-react";
import { motion as motion3 } from "framer-motion";
import { jsx as jsx8, jsxs as jsxs7 } from "react/jsx-runtime";

// src/voice/VoiceMicButton.tsx
import { Mic, Square, Loader2 as Loader24 } from "lucide-react";
import { motion as motion4 } from "framer-motion";
import { jsx as jsx9, jsxs as jsxs8 } from "react/jsx-runtime";

// src/voice/SpeakButton.tsx
import { Volume2, Loader2 as Loader25, Play } from "lucide-react";
import { jsx as jsx10 } from "react/jsx-runtime";

// src/voice/useAudioPlayer.ts
import { useEffect as useEffect5, useMemo, useRef as useRef4, useSyncExternalStore } from "react";

// src/voice/AudioPlayer.tsx
import { Play as Play2, Pause, Square as Square2, Loader2 as Loader26, AlertCircle } from "lucide-react";
import { useEffect as useEffect6 } from "react";
import { jsx as jsx11, jsxs as jsxs9 } from "react/jsx-runtime";

// src/voice/RichAudioPlayer.tsx
import {
  Play as Play3,
  Pause as Pause2,
  Square as Square3,
  Loader2 as Loader27,
  AlertCircle as AlertCircle2,
  RotateCcw,
  RotateCw
} from "lucide-react";
import { useEffect as useEffect7 } from "react";
import { jsx as jsx12, jsxs as jsxs10 } from "react/jsx-runtime";

// src/voice/AudioVisualizer.tsx
import { jsx as jsx13 } from "react/jsx-runtime";
var MIN_BAR_PCT = 4;
function normalizeLevels(levels) {
  return levels.map(
    (v) => !Number.isFinite(v) ? 0 : v < 0 ? 0 : v > 1 ? 1 : v
  );
}
function resampleLevels(levels, count) {
  if (count <= 0) return [];
  if (levels.length === 0) return new Array(count).fill(0);
  if (levels.length === count) return levels.slice();
  const out = [];
  for (let i = 0; i < count; i++) {
    const idx = Math.min(
      levels.length - 1,
      Math.floor(i / count * levels.length)
    );
    out.push(levels[idx]);
  }
  return out;
}
function AudioVisualizer({
  levels,
  variant = "bars",
  active = true,
  barCount,
  label = "Visualizador de nivel de audio",
  className,
  barClassName,
  color
}) {
  const normalized = normalizeLevels(levels);
  if (variant === "pulse") {
    const peak = active && normalized.length ? Math.max(...normalized) : 0;
    const scale = 1 + peak;
    return /* @__PURE__ */ jsx13(
      "div",
      {
        role: "img",
        "aria-label": label,
        className,
        "data-fi-audio-visualizer": "pulse",
        "data-active": active ? "" : void 0,
        children: /* @__PURE__ */ jsx13(
          "span",
          {
            "data-fi-pulse-core": "",
            style: {
              display: "inline-block",
              transform: `scale(${scale})`,
              borderColor: color
            }
          }
        )
      }
    );
  }
  const count = barCount && barCount > 0 ? barCount : normalized.length;
  const bars = resampleLevels(normalized, count);
  return /* @__PURE__ */ jsx13(
    "div",
    {
      role: "img",
      "aria-label": label,
      className,
      "data-fi-audio-visualizer": "bars",
      "data-active": active ? "" : void 0,
      style: { display: "inline-flex", alignItems: "flex-end" },
      children: bars.map((level, i) => {
        const pct = active ? Math.max(MIN_BAR_PCT, level * 100) : MIN_BAR_PCT;
        return /* @__PURE__ */ jsx13(
          "span",
          {
            "data-fi-audio-bar": "",
            className: barClassName,
            style: { height: `${pct}%`, backgroundColor: color }
          },
          i
        );
      })
    }
  );
}

// src/voice/ComposerMicSlot.tsx
import { Mic as Mic2, MicOff, Square as Square4, Loader2 as Loader28 } from "lucide-react";
import { jsx as jsx14 } from "react/jsx-runtime";
var ICON = "w-4 h-4";
var BTN = "p-2 disabled:opacity-40";
function ComposerMicSlot({
  available = false,
  recording = false,
  busy = false,
  onStart,
  onStop,
  unavailableLabel = "Dictado por voz no disponible todav\xEDa",
  startLabel = "Iniciar dictado por voz",
  stopLabel = "Detener dictado por voz",
  busyLabel = "Transcribiendo\u2026",
  className,
  buttonClassName,
  iconClassName
}) {
  useTouchTargetStyle();
  const btnClass = `${FI_TOUCH_TARGET_CLASS} ${buttonClassName ?? BTN}`;
  const iconClass = iconClassName ?? ICON;
  const disabled = !available || busy;
  const label = !available ? unavailableLabel : busy ? busyLabel : recording ? stopLabel : startLabel;
  const handleClick = () => {
    if (disabled) return;
    if (recording) onStop?.();
    else onStart?.();
  };
  const Icon = !available ? MicOff : busy ? Loader28 : recording ? Square4 : Mic2;
  return /* @__PURE__ */ jsx14("div", { className, "data-fi-mic-slot": "", "data-available": available ? "" : void 0, children: /* @__PURE__ */ jsx14(
    "button",
    {
      type: "button",
      onClick: handleClick,
      disabled,
      "aria-disabled": disabled,
      "aria-pressed": available ? recording : void 0,
      "aria-label": label,
      title: !available ? unavailableLabel : void 0,
      className: btnClass,
      children: /* @__PURE__ */ jsx14(
        Icon,
        {
          className: busy ? `${iconClass} animate-spin` : iconClass,
          "aria-hidden": true
        }
      )
    }
  ) });
}

// src/voice/useVoice.ts
import { useCallback as useCallback4, useRef as useRef5, useState as useState4 } from "react";

// src/voice/useDictation.ts
import { useCallback as useCallback6, useState as useState7 } from "react";

// src/voice/useRecorder.ts
import { useState as useState5, useRef as useRef6, useCallback as useCallback5 } from "react";

// src/voice/makeRecorder.ts
async function makeRecorder(stream, onChunk, opts) {
  const timeSlice = opts?.timeSlice;
  const channels = opts?.channels ?? 1;
  const mod = await import("recordrtc");
  const RecordRTC = mod.default ?? mod;
  if (!RecordRTC) {
    throw new Error("[makeRecorder] RecordRTC library not available");
  }
  const mimeType = "audio/wav";
  let currentRecorder = null;
  let loopTimer = null;
  let isActive = false;
  const createRecorder = () => {
    return new RecordRTC(stream, {
      type: "audio",
      recorderType: RecordRTC.StereoAudioRecorder,
      mimeType,
      numberOfAudioChannels: channels,
      desiredSampRate: opts?.sampleRate ?? 16e3,
      disableLogs: true
    });
  };
  const startLoop = async () => {
    if (!isActive) return;
    currentRecorder = createRecorder();
    currentRecorder.startRecording();
    if (timeSlice && timeSlice > 0) {
      loopTimer = setTimeout(async () => {
        if (!currentRecorder || !isActive) return;
        currentRecorder.stopRecording(() => {
          if (!isActive) return;
          const blob = currentRecorder.getBlob();
          if (blob && blob.size > 0) {
            onChunk(blob);
          }
          if (isActive) {
            startLoop();
          }
        });
      }, timeSlice);
    }
  };
  return {
    start: () => {
      isActive = true;
      startLoop();
    },
    stop: () => new Promise((resolve) => {
      isActive = false;
      if (loopTimer) {
        clearTimeout(loopTimer);
        loopTimer = null;
      }
      if (currentRecorder) {
        currentRecorder.stopRecording(() => {
          const finalBlob = currentRecorder.getBlob();
          resolve(finalBlob);
        });
      } else {
        resolve(new Blob([], { type: mimeType }));
      }
    }),
    kind: "recordrtc"
  };
}

// src/voice/useRecorder.ts
var log = {
  error: (_m, _meta) => {
    void _m;
    void _meta;
  },
  warn: (_m, _meta) => {
    void _m;
    void _meta;
  }
};
function useRecorder(config) {
  const {
    onChunk,
    onError,
    timeSlice = 3e3,
    sampleRate = 16e3,
    channels = 1,
    externalStream = null,
    deviceId = null
  } = config;
  const [isRecording, setIsRecording] = useState5(false);
  const [recordingTime, setRecordingTime] = useState5(0);
  const [fullAudioBlob, setFullAudioBlob] = useState5(null);
  const [fullAudioUrl, setFullAudioUrl] = useState5(null);
  const [currentStream, setCurrentStream] = useState5(null);
  const recorderRef = useRef6(null);
  const continuousRecorderRef = useRef6(null);
  const currentStreamRef = useRef6(null);
  const recordingTimerRef = useRef6(null);
  const fullAudioUrlRef = useRef6(null);
  const chunkNumberRef = useRef6(0);
  const startRecording = useCallback5(async () => {
    try {
      chunkNumberRef.current = 0;
      setRecordingTime(0);
      setFullAudioBlob(null);
      if (fullAudioUrlRef.current) {
        URL.revokeObjectURL(fullAudioUrlRef.current);
        fullAudioUrlRef.current = null;
        setFullAudioUrl(null);
      }
      let stream;
      if (externalStream) {
        stream = externalStream;
      } else {
        try {
          const timeoutMs = 15e3;
          const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => {
              reject(new Error(
                "Microphone permission timeout (15s). Check: 1) macOS System Preferences \u2192 Privacy \u2192 Microphone has your browser enabled, 2) Restart browser after granting permission"
              ));
            }, timeoutMs);
          });
          const audioConstraints = deviceId ? { deviceId: { exact: deviceId } } : true;
          stream = await Promise.race([
            navigator.mediaDevices.getUserMedia({ audio: audioConstraints }),
            timeoutPromise
          ]);
        } catch (micError) {
          log.error("Microphone access failed", { error: String(micError) });
          throw micError;
        }
      }
      currentStreamRef.current = stream;
      setCurrentStream(stream);
      const chunkedRecorder = await makeRecorder(
        stream,
        async (blob) => {
          const chunkNumber = chunkNumberRef.current++;
          await onChunk(blob, chunkNumber);
        },
        {
          timeSlice,
          sampleRate,
          channels
        }
      );
      recorderRef.current = chunkedRecorder;
      chunkedRecorder.start();
      const continuousRecorder = await makeRecorder(
        stream,
        () => {
        },
        // Empty callback - blob comes from .stop() return value
        {
          // NO timeSlice = records continuously until stop()
          sampleRate,
          channels
        }
      );
      continuousRecorderRef.current = continuousRecorder;
      continuousRecorder.start();
      setIsRecording(true);
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1e3);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "No se pudo acceder al micr\xF3fono. Por favor, verifica los permisos.";
      log.error("Start failed", { error: String(err) });
      if (onError) {
        onError(errorMessage);
      }
    }
  }, [onChunk, onError, timeSlice, sampleRate, channels, externalStream, deviceId]);
  const stopRecording = useCallback5(async () => {
    try {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      setIsRecording(false);
      if (currentStreamRef.current) {
        currentStreamRef.current.getTracks().forEach((track) => {
          track.stop();
        });
        currentStreamRef.current = null;
        setCurrentStream(null);
      }
      let fullBlob = null;
      if (continuousRecorderRef.current) {
        try {
          fullBlob = await continuousRecorderRef.current.stop();
          if (fullBlob && fullBlob.size > 0) {
            if (fullAudioUrlRef.current) {
              URL.revokeObjectURL(fullAudioUrlRef.current);
            }
            const audioUrl = URL.createObjectURL(fullBlob);
            fullAudioUrlRef.current = audioUrl;
            setFullAudioUrl(audioUrl);
            setFullAudioBlob(fullBlob);
          }
        } catch (err) {
          log.warn("Continuous recorder stop error (non-critical)", { error: String(err) });
        }
        continuousRecorderRef.current = null;
      }
      if (recorderRef.current) {
        try {
          const lastChunk = await recorderRef.current.stop();
          if (lastChunk && lastChunk.size > 0) {
            const finalChunkNumber = chunkNumberRef.current++;
            try {
              const result = onChunk(lastChunk, finalChunkNumber);
              if (result instanceof Promise) {
                result.catch((err) => {
                  log.error("Final chunk processing failed", { error: String(err) });
                });
              }
            } catch (err) {
              log.error("Final chunk processing failed", { error: String(err) });
            }
          }
        } catch (err) {
          log.warn("Chunked recorder stop error (non-critical)", { error: String(err) });
        }
        recorderRef.current = null;
      }
      return fullBlob;
    } catch (err) {
      log.error("Stop failed", { error: String(err) });
      if (currentStreamRef.current) {
        currentStreamRef.current.getTracks().forEach((track) => track.stop());
        currentStreamRef.current = null;
        setCurrentStream(null);
      }
      setIsRecording(false);
      if (onError) {
        onError(err instanceof Error ? err.message : "Error al detener grabaci\xF3n");
      }
      return null;
    }
  }, [onChunk, onError]);
  return {
    isRecording,
    recordingTime,
    currentStream,
    fullAudioBlob,
    fullAudioUrl,
    startRecording,
    stopRecording
  };
}

// src/voice/useAudioAnalysis.ts
import { useState as useState6, useRef as useRef7, useEffect as useEffect8 } from "react";
var AUDIO_CONFIG = { SILENCE_THRESHOLD: 2, AUDIO_GAIN: 2.5 };
function frequencyDataToBands(data, bandCount, gain) {
  if (bandCount <= 0 || data.length === 0) return new Array(Math.max(0, bandCount)).fill(0);
  const usable = Math.floor(data.length * 0.75) || data.length;
  const sliceSize = Math.max(1, Math.floor(usable / bandCount));
  const bands = new Array(bandCount);
  for (let b = 0; b < bandCount; b++) {
    const start = b * sliceSize;
    let sum = 0;
    let n = 0;
    for (let i = start; i < start + sliceSize && i < usable; i++) {
      sum += data[i];
      n++;
    }
    const avg = n ? sum / n : 0;
    const scaled = avg / 255 * gain;
    bands[b] = scaled > 1 ? 1 : scaled < 0 ? 0 : scaled;
  }
  return bands;
}
function useAudioAnalysis(stream, config) {
  const {
    silenceThreshold = AUDIO_CONFIG.SILENCE_THRESHOLD,
    gain = AUDIO_CONFIG.AUDIO_GAIN,
    isActive,
    bandCount = 24
  } = config;
  const [audioLevel, setAudioLevel] = useState6(0);
  const [bands, setBands] = useState6([]);
  const analyserRef = useRef7(null);
  const audioContextRef = useRef7(null);
  const animationFrameRef = useRef7(null);
  const isSilent = audioLevel < silenceThreshold;
  useEffect8(() => {
    if (!stream || !isActive) {
      setAudioLevel(0);
      setBands([]);
      return;
    }
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const gainNode = audioContext.createGain();
    const source = audioContext.createMediaStreamSource(stream);
    gainNode.gain.value = gain;
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;
    source.connect(gainNode);
    gainNode.connect(analyser);
    audioContextRef.current = audioContext;
    analyserRef.current = analyser;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    const updateLevel = () => {
      if (!analyserRef.current) return;
      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      setAudioLevel(average);
      setBands(frequencyDataToBands(dataArray, bandCount, gain));
      animationFrameRef.current = requestAnimationFrame(updateLevel);
    };
    updateLevel();
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [stream, isActive, gain, silenceThreshold, bandCount]);
  return { audioLevel, isSilent, bands };
}

// src/voice/useDictation.ts
function useDictation(adapter, opts = {}) {
  const { timeSliceMs = 3e4, deviceId = null, onTranscriptUpdate, onError } = opts;
  const [liveTranscript, setLiveTranscript] = useState7("");
  const [isTranscribing, setIsTranscribing] = useState7(false);
  const handleChunk = useCallback6(
    async (blob, chunkNumber) => {
      if (!adapter?.transcribe) return;
      setIsTranscribing(true);
      try {
        const { text } = await adapter.transcribe(blob, { index: chunkNumber });
        if (text) {
          setLiveTranscript((prev) => {
            const updated = prev ? `${prev} ${text}` : text;
            onTranscriptUpdate?.(updated);
            return updated;
          });
        }
      } catch (err) {
        onError?.(err instanceof Error ? err.message : "transcription failed");
      } finally {
        setIsTranscribing(false);
      }
    },
    [adapter, onTranscriptUpdate, onError]
  );
  const { isRecording, recordingTime, currentStream, startRecording, stopRecording } = useRecorder({
    onChunk: handleChunk,
    onError,
    timeSlice: timeSliceMs,
    deviceId
  });
  const { audioLevel, isSilent, bands } = useAudioAnalysis(currentStream, {
    isActive: isRecording
  });
  const start = useCallback6(async () => {
    setLiveTranscript("");
    await startRecording();
  }, [startRecording]);
  const stop = useCallback6(async () => {
    await stopRecording();
  }, [stopRecording]);
  return {
    isRecording,
    recordingTime,
    audioLevel,
    isSilent,
    bands,
    liveTranscript,
    isTranscribing,
    startRecording: start,
    stopRecording: stop
  };
}

// src/voice/audioArtifact.ts
var AUDIO_QUEUE_DEFAULTS = {
  maxItems: 10,
  maxBytes: 50 * 1024 * 1024,
  // 50 MB total queue
  maxBytesPerItem: 10 * 1024 * 1024
  // 10 MB per artifact
};

// src/voice/useAudioQueueStore.ts
import { useMemo as useMemo2 } from "react";

// src/voice/useDurableRecording.ts
import { useState as useState8, useRef as useRef8, useCallback as useCallback7, useEffect as useEffect9 } from "react";

// src/voice/useAudioQueue.ts
import { useState as useState9, useEffect as useEffect10, useCallback as useCallback8 } from "react";

// src/voice/AudioQueuePanel.tsx
import { useEffect as useEffect11, useState as useState11 } from "react";
import { Loader2 as Loader210, Trash2 as Trash22, Info } from "lucide-react";

// src/voice/AudioQueueItem.tsx
import { useState as useState10, useCallback as useCallback9 } from "react";
import {
  Mic as Mic3,
  PauseCircle,
  CheckCircle2,
  CheckCheck,
  AlertCircle as AlertCircle3,
  Loader2 as Loader29,
  Play as Play4,
  RotateCcw as RotateCcw2,
  Trash2,
  FileAudio
} from "lucide-react";
import { jsx as jsx15, jsxs as jsxs11 } from "react/jsx-runtime";

// src/voice/AudioQueuePanel.tsx
import { jsx as jsx16, jsxs as jsxs12 } from "react/jsx-runtime";

// src/voice/AudioDraftPlayer.tsx
import { useState as useState12, useEffect as useEffect12 } from "react";
import { Play as Play5, Trash2 as Trash23, Loader2 as Loader211, RotateCcw as RotateCcw3, ArrowUp } from "lucide-react";
import { jsx as jsx17, jsxs as jsxs13 } from "react/jsx-runtime";

// src/voice/useResonanceCallLoop.ts
import { useCallback as useCallback10, useEffect as useEffect13, useMemo as useMemo3, useRef as useRef9, useState as useState13 } from "react";

// src/agent/conversation-surface/hooks/useSurfaceDictation.ts
function useSurfaceDictation(options) {
  const { voiceAdapter, input, setInput, onVoiceError } = options;
  const micAvailable = typeof voiceAdapter?.transcribe === "function";
  const baseInputRef = useRef10("");
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
import { useEffect as useEffect14 } from "react";
function useComposerAppend(options) {
  const { composerAppend, onComposerAppendConsumed, setInput } = options;
  useEffect14(() => {
    if (!composerAppend) return;
    setInput((prev) => prev ? `${prev} ${composerAppend}` : composerAppend);
    onComposerAppendConsumed?.();
  }, [composerAppend]);
}

// src/shell/useMediaQuery.ts
import { useSyncExternalStore as useSyncExternalStore2 } from "react";
var mqlCache = /* @__PURE__ */ new Map();
function getMql(query, useCache = true) {
  if (typeof window === "undefined" || !("matchMedia" in window)) {
    return null;
  }
  if (useCache) {
    const cached = mqlCache.get(query);
    if (cached) return cached;
  }
  const mql = window.matchMedia(query);
  if (useCache) {
    mqlCache.set(query, mql);
  }
  return mql;
}
function useMediaQuery(query, options) {
  const ssrMatch = options?.ssrMatch ?? false;
  const useRaf = options?.useRaf ?? true;
  const cache = options?.cache ?? true;
  const mql = getMql(query, cache);
  const getSnapshot = () => mql ? mql.matches : ssrMatch;
  const getServerSnapshot = () => ssrMatch;
  const subscribe = (onStoreChange) => {
    if (!mql) return () => {
    };
    let rafId = 0;
    const handler = () => {
      if (!useRaf) {
        onStoreChange();
        return;
      }
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => onStoreChange());
    };
    const mqlAny = mql;
    if (typeof mqlAny.addEventListener === "function") {
      mqlAny.addEventListener("change", handler);
    } else if (typeof mqlAny.addListener === "function") {
      mqlAny.addListener(handler);
    }
    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      if (typeof mqlAny.removeEventListener === "function") {
        mqlAny.removeEventListener("change", handler);
      } else if (typeof mqlAny.removeListener === "function") {
        mqlAny.removeListener(handler);
      }
    };
  };
  return useSyncExternalStore2(subscribe, getSnapshot, getServerSnapshot);
}

// src/agent/conversation-surface/hooks/useSurfaceLayout.ts
function useSurfaceLayout(layout) {
  const isMobileViewport = useMediaQuery("(max-width: 768px)");
  const contentInset = isMobileViewport ? "100%" : "calc(100% - 60px)";
  const rootStyle = layout === "contained" ? { display: "flex", flexDirection: "column", height: "100%", minHeight: 0, overflow: "hidden" } : { display: "flex", flexDirection: "column", height: "100dvh" };
  return { rootStyle, contentInset };
}

// src/agent/conversation-surface/components/transcript/TranscriptRegion.tsx
import { useStickToBottom } from "use-stick-to-bottom";

// src/agent/ScrollToBottomButton.tsx
import { ChevronDown } from "lucide-react";
import { jsx as jsx18 } from "react/jsx-runtime";
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
  return /* @__PURE__ */ jsx18(
    "button",
    {
      type: "button",
      onClick,
      "aria-label": label,
      className: className ? `fi-scroll-to-bottom ${className}` : "fi-scroll-to-bottom",
      style: className ? placement : { ...placement, ...skin },
      children: /* @__PURE__ */ jsx18(ChevronDown, { size: 16, className: iconClassName, "aria-hidden": true })
    }
  );
}

// src/agent/conversation-surface/components/transcript/TranscriptMessages.tsx
import { Fragment as Fragment4 } from "react";

// src/messages/styles.ts
var messageStyles = {
  // Container
  container: {
    base: "space-y-0.5",
    padding: "px-4"
  },
  // Message row. CONV-MOBILE-RECLAIM-1: on phones (max-md) the row tightens to
  // ~10px/14px padding so content dominates the viewport; desktop keeps the
  // original 12px/16px.
  message: {
    base: "group relative py-3 px-4 -mx-4 max-md:py-2.5 max-md:px-3.5 max-md:-mx-3.5 transition-colors duration-150",
    user: "bg-transparent hover:bg-white/[0.02]",
    assistant: "bg-white/[0.02] hover:bg-white/[0.04]",
    borderRadius: "rounded-lg"
  },
  // Avatar
  avatar: {
    size: "w-6 h-6",
    base: "rounded-md flex items-center justify-center text-[10px] font-semibold flex-shrink-0",
    user: "bg-violet-600/80 text-white",
    assistant: "bg-amber-500/80 text-slate-900"
  },
  // Meta (name + time)
  meta: {
    container: "flex items-baseline gap-2",
    name: "text-[13px] font-medium text-slate-300",
    time: "text-[11px] text-slate-500 tabular-nums"
  },
  // Content. CONV-MOBILE-RECLAIM-1: phones read at 16px/1.5 (WCAG-comfortable)
  // and drop the 2rem avatar indent — the header row already attributes the
  // message, so on a 390px screen the body reclaims the full text column.
  content: {
    base: "text-[14px] leading-relaxed max-md:text-[16px] max-md:leading-[1.5]",
    user: "text-slate-200",
    assistant: "text-slate-100",
    indent: "pl-8 max-md:pl-0"
    // Align with avatar (desktop only)
  },
  // Actions toolbar
  actions: {
    container: `
      absolute top-2 right-2
      flex items-center gap-0.5
      opacity-0 group-hover:opacity-100
      transition-opacity duration-150
      bg-slate-800/95 backdrop-blur-sm rounded-md p-0.5
      border border-slate-700/50 shadow-lg
    `,
    button: {
      // B3-FIGLASS-VISUAL-1: was p-1 + w-3 (20px, slate-400) — a barely-visible
      // 12px glyph on desktop where fi-touch-target doesn't inflate it. Nudged
      // to a ~26px target with a brighter idle tint, still secondary to the text.
      base: "p-1.5 rounded transition-colors duration-150",
      idle: "hover:bg-slate-700 text-slate-300 hover:text-white",
      active: "bg-emerald-500/20 text-emerald-400",
      speaking: "bg-amber-500/20 text-amber-400"
    },
    icon: "w-3.5 h-3.5"
  },
  // Date divider
  dateDivider: {
    container: "my-4 flex items-center gap-3",
    line: "flex-1 h-px bg-gradient-to-r from-transparent via-slate-700/30 to-transparent",
    label: "px-3 py-1 text-[10px] text-slate-500 font-medium bg-slate-900/50 rounded-full"
  },
  // Typing indicator
  typing: {
    container: "flex items-center gap-2 px-4 py-2",
    dot: "w-1.5 h-1.5 bg-amber-400/80 rounded-full",
    animation: "animate-bounce"
  }
};
var markdownStyles = {
  p: "mb-3 last:mb-0",
  strong: "font-semibold text-white",
  em: "italic text-slate-300",
  code: "px-1 py-0.5 bg-slate-800/80 rounded text-amber-300/90 font-mono text-[13px]",
  pre: "my-3 p-3 bg-slate-900/80 rounded-lg border border-slate-700/30 overflow-x-auto text-[13px]",
  ul: "my-2 ml-0.5 space-y-1.5",
  ol: "my-2 ml-0.5 space-y-1.5 list-decimal list-inside",
  li: "flex gap-1.5 text-slate-200",
  bullet: "text-slate-500 select-none text-[10px] mt-1",
  h1: "text-lg font-semibold text-white mt-4 mb-2",
  h2: "text-base font-semibold text-white mt-3 mb-1.5",
  h3: "text-sm font-semibold text-slate-100 mt-2 mb-1",
  blockquote: "my-3 px-4 py-3 rounded-lg bg-white/[0.03] border border-slate-700/40 border-l-2 border-l-amber-500/60 text-slate-200 text-[13.5px]",
  // B3-FIGLASS-VISUAL-1: links were amber-400, one shade off the amber-300 of
  // inline `code` — you couldn't tell a clickable link from literal code.
  // Emerald is the chat accent and reads unmistakably as "interactive".
  link: "text-emerald-400 hover:text-emerald-300 underline underline-offset-2 transition-colors"
};

// src/messages/MessageContent.tsx
import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

// src/messages/normalizeStreamedMarkdown.ts
var FENCE_SPLIT = /(```[\s\S]*?(?:```|$))/;
var GLUED_HEADING = /([.!?:;,)\]"'»…])(#{1,6} )/g;
function normalizeStreamedMarkdown(content) {
  if (!content.includes("#")) return content;
  return content.split(FENCE_SPLIT).map(
    (segment, i) => i % 2 === 1 ? segment : segment.replace(GLUED_HEADING, "$1\n\n$2")
  ).join("");
}

// src/messages/CollapsibleText.tsx
import { useEffect as useEffect15, useId, useRef as useRef11, useState as useState14 } from "react";
import { jsx as jsx19, jsxs as jsxs14 } from "react/jsx-runtime";
var OVERFLOW_TOLERANCE_PX = 16;
function CollapsibleText({
  children,
  maxHeight = 264,
  fadeHeight = 48,
  showMoreLabel = "Mostrar m\xE1s",
  showLessLabel = "Mostrar menos",
  className,
  toggleClassName
}) {
  const contentId = useId();
  const contentRef = useRef11(null);
  const [expanded, setExpanded] = useState14(false);
  const [overflowing, setOverflowing] = useState14(false);
  useEffect15(() => {
    const el = contentRef.current;
    if (!el) return;
    const measure = () => setOverflowing(el.scrollHeight > maxHeight + OVERFLOW_TOLERANCE_PX);
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [maxHeight]);
  const clamped = overflowing && !expanded;
  const mask = `linear-gradient(rgb(0,0,0) calc(100% - ${fadeHeight}px), transparent)`;
  return /* @__PURE__ */ jsxs14("div", { className, children: [
    /* @__PURE__ */ jsx19(
      "div",
      {
        id: contentId,
        ref: contentRef,
        style: clamped ? {
          maxHeight,
          overflow: "hidden",
          maskImage: mask,
          WebkitMaskImage: mask
        } : void 0,
        children
      }
    ),
    overflowing && /* @__PURE__ */ jsx19(
      "button",
      {
        type: "button",
        "aria-expanded": expanded,
        "aria-controls": contentId,
        onClick: () => setExpanded((e) => !e),
        className: toggleClassName,
        style: toggleClassName ? void 0 : {
          marginTop: "0.25rem",
          padding: 0,
          border: "none",
          background: "transparent",
          color: "#94a3b8",
          fontSize: "0.8rem",
          cursor: "pointer",
          textDecoration: "underline",
          textUnderlineOffset: 2
        },
        children: expanded ? showLessLabel : showMoreLabel
      }
    )
  ] });
}

// src/messages/MessageContent.tsx
import { jsx as jsx20, jsxs as jsxs15 } from "react/jsx-runtime";
var mdComponents = {
  p: ({ children }) => /* @__PURE__ */ jsx20("p", { className: markdownStyles.p, children }),
  strong: ({ children }) => /* @__PURE__ */ jsx20("strong", { className: markdownStyles.strong, children }),
  em: ({ children }) => /* @__PURE__ */ jsx20("em", { className: markdownStyles.em, children }),
  code: ({ children }) => /* @__PURE__ */ jsx20("code", { className: markdownStyles.code, children }),
  pre: ({ children }) => /* @__PURE__ */ jsx20("pre", { className: markdownStyles.pre, children }),
  ul: ({ children }) => /* @__PURE__ */ jsx20("ul", { className: markdownStyles.ul, children }),
  ol: ({ children }) => /* @__PURE__ */ jsx20("ol", { className: markdownStyles.ol, children }),
  li: ({ children }) => /* @__PURE__ */ jsxs15("li", { className: markdownStyles.li, children: [
    /* @__PURE__ */ jsx20("span", { className: markdownStyles.bullet, children: "\u2022" }),
    /* @__PURE__ */ jsx20("span", { className: "flex-1", children })
  ] }),
  h1: ({ children }) => /* @__PURE__ */ jsx20("h1", { className: markdownStyles.h1, children }),
  h2: ({ children }) => /* @__PURE__ */ jsx20("h2", { className: markdownStyles.h2, children }),
  h3: ({ children }) => /* @__PURE__ */ jsx20("h3", { className: markdownStyles.h3, children }),
  blockquote: ({ children }) => /* @__PURE__ */ jsx20("blockquote", { className: markdownStyles.blockquote, children }),
  a: ({ href, children }) => /* @__PURE__ */ jsx20("a", { href, className: markdownStyles.link, target: "_blank", rel: "noopener noreferrer", children })
};
function defaultRenderMarkdown(content) {
  return /* @__PURE__ */ jsx20(ReactMarkdown, { remarkPlugins: [remarkGfm, remarkBreaks], components: mdComponents, children: normalizeStreamedMarkdown(content) });
}
var MessageContent = memo(function MessageContent2({
  isUser,
  content,
  isStreaming = false,
  renderMarkdown = defaultRenderMarkdown,
  collapsible = false,
  collapsedMaxHeight,
  showMoreLabel,
  showLessLabel,
  collapseToggleClassName
}) {
  const { content: styles } = messageStyles;
  const body = isUser ? (
    // User: plain text, preserve whitespace
    /* @__PURE__ */ jsx20("p", { className: "whitespace-pre-wrap", children: content })
  ) : (
    // Assistant: markdown (overridable)
    renderMarkdown(content)
  );
  return /* @__PURE__ */ jsxs15(
    "div",
    {
      className: `${styles.base} ${isUser ? styles.user : styles.assistant} ${styles.indent}`,
      children: [
        collapsible && !isStreaming ? /* @__PURE__ */ jsx20(
          CollapsibleText,
          {
            maxHeight: collapsedMaxHeight,
            showMoreLabel,
            showLessLabel,
            toggleClassName: collapseToggleClassName,
            children: body
          }
        ) : body,
        isStreaming && /* @__PURE__ */ jsx20("span", { className: "inline-block w-1.5 h-4 bg-amber-400/80 ml-0.5 animate-pulse rounded-sm" })
      ]
    }
  );
});

// src/messages/CopyButton.tsx
import { memo as memo2, useCallback as useCallback11, useState as useState15 } from "react";
import { Copy, Check } from "lucide-react";
import { jsx as jsx21 } from "react/jsx-runtime";
var CopyButton = memo2(function CopyButton2({
  content,
  onError,
  className,
  idleClassName,
  activeClassName,
  iconClassName,
  copyLabel = "Copiar",
  copiedLabel = "Copiado",
  resetMs = 2e3
}) {
  const [copied, setCopied] = useState15(false);
  useTouchTargetStyle();
  const { actions } = messageStyles;
  const base = className ?? actions.button.base;
  const idle = idleClassName ?? actions.button.idle;
  const active = activeClassName ?? actions.button.active;
  const icon = iconClassName ?? actions.icon;
  const handleCopy = useCallback11(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), resetMs);
    } catch (err) {
      onError?.(err);
    }
  }, [content, onError, resetMs]);
  return /* @__PURE__ */ jsx21(
    "button",
    {
      onClick: handleCopy,
      className: `${FI_TOUCH_TARGET_CLASS} ${base} ${copied ? active : idle}`,
      title: copied ? copiedLabel : copyLabel,
      "aria-label": copied ? copiedLabel : `${copyLabel} mensaje`,
      children: copied ? /* @__PURE__ */ jsx21(Check, { className: icon }) : /* @__PURE__ */ jsx21(Copy, { className: icon })
    }
  );
});

// src/messages/MessageBubble.tsx
import { memo as memo3, useEffect as useEffect17, useRef as useRef12, useState as useState16 } from "react";

// src/messages/messageActionsStyle.ts
import { useEffect as useEffect16 } from "react";
var FI_MSG_ACTIONS_CLASS = "fi-msg-actions";
var MESSAGE_ACTIONS_STYLE_ID = "fi-msg-actions-style";
var CSS = `
.${FI_MSG_ACTIONS_CLASS} {
  margin-top: 0.25rem;
}
@media (hover: hover) and (pointer: fine) {
  .${FI_MSG_ACTIONS_CLASS} {
    opacity: 0;
    transition: opacity 0.15s ease;
  }
  article:hover > .${FI_MSG_ACTIONS_CLASS},
  .${FI_MSG_ACTIONS_CLASS}:focus-within {
    opacity: 1;
  }
}
@media (pointer: coarse) {
  .${FI_MSG_ACTIONS_CLASS} {
    display: none;
  }
  article[data-fi-last-message] > .${FI_MSG_ACTIONS_CLASS},
  article[data-fi-actions-open] > .${FI_MSG_ACTIONS_CLASS} {
    display: block;
  }
}
`;
function ensureMessageActionsStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(MESSAGE_ACTIONS_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = MESSAGE_ACTIONS_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}
function useMessageActionsStyle() {
  useEffect16(() => {
    ensureMessageActionsStyle();
  }, []);
}

// src/messages/MessageBubble.tsx
import { jsx as jsx22, jsxs as jsxs16 } from "react/jsx-runtime";
var ACTIONS_OPEN_EVENT = "fi-msg-actions-open";
var MessageBubble = memo3(function MessageBubble2({
  role,
  children,
  header,
  reasoning,
  badge,
  actions,
  isLatest = false,
  className,
  ariaLabel
}) {
  useMessageActionsStyle();
  const { message: styles } = messageStyles;
  const isUser = role === "user";
  const [actionsOpen, setActionsOpen] = useState16(false);
  const selfToken = useRef12({});
  useEffect17(() => {
    if (!actionsOpen) return;
    const onOtherOpen = (e) => {
      if (e.detail !== selfToken.current) setActionsOpen(false);
    };
    document.addEventListener(ACTIONS_OPEN_EVENT, onOtherOpen);
    return () => document.removeEventListener(ACTIONS_OPEN_EVENT, onOtherOpen);
  }, [actionsOpen]);
  const onBubbleClick = (e) => {
    if (!actions) return;
    if (e.target.closest('a, button, input, textarea, [role="button"]')) return;
    const next = !actionsOpen;
    setActionsOpen(next);
    if (next) {
      document.dispatchEvent(
        new CustomEvent(ACTIONS_OPEN_EVENT, { detail: selfToken.current })
      );
    }
  };
  return /* @__PURE__ */ jsxs16(
    "article",
    {
      className: `fi-msg-appear ${styles.base} ${styles.borderRadius} ${isUser ? styles.user : styles.assistant} ${className || ""}`,
      role: "article",
      "aria-label": ariaLabel,
      "data-fi-last-message": isLatest || void 0,
      "data-fi-actions-open": actionsOpen || void 0,
      onClick: onBubbleClick,
      children: [
        header && /* @__PURE__ */ jsx22("div", { className: "flex items-center gap-1.5 mb-0.5", children: header }),
        reasoning && /* @__PURE__ */ jsx22("div", { className: "mt-3 mb-3", children: reasoning }),
        children,
        badge && /* @__PURE__ */ jsx22("div", { className: "mt-2", children: badge }),
        actions != null && actions !== false && /* @__PURE__ */ jsx22("div", { className: FI_MSG_ACTIONS_CLASS, children: actions })
      ]
    }
  );
});

// src/messages/MessageImages.tsx
import { jsx as jsx23 } from "react/jsx-runtime";
function MessageImages({
  images,
  className,
  imageClassName,
  altLabel = "Imagen adjunta"
}) {
  if (!images || images.length === 0) return null;
  return /* @__PURE__ */ jsx23(
    "div",
    {
      className,
      "data-fi-message-images": "",
      style: { display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.5rem" },
      children: images.map((img, i) => /* @__PURE__ */ jsx23(
        "img",
        {
          src: `data:${img.mediaType};base64,${img.data}`,
          alt: `${altLabel} ${i + 1}`,
          loading: "lazy",
          style: {
            maxWidth: "min(100%, 20rem)",
            maxHeight: "20rem",
            borderRadius: "0.75rem",
            display: "block",
            objectFit: "contain"
          },
          className: imageClassName
        },
        i
      ))
    }
  );
}

// src/messages/MessageAuthorHeader.tsx
import { Fragment as Fragment3, jsx as jsx24, jsxs as jsxs17 } from "react/jsx-runtime";
var AVATAR = {
  width: 22,
  height: 22,
  borderRadius: 6,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: 10,
  fontWeight: 600,
  flexShrink: 0
};
function avatarToken(author) {
  const symbol = author.symbol?.trim();
  if (symbol) return symbol;
  return author.name.trim().slice(0, 2) || "?";
}
function formatTime(iso, locale) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
}
function MessageAuthorHeader({
  author,
  timestamp,
  isUser = false,
  locale
}) {
  const time = formatTime(timestamp, locale);
  return /* @__PURE__ */ jsxs17(Fragment3, { children: [
    /* @__PURE__ */ jsx24(
      "span",
      {
        "aria-hidden": true,
        "data-fi-author-avatar": "",
        style: {
          ...AVATAR,
          background: isUser ? "var(--fi-author-user-bg, rgba(124,58,237,0.8))" : "var(--fi-author-agent-bg, var(--og-accent, #34d399))",
          color: isUser ? "var(--fi-author-user-fg, #fff)" : "var(--fi-author-agent-fg, #0a0f1e)"
        },
        children: avatarToken(author)
      }
    ),
    /* @__PURE__ */ jsx24("span", { "data-fi-author-name": "", style: { fontSize: 13, fontWeight: 500, color: "#cbd5e1" }, children: author.name }),
    author.engine && /* @__PURE__ */ jsx24(
      "span",
      {
        "data-fi-author-engine": "",
        style: {
          fontSize: 11,
          padding: "1px 6px",
          borderRadius: 9999,
          border: "1px solid rgba(255,255,255,0.12)",
          color: "#94a3b8"
        },
        children: author.engine
      }
    ),
    time && /* @__PURE__ */ jsx24("span", { style: { fontSize: 11, color: "#64748b", fontVariantNumeric: "tabular-nums" }, children: time })
  ] });
}
function defaultMessageHeader(message, agentAuthor, userAuthor, locale) {
  const isUser = message.role === "user";
  const author = message.author ?? (isUser ? userAuthor : agentAuthor);
  return /* @__PURE__ */ jsx24(
    MessageAuthorHeader,
    {
      author,
      timestamp: message.timestamp,
      isUser,
      locale
    }
  );
}

// src/messages/MessageModelBadge.tsx
import { jsx as jsx25, jsxs as jsxs18 } from "react/jsx-runtime";
function MessageModelBadge({
  model,
  title = "Generado por {model}",
  label = "Powered by"
}) {
  return /* @__PURE__ */ jsxs18(
    "span",
    {
      "data-fi-model-badge": "",
      title: title.replace("{model}", model),
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "2px 8px",
        borderRadius: 9999,
        border: "1px solid rgba(255,255,255,0.1)",
        background: "rgba(15,23,42,0.5)",
        fontSize: 11,
        color: "#94a3b8"
      },
      children: [
        label,
        " ",
        /* @__PURE__ */ jsx25("span", { style: { color: "var(--fi-accent, var(--og-accent, #34d399))" }, children: model })
      ]
    }
  );
}
function defaultMessageBadge(message) {
  if (message.role !== "assistant") return void 0;
  const model = message.trace?.model?.trim();
  if (!model) return void 0;
  return /* @__PURE__ */ jsx25(MessageModelBadge, { model });
}

// src/messages/MessageList.tsx
import { jsx as jsx26, jsxs as jsxs19 } from "react/jsx-runtime";

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
    meta: null,
    author: message.author ?? null,
    heartbeats: 0,
    status: "done"
  };
}

// src/agent/conversation-surface/components/transcript/TranscriptMessages.tsx
import { jsx as jsx27, jsxs as jsxs20 } from "react/jsx-runtime";
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
  renderBadge,
  renderActions,
  resolveBubbleClass,
  collapseUserMessages,
  collapseMaxHeight,
  showMoreLabel,
  showLessLabel,
  collapseToggleClassName
}) {
  return /* @__PURE__ */ jsxs20("div", { style: { display: "flex", flexDirection: "column", gap: "var(--fi-transcript-gap, 1rem)" }, children: [
    messages.map((m, i) => {
      const traceTurn = showPersistedTrace && m.role === "assistant" ? persistedTraceTurn(m) : null;
      return /* @__PURE__ */ jsxs20(Fragment4, { children: [
        traceTurn && /* @__PURE__ */ jsx27(AgentPanel, { turn: traceTurn, ...agentPanelProps }),
        /* @__PURE__ */ jsxs20(
          MessageBubble,
          {
            role: m.role,
            header: renderHeader ? renderHeader(m) : defaultMessageHeader(m, agentAuthor, userAuthor ?? DEFAULT_USER_AUTHOR),
            badge: renderBadge ? renderBadge(m) : defaultMessageBadge(m),
            actions: renderActions?.(m) ?? (showCopyAction ? /* @__PURE__ */ jsx27(CopyButton, { content: m.content }) : void 0),
            isLatest: i === messages.length - 1,
            className: resolveBubbleClass(m),
            children: [
              /* @__PURE__ */ jsx27(MessageImages, { images: m.images }),
              /* @__PURE__ */ jsx27(
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
              )
            ]
          }
        )
      ] }, `${m.timestamp}-${i}`);
    }),
    isStreaming && /* @__PURE__ */ jsxs20("div", { style: { display: "flex", flexDirection: "column", gap: "var(--fi-transcript-gap, 1rem)" }, children: [
      /* @__PURE__ */ jsx27("div", { "data-fi-live-trace": "", style: { position: "sticky", top: 0, zIndex: 1 }, children: /* @__PURE__ */ jsx27(AgentPanel, { turn, ...agentPanelProps }) }),
      turn.text && /* @__PURE__ */ jsx27(
        MessageBubble,
        {
          role: "assistant",
          header: /* @__PURE__ */ jsx27(MessageAuthorHeader, { author: turn.author ?? agentAuthor }),
          className: resolveBubbleClass({
            role: "assistant",
            content: turn.text,
            timestamp: ""
          }),
          children: /* @__PURE__ */ jsx27(MessageContent, { isUser: false, content: turn.text, isStreaming: true })
        }
      )
    ] })
  ] });
}

// src/agent/conversation-surface/components/transcript/TurnErrorBanner.tsx
import { jsx as jsx28, jsxs as jsxs21 } from "react/jsx-runtime";
function TurnErrorBanner({
  error,
  onRetry,
  onDismiss,
  className,
  retryLabel = "Reintentar",
  dismissLabel = "Descartar",
  retryButtonClassName,
  dismissButtonClassName
}) {
  return /* @__PURE__ */ jsxs21(
    "div",
    {
      role: "alert",
      className,
      style: {
        marginTop: "1rem",
        padding: "0.75rem 1rem",
        borderRadius: 10,
        border: "1px solid rgba(248,113,113,0.35)",
        background: "rgba(248,113,113,0.08)",
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "0.75rem"
      },
      children: [
        /* @__PURE__ */ jsx28("span", { style: { color: "#fca5a5", fontSize: "0.85rem", flex: 1, minWidth: 0 }, children: error.message }),
        /* @__PURE__ */ jsx28(
          "button",
          {
            type: "button",
            onClick: onRetry,
            className: retryButtonClassName,
            style: retryButtonClassName ? void 0 : {
              padding: "0.35rem 0.75rem",
              borderRadius: 8,
              border: "1px solid rgba(255,255,255,0.2)",
              background: "transparent",
              color: "#e2e8f0",
              fontSize: "0.8rem",
              cursor: "pointer"
            },
            children: retryLabel
          }
        ),
        /* @__PURE__ */ jsx28(
          "button",
          {
            type: "button",
            onClick: onDismiss,
            className: dismissButtonClassName,
            style: dismissButtonClassName ? void 0 : {
              padding: "0.35rem 0.75rem",
              borderRadius: 8,
              border: "none",
              background: "transparent",
              color: "#94a3b8",
              fontSize: "0.8rem",
              cursor: "pointer"
            },
            children: dismissLabel
          }
        )
      ]
    }
  );
}

// src/agent/conversation-surface/components/transcript/TranscriptRegion.tsx
import { jsx as jsx29, jsxs as jsxs22 } from "react/jsx-runtime";
function TranscriptRegion({ surface, conversation, contentInset }) {
  const {
    messages,
    turn,
    author,
    isStreaming,
    turnError,
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
    messageBubbleClassName,
    collapseMaxHeight,
    showMoreLabel,
    showLessLabel,
    collapseToggleClassName,
    errorClassName,
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
    /* @__PURE__ */ jsxs22("div", { style: { position: "relative", flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }, children: [
      /* @__PURE__ */ jsx29(
        "div",
        {
          ref: autoScroll ? stick.scrollRef : void 0,
          style: { flex: 1, overflowY: "auto", padding: "var(--fi-transcript-pad, 1.25rem 1rem)" },
          children: /* @__PURE__ */ jsxs22(
            "div",
            {
              ref: autoScroll ? stick.contentRef : void 0,
              style: { maxWidth: contentInset, margin: "0 auto", width: "100%" },
              children: [
                idle ? emptyState : /* @__PURE__ */ jsx29(
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
                turnError && /* @__PURE__ */ jsx29(
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
                persistError && /* @__PURE__ */ jsx29(
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
      autoScroll && !stick.isAtBottom && /* @__PURE__ */ jsx29(
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

// src/composer/AutoResizeTextarea.tsx
import {
  forwardRef as forwardRef2,
  useEffect as useEffect18,
  useId as useId2,
  useImperativeHandle,
  useRef as useRef13,
  useState as useState17
} from "react";
import { jsx as jsx30, jsxs as jsxs23 } from "react/jsx-runtime";
var AutoResizeTextarea = forwardRef2(function AutoResizeTextarea2({
  value,
  onChange,
  maxRows = 5,
  showCounter = false,
  maxLength,
  wrapperClassName = "",
  wrapperStyle,
  className = "",
  id,
  name,
  ...props
}, ref) {
  const textareaRef = useRef13(null);
  useImperativeHandle(ref, () => textareaRef.current);
  const [rows, setRows] = useState17(1);
  const generatedId = useId2();
  const resolvedId = id ?? `fi-glass-composer-${generatedId}`;
  const resolvedName = name ?? resolvedId;
  useEffect18(() => {
    if (!textareaRef.current) return;
    const textarea = textareaRef.current;
    textarea.rows = 1;
    textarea.style.height = "auto";
    const computed = window.getComputedStyle(textarea);
    const parsed = parseFloat(computed.lineHeight);
    const lineHeight = Number.isFinite(parsed) && parsed > 0 ? parsed : 20;
    const newRows = value === "" ? 1 : Math.max(1, Math.min(Math.ceil(textarea.scrollHeight / lineHeight), maxRows));
    setRows(newRows);
    textarea.rows = newRows;
    textarea.style.height = `${newRows * lineHeight}px`;
    textarea.style.width = "100%";
  }, [value, maxRows]);
  const charCount = typeof value === "string" ? value.length : 0;
  const isNearLimit = maxLength && charCount > maxLength * 0.9;
  const isOverLimit = maxLength && charCount > maxLength;
  return /* @__PURE__ */ jsxs23("div", { className: `relative ${wrapperClassName}`, style: wrapperStyle, children: [
    /* @__PURE__ */ jsx30(
      "textarea",
      {
        ref: textareaRef,
        id: resolvedId,
        name: resolvedName,
        value,
        onChange,
        maxLength,
        className: `
          resize-none
          ${className}
        `,
        rows,
        ...props
      }
    ),
    showCounter && maxLength && /* @__PURE__ */ jsxs23("div", { className: isOverLimit ? "chat-char-counter-error" : isNearLimit ? "chat-char-counter-warning" : "chat-char-counter-ok", children: [
      charCount,
      "/",
      maxLength
    ] })
  ] });
});

// src/composer/Composer.tsx
import { jsx as jsx31 } from "react/jsx-runtime";
function Composer({
  message,
  loading = false,
  disabled = false,
  placeholder = "Escribe tu mensaje...",
  onMessageChange,
  onSend,
  onPaste,
  maxRows = 5,
  areaClassName,
  wrapperClassName,
  wrapperStyle,
  textareaClassName,
  id,
  name,
  textareaRef
}) {
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (loading || disabled) return;
      onSend();
    }
  };
  return /* @__PURE__ */ jsx31("div", { className: areaClassName, children: /* @__PURE__ */ jsx31(
    AutoResizeTextarea,
    {
      ref: textareaRef,
      id,
      name,
      value: message,
      onChange: (e) => onMessageChange(e.target.value),
      onKeyDown: handleKeyDown,
      onPaste,
      placeholder,
      disabled,
      maxRows,
      showCounter: false,
      wrapperClassName,
      wrapperStyle,
      className: textareaClassName
    }
  ) });
}

// src/composer/ComposerFrame.tsx
import { useEffect as useEffect19, useId as useId3, useState as useState18 } from "react";
import { SlidersHorizontal } from "lucide-react";
import { Fragment as Fragment5, jsx as jsx32, jsxs as jsxs24 } from "react/jsx-runtime";
var COMPOSER_FRAME_STYLE_ID = "fi-composer-frame-style";
var CSS2 = `
[data-fi-composer-slot="header"] {
  margin-bottom: var(--fi-space-2, 0.5rem);
}
[data-fi-composer-slot="footer"] {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--fi-space-2, 0.5rem);
}
[data-fi-composer-slot="footer-start"] {
  display: flex;
  align-items: center;
  gap: var(--fi-space-2, 0.5rem);
  min-width: 0;
  margin-right: auto;
}
/* A consumer's aboveComposer is usually a fragment of conditional banners, so it
 * is ALWAYS truthy and its wrapper mounts even with nothing inside \u2014 leaving a
 * ghost row of margin above the box. Collapse it when it renders empty. */
.fi-surface-above-composer:empty {
  display: none;
}
/* CONV-MOBILE-RECLAIM-1 \u2014 compact composer on narrow containers.
 *
 * Wide (desktop) is byte-identical: the rail toggle stays display:none and the
 * body/footer keep their stacked anatomy. At <=420px container width the frame
 * becomes ONE wrapping flex row \u2014 [toggle] [textarea] [mic] [send] \u2014 and the
 * footer-start rail (persona chip, call, attach) collapses behind the toggle,
 * expanding as its own full-width row under the input. Send stays the single
 * always-visible primary action; the textarea still grows to maxRows. */
.fi-composer-rail-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--fi-sidebar-item-action-color, #64748b);
  cursor: pointer;
  padding: 0;
  border-radius: 8px;
}
.fi-composer-rail-toggle[aria-expanded="true"] {
  color: var(--glass-chat-accent-text, #6ee7b7);
  background: rgba(255, 255, 255, 0.06);
}
@container fi-composer (max-width: 420px) {
  [data-fi-composer-frame] {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 0.375rem;
  }
  [data-fi-composer-slot="header"] {
    flex: 1 1 100%;
    order: -2;
    margin-bottom: 0;
  }
  [data-fi-composer-slot="footer"] {
    display: contents;
  }
  /* The body (whatever wrapper the consumer's Composer renders) becomes the
     row's flexing member so the textarea shares the line with toggle/mic/send. */
  [data-fi-composer-frame] > :not([data-fi-composer-slot]) {
    flex: 1 1 0%;
    min-width: 0;
  }
  .fi-composer-rail-toggle {
    display: inline-flex;
    order: -1;
  }
  [data-fi-composer-slot="footer-start"] {
    flex: 1 1 100%;
    order: 5;
    flex-wrap: wrap;
    margin-right: 0;
  }
  [data-fi-composer-frame][data-fi-rail="closed"] [data-fi-composer-slot="footer-start"] {
    display: none;
  }
  /* A control marked data-fi-rail-keep survives the collapse \u2014 the contract for
     "this is live and the user must keep reaching it" (e.g. the hang-up button
     of an ACTIVE voice call). The closed rail then stays rendered inline on the
     input row but shows ONLY the kept controls. */
  [data-fi-composer-frame][data-fi-rail="closed"] [data-fi-composer-slot="footer-start"]:has([data-fi-rail-keep]) {
    display: flex;
    flex: 0 0 auto;
    order: 0;
    margin-right: 0;
  }
  /* !important on purpose: slotted controls (e.g. ComposerActions' trigger)
     carry inline display styles that outrank any selector \u2014 and the collapse
     contract must win over a control's own presentation. */
  [data-fi-composer-frame][data-fi-rail="closed"] [data-fi-composer-slot="footer-start"]:has([data-fi-rail-keep]) > :not([data-fi-rail-keep]) {
    display: none !important;
  }
}
`;
function ensureComposerFrameStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(COMPOSER_FRAME_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = COMPOSER_FRAME_STYLE_ID;
  el.textContent = CSS2;
  document.head.appendChild(el);
}
function useComposerFrameStyle() {
  useEffect19(() => {
    ensureComposerFrameStyle();
  }, []);
}
var filled = (slot) => slot != null && slot !== false;
function ComposerFrame({
  children,
  header,
  footer,
  footerStart,
  className,
  style,
  headerClassName,
  footerClassName,
  footerStyle,
  footerStartClassName,
  railToggleLabel = "M\xE1s opciones"
}) {
  useComposerFrameStyle();
  const [railOpen, setRailOpen] = useState18(false);
  const railId = useId3();
  const hasRail = filled(footerStart);
  return /* @__PURE__ */ jsxs24(
    "div",
    {
      className,
      style,
      "data-fi-composer-frame": "",
      "data-fi-rail": hasRail ? railOpen ? "open" : "closed" : void 0,
      children: [
        filled(header) && /* @__PURE__ */ jsx32("div", { className: headerClassName, "data-fi-composer-slot": "header", children: header }),
        children,
        (filled(footer) || hasRail) && /* @__PURE__ */ jsxs24(
          "div",
          {
            className: footerClassName,
            style: footerStyle,
            "data-fi-composer-slot": "footer",
            children: [
              hasRail && /* @__PURE__ */ jsxs24(Fragment5, { children: [
                /* @__PURE__ */ jsx32(
                  "button",
                  {
                    type: "button",
                    className: withTouchTarget("fi-composer-rail-toggle"),
                    "aria-label": railToggleLabel,
                    "aria-expanded": railOpen,
                    "aria-controls": railId,
                    onClick: () => setRailOpen((v) => !v),
                    children: /* @__PURE__ */ jsx32(SlidersHorizontal, { size: 18, "aria-hidden": true })
                  }
                ),
                /* @__PURE__ */ jsx32(
                  "div",
                  {
                    id: railId,
                    className: footerStartClassName,
                    "data-fi-composer-slot": "footer-start",
                    children: footerStart
                  }
                )
              ] }),
              footer
            ]
          }
        )
      ]
    }
  );
}

// src/composer/ComposerImageAttachments.tsx
import { useRef as useRef14 } from "react";
import { X } from "lucide-react";
import { jsx as jsx33, jsxs as jsxs25 } from "react/jsx-runtime";
function ComposerImageChips({
  drafts,
  onRemove,
  disabled = false,
  className,
  removeLabel = "Quitar imagen"
}) {
  if (drafts.length === 0) return null;
  return /* @__PURE__ */ jsx33(
    "div",
    {
      className,
      "data-fi-image-chips": "",
      style: { display: "flex", flexWrap: "wrap", gap: "0.5rem" },
      children: drafts.map((draft) => /* @__PURE__ */ jsxs25("div", { style: { position: "relative" }, children: [
        /* @__PURE__ */ jsx33(
          "img",
          {
            src: draft.dataUrl,
            alt: draft.name,
            title: draft.name,
            style: {
              width: "3.5rem",
              height: "3.5rem",
              objectFit: "cover",
              borderRadius: "0.5rem",
              display: "block"
            }
          }
        ),
        /* @__PURE__ */ jsx33(
          "button",
          {
            type: "button",
            "aria-label": `${removeLabel}: ${draft.name}`,
            onClick: () => onRemove(draft.id),
            disabled,
            style: {
              position: "absolute",
              top: "-0.375rem",
              right: "-0.375rem",
              width: "1.25rem",
              height: "1.25rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "9999px",
              border: "none",
              cursor: disabled ? "default" : "pointer",
              background: "rgba(0,0,0,0.65)",
              color: "#fff",
              padding: 0
            },
            children: /* @__PURE__ */ jsx33(X, { size: 12, "aria-hidden": true })
          }
        )
      ] }, draft.id))
    }
  );
}
function useImagePicker(onFiles) {
  const inputRef = useRef14(null);
  const input = /* @__PURE__ */ jsx33(
    "input",
    {
      ref: inputRef,
      type: "file",
      accept: COMPOSER_IMAGE_ACCEPT,
      multiple: true,
      style: { display: "none" },
      "data-fi-image-input": "",
      onChange: (e) => {
        const files = Array.from(e.target.files ?? []);
        e.target.value = "";
        if (files.length > 0) onFiles(files);
      }
    }
  );
  return { input, open: () => inputRef.current?.click() };
}

// src/composer/ComposerActions.tsx
import { Plus } from "lucide-react";

// src/menu/ActionMenu.tsx
import { Fragment as Fragment6, useEffect as useEffect20, useRef as useRef15, useState as useState19 } from "react";
import { createPortal } from "react-dom";
import { Fragment as Fragment7, jsx as jsx34, jsxs as jsxs26 } from "react/jsx-runtime";
function ActionMenu({
  actions,
  trigger,
  triggerLabel,
  triggerClassName,
  triggerStyle,
  disabled = false,
  menuClassName,
  itemClassName,
  dividerClassName,
  triggerAttribute
}) {
  const [open, setOpen] = useState19(false);
  const triggerRef = useRef15(null);
  const [position, setPosition] = useState19({ top: 0, left: 0 });
  useEffect20(() => {
    if (open && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPosition({ top: rect.top - 8, left: rect.left });
    }
  }, [open]);
  useEffect20(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);
  if (actions.length === 0) return null;
  const triggerProps = triggerAttribute ? { [triggerAttribute]: "" } : {};
  return /* @__PURE__ */ jsxs26(Fragment7, { children: [
    /* @__PURE__ */ jsx34(
      "button",
      {
        ref: triggerRef,
        type: "button",
        onClick: () => setOpen((v) => !v),
        className: triggerClassName,
        style: triggerStyle,
        title: triggerLabel,
        "aria-label": triggerLabel,
        "aria-haspopup": "menu",
        "aria-expanded": open,
        disabled,
        ...triggerProps,
        children: trigger
      }
    ),
    open && typeof document !== "undefined" && createPortal(
      /* @__PURE__ */ jsxs26(Fragment7, { children: [
        /* @__PURE__ */ jsx34(
          "div",
          {
            className: "fixed inset-0 z-[9998]",
            onClick: () => setOpen(false),
            "aria-hidden": "true"
          }
        ),
        /* @__PURE__ */ jsx34(
          "div",
          {
            role: "menu",
            "data-fi-action-menu": "",
            className: menuClassName,
            style: {
              position: "fixed",
              top: position.top,
              left: position.left,
              // Grow UPWARD from the anchor — the composer is at the bottom.
              transform: "translateY(-100%)",
              zIndex: 9999,
              ...menuClassName ? {} : {
                minWidth: "13rem",
                padding: "0.35rem",
                borderRadius: 12,
                border: "1px solid rgba(255,255,255,0.12)",
                background: "rgba(15,23,42,0.98)",
                boxShadow: "0 12px 32px rgba(0,0,0,0.45)"
              }
            },
            children: actions.map((action) => {
              const item = /* @__PURE__ */ jsxs26(
                "button",
                {
                  type: "button",
                  role: "menuitem",
                  disabled: action.disabled,
                  onClick: () => {
                    setOpen(false);
                    action.onSelect();
                  },
                  className: action.className ?? itemClassName,
                  style: action.className ?? itemClassName ? void 0 : {
                    display: "flex",
                    alignItems: "center",
                    gap: "0.6rem",
                    width: "100%",
                    padding: "0.5rem 0.65rem",
                    borderRadius: 8,
                    border: "none",
                    background: "transparent",
                    color: action.disabled ? "#64748b" : "#e2e8f0",
                    fontSize: "0.875rem",
                    textAlign: "left",
                    cursor: action.disabled ? "default" : "pointer"
                  },
                  children: [
                    action.icon,
                    /* @__PURE__ */ jsx34("span", { children: action.label })
                  ]
                },
                action.id
              );
              const divider = action.dividerBefore ? /* @__PURE__ */ jsx34(
                "div",
                {
                  className: dividerClassName,
                  style: dividerClassName ? void 0 : { height: 1, margin: "0.25rem 0", background: "rgba(255,255,255,0.08)" }
                }
              ) : null;
              return action.wrapperClassName ? /* @__PURE__ */ jsxs26("div", { className: action.wrapperClassName, children: [
                divider,
                item
              ] }, action.id) : /* @__PURE__ */ jsxs26(Fragment6, { children: [
                divider,
                item
              ] }, action.id);
            })
          }
        )
      ] }),
      document.body
    )
  ] });
}

// src/composer/ComposerActions.tsx
import { jsx as jsx35 } from "react/jsx-runtime";
function ComposerActions({
  actions,
  disabled = false,
  label = "A\xF1adir",
  className,
  iconClassName,
  menuClassName,
  itemClassName
}) {
  return /* @__PURE__ */ jsx35(
    ActionMenu,
    {
      actions,
      trigger: /* @__PURE__ */ jsx35(Plus, { size: 18, "aria-hidden": true, className: iconClassName }),
      triggerLabel: label,
      triggerClassName: `fi-touch-target ${className ?? ""}`.trim(),
      triggerStyle: {
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        background: "transparent",
        border: "none",
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.5 : 1,
        padding: "0.375rem",
        color: "inherit"
      },
      disabled,
      menuClassName,
      itemClassName,
      triggerAttribute: "data-fi-composer-actions"
    }
  );
}

// src/agent/conversation-surface/components/composer/ComposerRegion.tsx
import { ImagePlus } from "lucide-react";

// src/agent/conversation-surface/components/composer/ComposerControls.tsx
import { Send, Loader2 as Loader212, Square as Square5 } from "lucide-react";
import { Fragment as Fragment8, jsx as jsx36, jsxs as jsxs27 } from "react/jsx-runtime";
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
  const stopping = isStreaming && onStop != null;
  return /* @__PURE__ */ jsxs27(Fragment8, { children: [
    micSlotOverride == null && dictation.micAvailable && dictation.isRecording && /* @__PURE__ */ jsx36(
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
    micSlotOverride != null ? micSlotOverride : dictation.micAvailable && /* @__PURE__ */ jsx36(
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
    /* @__PURE__ */ jsx36(
      "button",
      {
        type: "button",
        onClick: stopping ? onStop : onSend,
        disabled: stopping ? false : !canSend,
        "aria-label": stopping ? stopLabel : sendLabel,
        "data-fi-composer-send-state": stopping ? "stop" : isStreaming ? "busy" : "send",
        className: [
          FI_TOUCH_TARGET_CLASS,
          sendButtonClassName,
          stopping ? stopButtonClassName : void 0
        ].filter(Boolean).join(" "),
        children: stopping ? /* @__PURE__ */ jsx36(Square5, { className: sendButtonIconClassName, fill: "currentColor", "aria-hidden": true }) : isStreaming ? /* @__PURE__ */ jsx36(
          Loader212,
          {
            className: sendButtonIconClassName ? `${sendButtonIconClassName} animate-spin` : "animate-spin",
            "aria-hidden": true
          }
        ) : /* @__PURE__ */ jsx36(Send, { className: sendButtonIconClassName, "aria-hidden": true })
      }
    )
  ] });
}

// src/agent/conversation-surface/components/composer/NewChatButton.tsx
import { jsx as jsx37 } from "react/jsx-runtime";
function NewChatButton({ onClick, disabled, label = "New chat" }) {
  return /* @__PURE__ */ jsx37("div", { style: { display: "flex", justifyContent: "flex-end", marginBottom: "0.5rem" }, children: /* @__PURE__ */ jsx37(
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
import { Fragment as Fragment9, jsx as jsx38, jsxs as jsxs28 } from "react/jsx-runtime";
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
  const imageChips = images && images.drafts.length > 0 ? /* @__PURE__ */ jsx38(
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
        label: attachImageLabel ?? "Adjuntar imagen",
        icon: /* @__PURE__ */ jsx38(ImagePlus, { size: 16, "aria-hidden": true }),
        onSelect: imagePicker.open
      }
    ] : [],
    ...composerActions ?? []
  ];
  const attachButton = actions.length > 0 ? /* @__PURE__ */ jsxs28(Fragment9, { children: [
    images ? imagePicker.input : null,
    /* @__PURE__ */ jsx38(
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
  const header = imageChips || composerHeader ? /* @__PURE__ */ jsxs28(Fragment9, { children: [
    imageChips,
    composerHeader
  ] }) : void 0;
  const footerStart = attachButton || composerFooterStart ? /* @__PURE__ */ jsxs28(Fragment9, { children: [
    attachButton,
    composerFooterStart
  ] }) : void 0;
  const footer = showSendButton || micSlotOverride != null || dictation.micAvailable ? /* @__PURE__ */ jsx38(
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
  return /* @__PURE__ */ jsx38(
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
      children: /* @__PURE__ */ jsxs28("div", { style: { maxWidth: contentInset, margin: "0 auto", width: "100%", containerType: "inline-size", containerName: "fi-composer" }, children: [
        hasThread && showNewChatButton && /* @__PURE__ */ jsx38(NewChatButton, { onClick: newConversation, disabled: isStreaming, label: newChatLabel }),
        aboveComposer && /* @__PURE__ */ jsx38("div", { className: "fi-surface-above-composer", style: { marginBottom: "0.5rem" }, children: aboveComposer }),
        /* @__PURE__ */ jsx38(
          ComposerFrame,
          {
            className: composerBoxClassName,
            header,
            headerClassName: composerHeaderClassName,
            footerClassName: composerControlsClassName,
            footerStart,
            footerStartClassName: composerFooterStartClassName,
            footer,
            children: /* @__PURE__ */ jsx38(
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
import { jsx as jsx39, jsxs as jsxs29 } from "react/jsx-runtime";
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
    persistError,
    retryPersist,
    dismissPersistError,
    send,
    stop,
    retry,
    dismissError,
    newConversation,
    unsentText,
    clearUnsentText
  } = conversation;
  const [input, setInput] = useState20("");
  useEffect21(() => {
    if (!unsentText) return;
    setInput((current) => current.trim() ? current : unsentText);
    clearUnsentText();
  }, [unsentText, clearUnsentText]);
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
  const onSend = () => {
    const t = input.trim();
    const attached = imageAttachments ? images.toMessageImages() : [];
    if (!t && attached.length === 0) return;
    setInput("");
    images.clear();
    send(t, attached.length > 0 ? attached : void 0);
  };
  return /* @__PURE__ */ jsxs29("div", { style: rootStyle, children: [
    /* @__PURE__ */ jsx39(
      TranscriptRegion,
      {
        surface: props,
        conversation: {
          messages,
          turn,
          author,
          isStreaming,
          turnError,
          retry,
          dismissError,
          persistError,
          retryPersist,
          dismissPersistError
        },
        contentInset
      }
    ),
    /* @__PURE__ */ jsx39(
      ComposerRegion,
      {
        surface: props,
        state: {
          input,
          setInput,
          onSend,
          canSend: (input.trim().length > 0 || imageAttachments && images.drafts.length > 0) && !isStreaming,
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
import {
  useCallback as useCallback12,
  useEffect as useEffect23,
  useState as useState21
} from "react";
import { Menu } from "lucide-react";

// src/agent/densityStyle.ts
import { useEffect as useEffect22 } from "react";
var DENSITY_STYLE_ID = "fi-density-style";
var CSS3 = `
.fi-agent-workspace {
  --fi-space-1: 0.25rem;
  --fi-space-2: 0.5rem;
  --fi-space-3: 0.75rem;
  --fi-space-4: 1rem;
  --fi-space-5: 1.5rem;
  --fi-radius-section: 12px;
  --fi-touch-target: 44px;
}
/* CONV-MOBILE-RECLAIM-1 \u2014 the conversation surface's own spacing tokens. The
 * transcript/composer regions read these (with their previous literals as
 * fallbacks), so on a phone the chrome tightens and content dominates; desktop
 * resolves to the exact former values. Consumers re-tune by setting the vars. */
@media (max-width: 768px) {
  .fi-agent-workspace {
    --fi-transcript-pad: 0.75rem 0.75rem 0.5rem;
    --fi-transcript-gap: 0.5rem;
    --fi-composer-bar-pt: 0.5rem;
    --fi-composer-bar-px: 0.75rem;
    --fi-composer-bar-pb: 0.5rem;
  }
}
.fi-density-comfortable {
  --fi-section-gap: 0.5rem;
  --fi-sidebar-gap: 0.5rem;
  --fi-item-gap: 0.4rem;
  --fi-item-padding: 0.55rem 0.6rem;
  --fi-section-head-gap: 0.5rem;
  --fi-section-head-padding: 0.8rem 0.85rem 0.5rem;
}
.fi-density-compact {
  --fi-section-gap: 0.25rem;
  --fi-sidebar-gap: 0.25rem;
  --fi-item-gap: 0.3rem;
  --fi-item-padding: 0.4rem 0.5rem;
  --fi-section-head-gap: 0.4rem;
  --fi-section-head-padding: 0.6rem 0.7rem 0.35rem;
}
.fi-density-spacious {
  --fi-section-gap: 0.85rem;
  --fi-sidebar-gap: 0.85rem;
  --fi-item-gap: 0.55rem;
  --fi-item-padding: 0.75rem 0.85rem;
  --fi-section-head-gap: 0.65rem;
  --fi-section-head-padding: 1rem 1rem 0.65rem;
}
`;
function ensureDensityStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(DENSITY_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = DENSITY_STYLE_ID;
  el.textContent = CSS3;
  document.head.appendChild(el);
}
function useDensityStyle() {
  useEffect22(() => {
    ensureDensityStyle();
  }, []);
}

// src/agent/AgentWorkspaceShell.tsx
import { jsx as jsx40, jsxs as jsxs30 } from "react/jsx-runtime";
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
      outline: 2px solid var(--og-accent, #34d399); outline-offset: 2px;
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
  mobileQuery = "(max-width: 768px)",
  sidebarWidth = 280,
  toggleLabel = "Conversaciones",
  className,
  style
}) {
  useDensityStyle();
  const isMobile = useMediaQuery(mobileQuery);
  const [isOpen, setIsOpen] = useState21(false);
  const hasSidebar = sidebar != null;
  const drawerMode = hasSidebar && responsive && isMobile;
  const open = useCallback12(() => setIsOpen(true), []);
  const close = useCallback12(() => setIsOpen(false), []);
  const toggle = useCallback12(() => setIsOpen((v) => !v), []);
  useEffect23(() => {
    if (!drawerMode && isOpen) setIsOpen(false);
  }, [drawerMode, isOpen]);
  useEffect23(() => {
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
  useEffect23(() => {
    if (drawerMode) ensureToggleStyle();
  }, [drawerMode]);
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
    className
  ].filter(Boolean).join(" ");
  const content = /* @__PURE__ */ jsxs30(
    "div",
    {
      "data-fi-workspace": "agent",
      "data-fi-visual": visual,
      "data-fi-density": density,
      className: rootClassName,
      style: hasSidebar ? { ...rootStyle, flex: 1, minWidth: 0, height: "100%", ...style } : { ...rootStyle, ...style },
      children: [
        header != null && /* @__PURE__ */ jsx40("header", { "data-fi-slot": "header", children: header }),
        /* @__PURE__ */ jsxs30("main", { "data-fi-slot": "main", style: mainStyle, children: [
          /* @__PURE__ */ jsx40("div", { "data-fi-slot": "conversation", style: conversationStyle, children: conversation }),
          rail != null && /* @__PURE__ */ jsx40("aside", { "data-fi-slot": "rail", style: railStyle, children: rail })
        ] }),
        footer != null && /* @__PURE__ */ jsx40("footer", { "data-fi-slot": "footer", children: footer })
      ]
    }
  );
  if (!hasSidebar) return content;
  const api = { isOpen, isMobile, open, close, toggle };
  const sidebarNode = typeof sidebar === "function" ? sidebar(api) : sidebar;
  const widthCss = typeof sidebarWidth === "number" ? `${sidebarWidth}px` : sidebarWidth;
  const sidebarContainerStyle = drawerMode ? {
    position: "fixed",
    top: 0,
    left: 0,
    bottom: 0,
    zIndex: 50,
    width: `min(${widthCss}, 85vw)`,
    display: "flex",
    flexDirection: "column",
    transform: isOpen ? "translateX(0)" : "translateX(-100%)",
    transition: "transform 0.24s ease",
    willChange: "transform",
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
    paddingTop: "env(safe-area-inset-top, 0px)"
  } : {
    width: widthCss,
    flexShrink: 0,
    display: "flex",
    flexDirection: "column",
    containerType: "inline-size",
    containerName: "fi-sidebar"
  };
  return /* @__PURE__ */ jsxs30(
    "div",
    {
      "data-fi-workspace": "agent-with-sidebar",
      style: { display: "flex", height: "100dvh", position: "relative", overflowX: "hidden" },
      children: [
        /* @__PURE__ */ jsx40(
          "nav",
          {
            "data-fi-slot": "sidebar",
            "aria-label": toggleLabel,
            style: sidebarContainerStyle,
            "aria-hidden": drawerMode ? !isOpen : void 0,
            inert: drawerMode && !isOpen ? true : void 0,
            children: sidebarNode
          }
        ),
        drawerMode && /* @__PURE__ */ jsx40(
          "div",
          {
            onClick: close,
            "aria-hidden": true,
            style: {
              position: "fixed",
              inset: 0,
              zIndex: 40,
              background: "rgba(0,0,0,0.5)",
              opacity: isOpen ? 1 : 0,
              pointerEvents: isOpen ? "auto" : "none",
              transition: "opacity 0.24s ease"
            }
          }
        ),
        drawerMode && !isOpen && /* @__PURE__ */ jsx40(
          "button",
          {
            type: "button",
            className: "fi-aws-toggle",
            onClick: open,
            "aria-label": toggleLabel,
            "aria-expanded": isOpen,
            style: { position: "absolute", top: "0.6rem", left: "0.6rem", zIndex: 30 },
            children: /* @__PURE__ */ jsx40(Menu, { size: 18, "aria-hidden": true })
          }
        ),
        content
      ]
    }
  );
}

// src/agent/AgentSidebarItem.tsx
import {
  useCallback as useCallback13,
  useRef as useRef16,
  useState as useState22
} from "react";

// src/agent/sidebarItemStyle.ts
import { useEffect as useEffect24 } from "react";
var FI_SIDEBAR_ITEM_CLASS = "fi-sidebar-item";
var FI_ITEM_BODY_CLASS = "fi-sidebar-item-body";
var FI_ITEM_TITLE_CLASS = "fi-sidebar-item-title";
var FI_ITEM_SUBTITLE_CLASS = "fi-sidebar-item-subtitle";
var FI_ITEM_META_CLASS = "fi-sidebar-item-meta";
var FI_ITEM_ACTION_CLASS = "fi-item-action";
var FI_ITEM_ACTION_DANGER_CLASS = "fi-item-action--danger";
var FI_RESOURCE_RENAME_INPUT_CLASS = "fi-resource-rename-input";
var SIDEBAR_ITEM_STYLE_ID = "fi-sidebar-item-style";
var CSS4 = `
.${FI_SIDEBAR_ITEM_CLASS} {
  display: flex;
  align-items: flex-start;
  gap: var(--fi-item-gap, 0.4rem);
  padding: var(--fi-item-padding, 0.55rem 0.6rem);
  border-radius: 10px;
  border: 1px solid transparent;
  cursor: pointer;
  outline: none;
  transition: background 0.12s ease, border-color 0.12s ease;
}
.${FI_SIDEBAR_ITEM_CLASS}:hover {
  background: var(--fi-sidebar-item-hover-bg, rgba(255, 255, 255, 0.04));
}
.${FI_SIDEBAR_ITEM_CLASS}:focus-visible {
  box-shadow: 0 0 0 2px var(--glass-chat-accent-from, #059669);
}
.${FI_SIDEBAR_ITEM_CLASS}.is-selected {
  background: var(--fi-sidebar-item-selected-bg, rgba(52, 211, 153, 0.08));
  border-color: var(--fi-sidebar-item-selected-border, rgba(52, 211, 153, 0.3));
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
  font-size: 0.85rem;
  color: var(--glass-chat-text, #e2e8f0);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.${FI_ITEM_SUBTITLE_CLASS} {
  font-size: 0.75rem;
  color: var(--glass-chat-text-muted, #94a3b8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.${FI_ITEM_META_CLASS} {
  font-size: 0.68rem;
  color: var(--fi-sidebar-item-meta-color, #475569);
}
.${FI_ITEM_ACTION_CLASS} {
  border: none;
  background: transparent;
  color: var(--fi-sidebar-item-action-color, #64748b);
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
  color: var(--fi-sidebar-item-danger, #f87171);
}
@media (pointer: coarse) {
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
  font-size: 0.85rem;
  color: var(--glass-chat-text, #e2e8f0);
  background: var(--glass-chat-bg-mid, #0f172a);
  border: 1px solid var(--glass-chat-accent-from, #059669);
  border-radius: 4px;
  padding: 0.1rem 0.3rem;
  width: 100%;
  outline: none;
}
`;
function ensureSidebarItemStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(SIDEBAR_ITEM_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = SIDEBAR_ITEM_STYLE_ID;
  el.textContent = CSS4;
  document.head.appendChild(el);
}
function useSidebarItemStyle() {
  useEffect24(() => {
    ensureSidebarItemStyle();
  }, []);
}

// src/agent/AgentSidebarItem.tsx
import { Fragment as Fragment10, jsx as jsx41, jsxs as jsxs31 } from "react/jsx-runtime";
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
  const cls = withTouchTarget(
    joinClasses(FI_ITEM_ACTION_CLASS, danger && FI_ITEM_ACTION_DANGER_CLASS, className)
  );
  return /* @__PURE__ */ jsx41(
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
  return /* @__PURE__ */ jsx41(ItemActionSlot, { ...props, danger: true });
}
function useInlineRename(value, onRename, { maxLength, emptyPolicy = "revert" } = {}) {
  const [editing, setEditing] = useState22(false);
  const [draft, setDraft] = useState22("");
  const cancelledRef = useRef16(false);
  const start = useCallback13(() => {
    cancelledRef.current = false;
    setDraft(value);
    setEditing(true);
  }, [value]);
  const cancel = useCallback13(() => {
    cancelledRef.current = true;
    setEditing(false);
  }, []);
  const commit = useCallback13(() => {
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
  const titleNode = typeof title === "string" ? /* @__PURE__ */ jsx41("span", { className: FI_ITEM_TITLE_CLASS, children: title }) : title;
  return /* @__PURE__ */ jsxs31(
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
        if ((e.key === "Enter" || e.key === " ") && interactive) {
          e.preventDefault();
          onSelect();
        }
      },
      children: [
        /* @__PURE__ */ jsxs31("div", { className: FI_ITEM_BODY_CLASS, children: [
          titleNode,
          subtitle != null && subtitle !== "" && /* @__PURE__ */ jsx41("span", { className: FI_ITEM_SUBTITLE_CLASS, children: subtitle }),
          meta != null && meta !== "" && /* @__PURE__ */ jsx41("span", { className: FI_ITEM_META_CLASS, children: meta })
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
  const titleNode = rename.editing ? /* @__PURE__ */ jsx41(
    "input",
    {
      className: FI_RESOURCE_RENAME_INPUT_CLASS,
      "aria-label": renameInputLabel,
      ...rename.inputProps
    }
  ) : title;
  return /* @__PURE__ */ jsx41(
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
      actions: !rename.editing && /* @__PURE__ */ jsxs31(Fragment10, { children: [
        /* @__PURE__ */ jsx41(
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
import { useEffect as useEffect25 } from "react";
var FI_SIDEBAR_SECTION_CLASS = "fi-sidebar-section";
var FI_SECTION_HEAD_CLASS = "fi-sidebar-section-head";
var FI_SECTION_TITLE_CLASS = "fi-sidebar-section-title";
var FI_SECTION_CARD_CLASS = "fi-sidebar-section--card";
var FI_SECTION_FOOTER_CLASS = "fi-sidebar-section-footer";
var FI_SECTION_SCROLL_CLASS = "fi-sidebar-section-scroll";
var SIDEBAR_SECTION_STYLE_ID = "fi-sidebar-section-style";
var CSS5 = `
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
  if (typeof document === "undefined") return;
  if (document.getElementById(SIDEBAR_SECTION_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = SIDEBAR_SECTION_STYLE_ID;
  el.textContent = CSS5;
  document.head.appendChild(el);
}
function useSidebarSectionStyle() {
  useEffect25(() => {
    ensureSidebarSectionStyle();
  }, []);
}

// src/agent/AgentSidebarSection.tsx
import { jsx as jsx42, jsxs as jsxs32 } from "react/jsx-runtime";
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
  const titleNode = typeof title === "string" ? /* @__PURE__ */ jsx42("span", { className: FI_SECTION_TITLE_CLASS, children: title }) : title;
  const showEmpty = count === 0 && emptyState != null;
  const body = showEmpty ? emptyState : children;
  const scrollStyle = maxBlockSize != null ? {
    ["--fi-section-scroll-max"]: typeof maxBlockSize === "number" ? `${maxBlockSize}px` : maxBlockSize
  } : void 0;
  return /* @__PURE__ */ jsxs32(
    "section",
    {
      className: joinClasses2(
        FI_SIDEBAR_SECTION_CLASS,
        variant === "card" && FI_SECTION_CARD_CLASS,
        className
      ),
      "aria-label": ariaLabel,
      children: [
        headerSlot ?? /* @__PURE__ */ jsxs32("div", { className: FI_SECTION_HEAD_CLASS, children: [
          titleNode,
          actionSlot
        ] }),
        scrollBehavior === "content" && !showEmpty ? /* @__PURE__ */ jsx42("div", { className: FI_SECTION_SCROLL_CLASS, style: scrollStyle, children: body }) : body,
        footerSlot != null && /* @__PURE__ */ jsx42("div", { className: FI_SECTION_FOOTER_CLASS, children: footerSlot })
      ]
    }
  );
}
export {
  AgentConversationSurface,
  AgentPanel,
  AgentSidebarItem,
  AgentSidebarSection,
  AgentWorkspaceShell,
  DEFAULT_TURN_TIMEOUT_MS,
  DestructiveActionSlot,
  EditableResourceItem,
  FI_ITEM_ACTION_CLASS,
  FI_ITEM_META_CLASS,
  FI_ITEM_SUBTITLE_CLASS,
  FI_ITEM_TITLE_CLASS,
  FI_RESOURCE_RENAME_INPUT_CLASS,
  FI_SECTION_CARD_CLASS,
  FI_SECTION_FOOTER_CLASS,
  FI_SECTION_HEAD_CLASS,
  FI_SECTION_SCROLL_CLASS,
  FI_SECTION_TITLE_CLASS,
  FI_SIDEBAR_ITEM_CLASS,
  FI_SIDEBAR_SECTION_CLASS,
  ItemActionSlot,
  PlanChecklist,
  ScrollToBottomButton,
  SourcesPanel,
  StepsPanel,
  classifyTool,
  defaultAgentIcons,
  ensureDensityStyle,
  ensureSidebarItemStyle,
  ensureSidebarSectionStyle,
  latestOpenToolIndex,
  resolveIcons,
  shortToolName,
  toolIcon,
  toolVisualStatus,
  useAgentConversation,
  useDensityStyle,
  useInlineRename,
  useSidebarItemStyle,
  useSidebarSectionStyle
};
//# sourceMappingURL=index.js.map