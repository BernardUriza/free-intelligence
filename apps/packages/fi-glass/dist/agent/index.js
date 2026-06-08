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
  const WarnIcon = ic.warning;
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
        className: "mt-2 inline-flex items-start gap-2 rounded-lg border border-amber-700/40 bg-amber-950/20 p-2.5 text-xs text-amber-200",
        role: "status",
        children: [
          /* @__PURE__ */ jsx2(
            WarnIcon,
            {
              className: "h-3.5 w-3.5 shrink-0 mt-0.5 text-amber-400",
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
function useAgentConversation(agent) {
  const [messages, setMessages] = useState2([]);
  const pending = useRef(false);
  const send = useCallback(
    (text) => {
      const t = text.trim();
      if (!t || agent.isStreaming) return;
      setMessages((prev) => [...prev, makeUserMessage(t)]);
      pending.current = true;
      void agent.send(t);
    },
    [agent]
  );
  useEffect2(() => {
    if (agent.isStreaming || !pending.current) return;
    pending.current = false;
    setMessages((prev) => {
      if (agent.turn.status === "error") return prev.slice(0, -1);
      if (agent.turn.text) return [...prev, foldAssistantTurn(agent.turn)];
      return prev;
    });
  }, [agent.isStreaming, agent.turn]);
  const newConversation = useCallback(() => {
    setMessages([]);
    pending.current = false;
    agent.reset?.();
  }, [agent]);
  return {
    messages,
    turn: agent.turn,
    isStreaming: agent.isStreaming,
    send,
    newConversation
  };
}

// src/agent/AgentConversationSurface.tsx
import { useState as useState5 } from "react";

// src/composer/AutoResizeTextarea.tsx
import {
  useEffect as useEffect3,
  useRef as useRef2,
  useState as useState3
} from "react";
import { jsx as jsx5, jsxs as jsxs5 } from "react/jsx-runtime";
function AutoResizeTextarea({
  value,
  onChange,
  maxRows = 5,
  showCounter = false,
  maxLength,
  wrapperClassName = "",
  className = "",
  ...props
}) {
  const textareaRef = useRef2(null);
  const [rows, setRows] = useState3(1);
  useEffect3(() => {
    if (!textareaRef.current) return;
    const textarea = textareaRef.current;
    textarea.style.height = "auto";
    const lineHeight = 20;
    const newRows = Math.min(
      Math.ceil(textarea.scrollHeight / lineHeight),
      maxRows
    );
    setRows(newRows);
    textarea.style.height = `${newRows * lineHeight}px`;
  }, [value, maxRows]);
  const charCount = typeof value === "string" ? value.length : 0;
  const isNearLimit = maxLength && charCount > maxLength * 0.9;
  const isOverLimit = maxLength && charCount > maxLength;
  return /* @__PURE__ */ jsxs5("div", { className: `relative ${wrapperClassName}`, children: [
    /* @__PURE__ */ jsx5(
      "textarea",
      {
        ref: textareaRef,
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
    showCounter && maxLength && /* @__PURE__ */ jsxs5("div", { className: isOverLimit ? "chat-char-counter-error" : isNearLimit ? "chat-char-counter-warning" : "chat-char-counter-ok", children: [
      charCount,
      "/",
      maxLength
    ] })
  ] });
}

// src/composer/Composer.tsx
import { jsx as jsx6 } from "react/jsx-runtime";
function Composer({
  message,
  loading = false,
  placeholder = "Escribe tu mensaje...",
  onMessageChange,
  onSend,
  maxRows = 5,
  areaClassName,
  wrapperClassName,
  textareaClassName
}) {
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };
  return /* @__PURE__ */ jsx6("div", { className: areaClassName, children: /* @__PURE__ */ jsx6(
    AutoResizeTextarea,
    {
      value: message,
      onChange: (e) => onMessageChange(e.target.value),
      onKeyDown: handleKeyDown,
      placeholder,
      disabled: loading,
      maxRows,
      showCounter: false,
      wrapperClassName,
      className: textareaClassName
    }
  ) });
}

// src/messages/styles.ts
var messageStyles = {
  // Container
  container: {
    base: "space-y-0.5",
    padding: "px-4"
  },
  // Message row
  message: {
    base: "group relative py-3 px-4 -mx-4 transition-colors duration-150",
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
  // Content
  content: {
    base: "text-[14px] leading-relaxed",
    user: "text-slate-200",
    assistant: "text-slate-100",
    indent: "pl-8"
    // Align with avatar
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
      base: "p-1 rounded transition-colors duration-150",
      idle: "hover:bg-slate-700 text-slate-400 hover:text-slate-200",
      active: "bg-emerald-500/20 text-emerald-400",
      speaking: "bg-amber-500/20 text-amber-400"
    },
    icon: "w-3 h-3"
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
  blockquote: "my-3 pl-3 border-l-2 border-slate-600/50 text-slate-400 italic text-[13px]",
  link: "text-amber-400/90 hover:text-amber-300 underline underline-offset-2 transition-colors"
};

// src/messages/MessageContent.tsx
import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { jsx as jsx7, jsxs as jsxs6 } from "react/jsx-runtime";
var mdComponents = {
  p: ({ children }) => /* @__PURE__ */ jsx7("p", { className: markdownStyles.p, children }),
  strong: ({ children }) => /* @__PURE__ */ jsx7("strong", { className: markdownStyles.strong, children }),
  em: ({ children }) => /* @__PURE__ */ jsx7("em", { className: markdownStyles.em, children }),
  code: ({ children }) => /* @__PURE__ */ jsx7("code", { className: markdownStyles.code, children }),
  pre: ({ children }) => /* @__PURE__ */ jsx7("pre", { className: markdownStyles.pre, children }),
  ul: ({ children }) => /* @__PURE__ */ jsx7("ul", { className: markdownStyles.ul, children }),
  ol: ({ children }) => /* @__PURE__ */ jsx7("ol", { className: markdownStyles.ol, children }),
  li: ({ children }) => /* @__PURE__ */ jsxs6("li", { className: markdownStyles.li, children: [
    /* @__PURE__ */ jsx7("span", { className: markdownStyles.bullet, children: "\u2022" }),
    /* @__PURE__ */ jsx7("span", { className: "flex-1", children })
  ] }),
  h1: ({ children }) => /* @__PURE__ */ jsx7("h1", { className: markdownStyles.h1, children }),
  h2: ({ children }) => /* @__PURE__ */ jsx7("h2", { className: markdownStyles.h2, children }),
  h3: ({ children }) => /* @__PURE__ */ jsx7("h3", { className: markdownStyles.h3, children }),
  blockquote: ({ children }) => /* @__PURE__ */ jsx7("blockquote", { className: markdownStyles.blockquote, children }),
  a: ({ href, children }) => /* @__PURE__ */ jsx7(
    "a",
    {
      href,
      className: markdownStyles.link,
      target: "_blank",
      rel: "noopener noreferrer",
      children
    }
  )
};
function defaultRenderMarkdown(content) {
  return /* @__PURE__ */ jsx7(ReactMarkdown, { remarkPlugins: [remarkGfm], components: mdComponents, children: content });
}
var MessageContent = memo(function MessageContent2({
  isUser,
  content,
  isStreaming = false,
  renderMarkdown = defaultRenderMarkdown
}) {
  const { content: styles } = messageStyles;
  return /* @__PURE__ */ jsxs6(
    "div",
    {
      className: `${styles.base} ${isUser ? styles.user : styles.assistant} ${styles.indent}`,
      children: [
        isUser ? (
          // User: plain text, preserve whitespace
          /* @__PURE__ */ jsx7("p", { className: "whitespace-pre-wrap", children: content })
        ) : (
          // Assistant: markdown (overridable)
          renderMarkdown(content)
        ),
        isStreaming && /* @__PURE__ */ jsx7("span", { className: "inline-block w-1.5 h-4 bg-amber-400/80 ml-0.5 animate-pulse rounded-sm" })
      ]
    }
  );
});

// src/messages/CopyButton.tsx
import { memo as memo2, useCallback as useCallback2, useState as useState4 } from "react";
import { Copy, Check } from "lucide-react";
import { jsx as jsx8 } from "react/jsx-runtime";
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
  const [copied, setCopied] = useState4(false);
  const { actions } = messageStyles;
  const base = className ?? actions.button.base;
  const idle = idleClassName ?? actions.button.idle;
  const active = activeClassName ?? actions.button.active;
  const icon = iconClassName ?? actions.icon;
  const handleCopy = useCallback2(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), resetMs);
    } catch (err) {
      onError?.(err);
    }
  }, [content, onError, resetMs]);
  return /* @__PURE__ */ jsx8(
    "button",
    {
      onClick: handleCopy,
      className: `${base} ${copied ? active : idle}`,
      title: copied ? copiedLabel : copyLabel,
      "aria-label": copied ? copiedLabel : `${copyLabel} mensaje`,
      children: copied ? /* @__PURE__ */ jsx8(Check, { className: icon }) : /* @__PURE__ */ jsx8(Copy, { className: icon })
    }
  );
});

