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
export {
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
  toolVisualStatus
};
//# sourceMappingURL=index.js.map