// src/messages/MessageBubble.tsx
import { memo as memo3 } from "react";
import { jsx as jsx9, jsxs as jsxs7 } from "react/jsx-runtime";
var MessageBubble = memo3(function MessageBubble2({
  role,
  children,
  header,
  reasoning,
  badge,
  actions,
  className,
  ariaLabel
}) {
  const { message: styles } = messageStyles;
  const isUser = role === "user";
  return /* @__PURE__ */ jsxs7(
    "article",
    {
      className: `${styles.base} ${styles.borderRadius} ${isUser ? styles.user : styles.assistant} ${className || ""}`,
      role: "article",
      "aria-label": ariaLabel,
      children: [
        header && /* @__PURE__ */ jsx9("div", { className: "flex items-center gap-2 mb-1", children: header }),
        reasoning && /* @__PURE__ */ jsx9("div", { className: "mt-3 mb-3", children: reasoning }),
        children,
        badge && /* @__PURE__ */ jsx9("div", { className: "mt-2", children: badge }),
        actions
      ]
    }
  );
});

// src/messages/MessageList.tsx
import { jsx as jsx10, jsxs as jsxs8 } from "react/jsx-runtime";

// src/agent/AgentConversationSurface.tsx
import { jsx as jsx11, jsxs as jsxs9 } from "react/jsx-runtime";
function AgentConversationSurface({
  conversation,
  composerPlaceholder,
  newChatLabel = "New chat",
  emptyState,
  aboveComposer,
  agentPanelProps,
  composerAreaClassName,
  composerTextareaClassName
}) {
  const { messages, turn, isStreaming, send, newConversation } = conversation;
  const [input, setInput] = useState5("");
  const idle = messages.length === 0 && !isStreaming && turn.status === "thinking" && !turn.plan && turn.steps.length === 0 && !turn.text;
  const hasThread = messages.length > 0 || isStreaming;
  const onSend = () => {
    const t = input.trim();
    if (!t) return;
    setInput("");
    send(t);
  };
  return /* @__PURE__ */ jsxs9("div", { style: { display: "flex", flexDirection: "column", height: "100dvh", maxWidth: 760, margin: "0 auto" }, children: [
    /* @__PURE__ */ jsx11("div", { style: { flex: 1, overflowY: "auto", padding: "1.25rem 1rem" }, children: idle ? emptyState : /* @__PURE__ */ jsxs9("div", { style: { display: "flex", flexDirection: "column", gap: "1rem" }, children: [
      messages.map((m, i) => /* @__PURE__ */ jsx11(MessageContent, { isUser: m.role === "user", content: m.content }, i)),
      isStreaming && /* @__PURE__ */ jsx11(AgentPanel, { turn, ...agentPanelProps }),
      isStreaming && turn.text && /* @__PURE__ */ jsx11("div", { style: { paddingTop: "0.5rem" }, children: /* @__PURE__ */ jsx11(MessageContent, { isUser: false, content: turn.text, isStreaming: true }) })
    ] }) }),
    /* @__PURE__ */ jsxs9("div", { style: { padding: "0.75rem 1rem 1.25rem", borderTop: "1px solid rgba(255,255,255,0.06)" }, children: [
      hasThread && /* @__PURE__ */ jsx11("div", { style: { display: "flex", justifyContent: "flex-end", marginBottom: "0.5rem" }, children: /* @__PURE__ */ jsx11(
        "button",
        {
          onClick: newConversation,
          disabled: isStreaming,
          style: {
            padding: "0.35rem 0.75rem",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.15)",
            background: "transparent",
            color: "#94a3b8",
            fontSize: "0.8rem",
            cursor: isStreaming ? "not-allowed" : "pointer",
            opacity: isStreaming ? 0.5 : 1
          },
          children: newChatLabel
        }
      ) }),
      aboveComposer,
      /* @__PURE__ */ jsx11(
        Composer,
        {
          message: input,
          loading: isStreaming,
          placeholder: composerPlaceholder,
          onMessageChange: setInput,
          onSend,
          areaClassName: composerAreaClassName,
          textareaClassName: composerTextareaClassName
        }
      )
    ] })
  ] });
}
export {
  AgentConversationSurface,
  AgentPanel,
  PlanChecklist,
  SourcesPanel,
  StepsPanel,
  classifyTool,
  defaultAgentIcons,
  latestOpenToolIndex,
  resolveIcons,
  shortToolName,
  toolIcon,
  toolVisualStatus,
  useAgentConversation
};
//# sourceMappingURL=index.js.map