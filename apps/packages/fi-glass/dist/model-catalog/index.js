'use client';

import {
  AdminAlert,
  AdminButton,
  AdminSheet,
  ensureAdminKitStyle
} from "../chunk-PIE7SC3N.js";
import {
  glassTokens
} from "../chunk-LO4SF24V.js";
import "../chunk-SMPLGG7E.js";
import {
  FI_MOBILE_QUERY,
  FI_TOUCH_QUERY
} from "../chunk-HJ2CVNCV.js";

// src/model-catalog/types.ts
var defaultModelCatalogConfirm = async (message) => typeof window !== "undefined" && typeof window.confirm === "function" ? window.confirm(message) : false;
var silentNotify = () => {
};
function errorMessage(err, fallback) {
  return err instanceof Error && err.message ? err.message : fallback;
}

// src/model-catalog/format.ts
var PROVIDER_INFO = {
  openai: { label: "OpenAI" },
  anthropic: { label: "Anthropic" },
  azure: { label: "Azure" },
  ollama: { label: "Ollama (Local)" }
};
var COST_TIER_INFO = {
  low: { label: "Econ\xF3mico", symbol: "$" },
  medium: { label: "Balance", symbol: "$$" },
  high: { label: "Premium", symbol: "$$$" }
};
var SOURCE_INFO = {
  gpt4all: { label: "GPT4All" },
  huggingface: { label: "HuggingFace" },
  ollama: { label: "Ollama" }
};
var QUANT_INFO = {
  Q4_0: { label: "Q4_0", quality: "B\xE1sica" },
  Q4_K_M: { label: "Q4_K_M", quality: "Balanceada" },
  Q5_K_M: { label: "Q5_K_M", quality: "Alta" },
  Q8_0: { label: "Q8_0", quality: "Muy Alta" },
  F16: { label: "F16", quality: "M\xE1xima" },
  unknown: { label: "Desconocida", quality: "N/A" }
};
var CATALOG_SOURCES = ["ollama", "gpt4all", "huggingface"];
var FEATURED_MODEL_IDS = [
  "llama-3.2-3b-instruct",
  "phi-3-mini",
  "mistral-7b-instruct",
  "qwen2.5-3b-instruct",
  "gemma-2-2b"
];
var CATALOG_SIZE_OPTIONS = [
  { value: "", label: "Tama\xF1o" },
  { value: "2", label: "\u2264 2 GB" },
  { value: "4", label: "\u2264 4 GB" },
  { value: "8", label: "\u2264 8 GB" },
  { value: "16", label: "\u2264 16 GB" }
];
function isLocalProvider(provider) {
  return provider === "ollama";
}
function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(sizes.length - 1, Math.floor(Math.log(bytes) / Math.log(1e3)));
  return `${(bytes / Math.pow(1e3, i)).toFixed(1)} ${sizes[i]}`;
}
function formatCount(n) {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return String(n);
}
function formatDate(iso, locale) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString(locale, { year: "numeric", month: "short", day: "numeric" });
}
function formatTimeUntil(iso, now = /* @__PURE__ */ new Date()) {
  if (!iso) return "Persistente";
  const diffMs = new Date(iso).getTime() - now.getTime();
  if (diffMs <= 0) return "Descargando...";
  const minutes = Math.floor(diffMs / 6e4);
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}
function usageLevel(percent) {
  if (percent < 50) return "ok";
  if (percent < 75) return "warn";
  if (percent < 90) return "danger";
  return "critical";
}
function isFeaturedModel(model) {
  const id = model.id.toLowerCase();
  return FEATURED_MODEL_IDS.some((featured) => id.includes(featured));
}
function catalogModelToCreate(model) {
  return {
    id: model.id,
    label: model.name,
    provider: "ollama",
    cost_tier: "low",
    max_tokens: 4096,
    context_window: model.context_length || 4096,
    is_active: true,
    description: model.description || `${model.name} (${model.quantization})`,
    size_bytes: model.size_bytes,
    ram_required_gb: model.ram_required_gb || null
  };
}
function isAlreadyRegisteredError(err) {
  const message = err instanceof Error ? err.message : "";
  return message.includes("already exists") || message.includes("duplicate");
}

// src/model-catalog/ProviderLogo.tsx
import { jsx, jsxs } from "react/jsx-runtime";
var STROKE = { stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round" };
function ProviderLogo({ provider, size = 24, className }) {
  const svg = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", className, "aria-hidden": true };
  switch (provider) {
    case "openai":
      return /* @__PURE__ */ jsxs("svg", { ...svg, children: [
        /* @__PURE__ */ jsx("path", { d: "M12 2L3 7v10l9 5 9-5V7l-9-5z", stroke: "currentColor", strokeWidth: 1.5 }),
        /* @__PURE__ */ jsx("circle", { cx: "12", cy: "12", r: "3", fill: "currentColor" }),
        /* @__PURE__ */ jsx("path", { d: "M12 5v4M12 15v4M5.5 8.5l3.5 2M15 13.5l3.5 2M5.5 15.5l3.5-2M15 10.5l3.5-2", ...STROKE })
      ] });
    case "anthropic":
      return /* @__PURE__ */ jsx("svg", { ...svg, children: /* @__PURE__ */ jsx("path", { d: "M12 3L4 21h3.5l1.5-4h6l1.5 4H20L12 3z", fill: "currentColor" }) });
    case "azure":
      return /* @__PURE__ */ jsxs("svg", { ...svg, children: [
        /* @__PURE__ */ jsx("path", { d: "M6.5 19a4.5 4.5 0 01-.5-8.97 5.5 5.5 0 0110.74-1.52A4 4 0 0118.5 16h-.5", ...STROKE, strokeLinejoin: "round" }),
        /* @__PURE__ */ jsx("path", { d: "M6 19h12", ...STROKE })
      ] });
    case "ollama":
      return /* @__PURE__ */ jsxs("svg", { ...svg, children: [
        /* @__PURE__ */ jsx(
          "path",
          {
            d: "M12 4c-2 0-3.5 1-4.5 2.5C6.5 8 6 9.5 6 11v6c0 1.5.5 2 2 2.5.5.2 1 .3 1.5.4M12 4c2 0 3.5 1 4.5 2.5 1 1.5 1.5 3 1.5 4.5v6c0 1.5-.5 2-2 2.5-.5.2-1 .3-1.5.4",
            ...STROKE
          }
        ),
        /* @__PURE__ */ jsx("circle", { cx: "9", cy: "10", r: "1", fill: "currentColor" }),
        /* @__PURE__ */ jsx("circle", { cx: "15", cy: "10", r: "1", fill: "currentColor" }),
        /* @__PURE__ */ jsx("path", { d: "M6 7c-1-1-2-1-3 0M18 7c1-1 2-1 3 0", ...STROKE }),
        /* @__PURE__ */ jsx("ellipse", { cx: "12", cy: "14", rx: "2", ry: "1.5", stroke: "currentColor", strokeWidth: 1 })
      ] });
    case "gpt4all":
      return /* @__PURE__ */ jsxs("svg", { ...svg, children: [
        /* @__PURE__ */ jsx("path", { d: "M12 22V12", ...STROKE }),
        /* @__PURE__ */ jsx("path", { d: "M12 12c-4-2-6-6-5-10 4 1 7 4 8 8", ...STROKE, strokeLinejoin: "round" }),
        /* @__PURE__ */ jsx("path", { d: "M12 12c4-2 6-6 5-10-4 1-7 4-8 8", ...STROKE, strokeLinejoin: "round" }),
        /* @__PURE__ */ jsx("path", { d: "M12 16c-2 0-4 1-5 3M12 16c2 0 4 1 5 3", ...STROKE })
      ] });
    case "huggingface":
      return /* @__PURE__ */ jsxs("svg", { ...svg, children: [
        /* @__PURE__ */ jsx("circle", { cx: "12", cy: "12", r: "9", stroke: "currentColor", strokeWidth: 1.5 }),
        /* @__PURE__ */ jsx("circle", { cx: "9", cy: "10", r: "1.5", fill: "currentColor" }),
        /* @__PURE__ */ jsx("circle", { cx: "15", cy: "10", r: "1.5", fill: "currentColor" }),
        /* @__PURE__ */ jsx("path", { d: "M8 14c1 2 3 3 4 3s3-1 4-3", ...STROKE }),
        /* @__PURE__ */ jsx("path", { d: "M3 10c0 2 1 4 2 5M21 10c0 2-1 4-2 5", ...STROKE })
      ] });
    default:
      return /* @__PURE__ */ jsxs("svg", { ...svg, children: [
        /* @__PURE__ */ jsx("circle", { cx: "12", cy: "12", r: "9", stroke: "currentColor", strokeWidth: 1.5 }),
        /* @__PURE__ */ jsx("path", { d: "M12 8v8M8 12h8", ...STROKE })
      ] });
  }
}
function ProviderLogoBox({ provider, size = 28, className }) {
  return /* @__PURE__ */ jsx("span", { className: className ? `fi-mc-logo ${className}` : "fi-mc-logo", "data-provider": provider, children: /* @__PURE__ */ jsx(ProviderLogo, { provider, size }) });
}

// src/model-catalog/LLMModelCard.tsx
import { Edit, FlaskConical, Power, PowerOff, Trash2 } from "lucide-react";

// src/model-catalog/modelCatalogStyle.ts
import { useInsertionEffect } from "react";
var FI_MODEL_CATALOG_ROOT_CLASS = "fi-model-catalog";
var STYLE_ID = "fi-model-catalog-style";
var ACCENT = `var(--fi-mc-accent, ${glassTokens.accent})`;
var CATALOG = `var(--fi-mc-catalog-accent, #a78bfa)`;
var FEATURED = `var(--fi-mc-featured, #fbbf24)`;
var TEXT = `var(--glass-chat-text, ${glassTokens.text})`;
var MUTED = `var(--glass-chat-text-muted, ${glassTokens.textMuted})`;
var DANGER = `var(--fi-mc-danger, ${glassTokens.danger})`;
var BORDER = `var(--fi-mc-border, ${glassTokens.surfaceBorder})`;
var FIELD_BG = `var(--fi-mc-field-bg, ${glassTokens.searchFill})`;
var SURFACE = glassTokens.surface;
var MONO = "ui-monospace, SFMono-Regular, Menlo, monospace";
var LINE = (side) => `border-${side}-width: 1px; border-${side}-style: solid; border-${side}-color: ${BORDER};`;
var CSS = `
.${FI_MODEL_CATALOG_ROOT_CLASS} { color: ${TEXT}; font-size: 0.875rem; --fi-admin-sheet-width: var(--fi-mc-sheet-width, 36rem); --fi-admin-panel-width: var(--fi-mc-drawer-width, 42rem); --fi-admin-accent: ${ACCENT}; --fi-admin-secondary: ${CATALOG}; }
.fi-mc-input {
  width: 100%; box-sizing: border-box; padding: 0.55rem 0.75rem; border-radius: 10px; font: inherit; font-size: 0.875rem;
  color: ${TEXT}; background: ${FIELD_BG}; border-width: 1px; border-style: solid; border-color: ${BORDER}; outline: none;
}
.fi-mc-input:focus-visible { border-color: ${ACCENT}; box-shadow: 0 0 0 1px ${ACCENT}; }
.fi-mc-input option { color: #0f172a; }
textarea.fi-mc-input { resize: vertical; line-height: 1.5; }
.fi-mc-mono { font-family: ${MONO}; }
.fi-mc-title { margin: 0; font-size: 1.125rem; font-weight: 600; color: ${TEXT}; display: flex; align-items: center; gap: 0.5rem; }
.fi-mc-subtitle { margin: 0.15rem 0 0; font-size: 0.8125rem; color: ${MUTED}; }
.fi-mc-actions { display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
.fi-mc-stack { display: flex; flex-direction: column; gap: 1rem; }
.fi-mc-grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.fi-mc-field { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
.fi-mc-label { font-size: 0.8125rem; font-weight: 500; color: ${MUTED}; }
.fi-mc-hint { margin: 0; font-size: 0.75rem; color: ${MUTED}; }
.fi-mc-check { display: inline-flex; align-items: center; gap: 0.5rem; cursor: pointer; color: ${MUTED}; min-height: 36px; }
.fi-mc-check input { width: 1.1rem; height: 1.1rem; accent-color: ${ACCENT}; margin: 0; }
.fi-mc-filters { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.fi-mc-filters .fi-mc-input { width: auto; min-width: 14rem; }
.fi-mc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr)); gap: 1.25rem; }
.fi-mc-empty { display: flex; flex-direction: column; align-items: center; gap: 0.6rem; padding: 3rem 1rem; color: ${MUTED}; text-align: center; }
.fi-mc-empty h3 { margin: 0; font-size: 1.125rem; font-weight: 600; color: ${TEXT}; }
.fi-mc-empty p { margin: 0; max-width: 28rem; }
.fi-mc-card {
  display: flex; flex-direction: column; gap: 0.9rem; padding: 1.25rem; border-radius: 14px; cursor: pointer; min-width: 0;
  background: ${SURFACE}; border-width: 1px; border-style: solid; border-color: ${BORDER}; transition: border-color 0.12s ease;
}
.fi-mc-card:hover { border-color: color-mix(in srgb, ${ACCENT} 50%, transparent); }
.fi-mc-card[data-selected="true"] { border-color: ${ACCENT}; background: color-mix(in srgb, ${ACCENT} 8%, ${SURFACE}); }
.fi-mc-card[data-active="false"] { opacity: 0.65; }
.fi-mc-card:focus-visible { outline: none; box-shadow: 0 0 0 2px ${ACCENT}; }
.fi-mc-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }
.fi-mc-card-id { display: flex; align-items: center; gap: 0.75rem; min-width: 0; }
.fi-mc-card-name { margin: 0; font-size: 1rem; font-weight: 700; color: ${TEXT}; overflow-wrap: anywhere; }
.fi-mc-badge { display: inline-flex; align-items: center; gap: 0.2rem; margin-left: 0.4rem; padding: 0.05rem 0.4rem; border-radius: 6px; font-size: 0.6875rem; font-weight: 500; vertical-align: middle; background: ${glassTokens.chipFill}; color: ${MUTED}; }
.fi-mc-badge[data-tone="installed"] { color: ${ACCENT}; background: color-mix(in srgb, ${ACCENT} 18%, transparent); }
.fi-mc-badge[data-tone="featured"] { color: ${FEATURED}; background: color-mix(in srgb, ${FEATURED} 18%, transparent); }
.fi-mc-clamp1, .fi-mc-clamp2 { margin: 0; display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden; }
.fi-mc-clamp1 { -webkit-line-clamp: 1; }
.fi-mc-clamp2 { -webkit-line-clamp: 2; color: ${MUTED}; font-size: 0.8125rem; }
.fi-mc-stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5rem; margin: 0; }
.fi-mc-mini { padding: 0.5rem 0.625rem; border-radius: 8px; background: ${glassTokens.chipFill}; min-width: 0; }
.fi-mc-mini dt { font-size: 0.6875rem; color: ${MUTED}; }
.fi-mc-mini dd { margin: 0; display: flex; align-items: center; gap: 0.35rem; font-family: ${MONO}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fi-mc-card-foot { padding-top: 0.75rem; ${LINE("top")} font-size: 0.75rem; color: ${MUTED}; }
.fi-mc-logo { flex: 0 0 auto; display: inline-flex; padding: 0.45rem; border-radius: 10px; border-width: 1px; border-style: solid; color: var(--fi-mc-logo, ${MUTED}); border-color: color-mix(in srgb, var(--fi-mc-logo, ${MUTED}) 45%, transparent); background: color-mix(in srgb, var(--fi-mc-logo, ${MUTED}) 14%, transparent); }
.fi-mc-logo[data-provider="openai"], .fi-mc-logo[data-provider="gpt4all"] { --fi-mc-logo: #34d399; }
.fi-mc-logo[data-provider="anthropic"] { --fi-mc-logo: #fb923c; }
.fi-mc-logo[data-provider="azure"] { --fi-mc-logo: #60a5fa; }
.fi-mc-logo[data-provider="ollama"] { --fi-mc-logo: #c084fc; }
.fi-mc-logo[data-provider="huggingface"] { --fi-mc-logo: #facc15; }
.fi-mc-panel { margin-bottom: 1.5rem; padding: 1.25rem; border-radius: 14px; background: ${SURFACE}; border-width: 1px; border-style: solid; border-color: ${BORDER}; }
.fi-mc-panel-head { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; margin-bottom: 1rem; }
.fi-mc-row-between { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap; }
.fi-mc-inline { display: inline-flex; align-items: center; gap: 0.4rem; min-width: 0; }
.fi-mc-muted { color: ${MUTED}; }
.fi-mc-small { font-size: 0.75rem; color: ${MUTED}; }
.fi-mc-meter { height: 0.6rem; margin: 0.5rem 0 0.3rem; border-radius: 999px; overflow: hidden; background: ${glassTokens.chipFill}; }
.fi-mc-meter > div { height: 100%; border-radius: inherit; transition: width 0.3s ease; background: ${ACCENT}; }
.fi-mc-meter[data-level="warn"] > div { background: #facc15; }
.fi-mc-meter[data-level="danger"] > div { background: #fb923c; }
.fi-mc-meter[data-level="critical"] > div { background: ${DANGER}; }
.fi-mc-meter[data-tone="catalog"] { height: 0.4rem; margin: 0.5rem 0 0.2rem; }
.fi-mc-meter[data-tone="catalog"] > div { background: ${CATALOG}; }
.fi-mc-section { margin-top: 1rem; padding-top: 1rem; ${LINE("top")} }
.fi-mc-running { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.75rem; }
.fi-mc-running-item { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; padding: 0.5rem 0.75rem; border-radius: 10px; background: ${glassTokens.chipFill}; }
.fi-mc-proc { padding: 0.05rem 0.4rem; border-radius: 6px; font-size: 0.6875rem; font-weight: 600; font-family: ${MONO}; color: ${MUTED}; background: ${glassTokens.chipFill}; }
.fi-mc-proc[data-processor="gpu"] { color: ${ACCENT}; background: color-mix(in srgb, ${ACCENT} 18%, transparent); }
.fi-mc-proc[data-processor="partial"] { color: #facc15; background: rgba(250, 204, 21, 0.15); }
.fi-mc-dot { display: inline-block; width: 0.5rem; height: 0.5rem; border-radius: 999px; background: ${ACCENT}; }
.fi-mc-sources { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.75rem 0; }
.fi-mc-chip { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.3rem 0.7rem; border-radius: 999px; font-size: 0.75rem; color: ${MUTED}; background: ${glassTokens.chipFill}; border-width: 1px; border-style: solid; border-color: ${BORDER}; }
.fi-mc-chip[data-status="loading"] { color: #60a5fa; }
.fi-mc-chip[data-status="loaded"] { color: ${ACCENT}; }
.fi-mc-chip[data-status="error"] { color: ${DANGER}; }
.fi-mc-toolbar { display: flex; gap: 0.5rem; align-items: center; }
.fi-mc-search { position: relative; flex: 1 1 auto; min-width: 0; }
.fi-mc-search svg { position: absolute; left: 0.75rem; top: 50%; transform: translateY(-50%); color: ${MUTED}; pointer-events: none; }
.fi-mc-search .fi-mc-input { padding-left: 2.25rem; }
.fi-mc-toolbar select.fi-mc-input { width: 7.5rem; flex: 0 0 auto; }
.fi-mc-tabs { display: flex; gap: 0.35rem; overflow-x: auto; margin-top: 0.75rem; padding-bottom: 0.15rem; scrollbar-width: none; }
.fi-mc-tab[aria-selected="true"] { color: #fff; background: color-mix(in srgb, ${CATALOG} 70%, transparent); border-color: transparent; }
.fi-mc-count { padding: 0 0.35rem; border-radius: 6px; font-size: 0.6875rem; background: rgba(0, 0, 0, 0.25); }
.fi-mc-section-title { display: flex; align-items: center; gap: 0.4rem; margin: 0 0 0.6rem; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em; color: ${MUTED}; }
.fi-mc-section-title[data-tone="featured"] { color: ${FEATURED}; }
.fi-mc-list { display: flex; flex-direction: column; gap: 0.4rem; margin: 0 0 1.25rem; padding: 0; list-style: none; }
.fi-mc-row {
  display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; border-radius: 12px; min-width: 0;
  background: ${glassTokens.chipFill}; border-width: 1px; border-style: solid; border-color: ${BORDER};
}
.fi-mc-row[data-installed="true"] { border-color: color-mix(in srgb, ${ACCENT} 35%, transparent); }
.fi-mc-row[data-featured="true"] { border-color: color-mix(in srgb, ${FEATURED} 35%, transparent); }
.fi-mc-row[data-selected="true"] { box-shadow: 0 0 0 2px ${CATALOG}; }
.fi-mc-row-info { flex: 1 1 auto; min-width: 0; }
.fi-mc-row-name { font-weight: 500; color: ${TEXT}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fi-mc-row-meta { display: flex; flex-wrap: wrap; gap: 0.25rem 0.75rem; margin-top: 0.15rem; font-size: 0.75rem; color: ${MUTED}; }
.fi-mc-row-error { margin: 0.25rem 0 0; font-size: 0.75rem; color: ${DANGER}; }
.fi-mc-skel { height: 3.75rem; border-radius: 12px; background: linear-gradient(90deg, ${glassTokens.chipFill} 25%, rgba(255, 255, 255, 0.09) 50%, ${glassTokens.chipFill} 75%); background-size: 200% 100%; animation: fi-mc-shimmer 1.4s ease-in-out infinite; }
@keyframes fi-mc-shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
.fi-mc-keys { display: flex; justify-content: space-between; gap: 1rem; font-size: 0.75rem; color: ${MUTED}; }
.fi-mc-result { display: flex; flex-direction: column; gap: 0.35rem; padding: 0.75rem 1rem; border-radius: 10px; background: ${glassTokens.chipFill}; }
.fi-mc-result[data-tone="success"] { background: color-mix(in srgb, ${ACCENT} 10%, transparent); border: 1px solid color-mix(in srgb, ${ACCENT} 35%, transparent); }
.fi-mc-result[data-tone="error"] { background: rgba(248, 113, 113, 0.08); border: 1px solid rgba(248, 113, 113, 0.35); }
.fi-mc-result p { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.fi-mc-result .fi-mc-label { text-transform: uppercase; font-size: 0.6875rem; letter-spacing: 0.05em; }
@media ${FI_MOBILE_QUERY} {
  .fi-mc-grid2, .fi-mc-stats { grid-template-columns: minmax(0, 1fr); }
  .fi-mc-input { font-size: 16px; }
  .fi-mc-filters .fi-mc-input { min-width: 0; flex: 1 1 auto; }
  .fi-mc-toolbar { flex-wrap: wrap; }
  .fi-mc-search { flex-basis: 100%; }
  .fi-mc-toolbar select.fi-mc-input { flex: 1 1 auto; width: auto; }
  .fi-mc-panel { padding: 1rem 0.75rem; }
}
@media ${FI_TOUCH_QUERY} {
  .fi-mc-input, .fi-mc-check { min-height: var(--fi-touch-target, 44px); }
  .fi-mc-keys { display: none; }
}
`;
function ensureModelCatalogStyle() {
  if (typeof document === "undefined") return;
  ensureAdminKitStyle();
  if (document.getElementById(STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}
function useModelCatalogStyle() {
  useInsertionEffect(() => {
    ensureModelCatalogStyle();
  }, []);
}

// src/model-catalog/LLMModelCard.tsx
import { jsx as jsx2, jsxs as jsxs2 } from "react/jsx-runtime";
function LLMModelCard({
  model,
  selected = false,
  onSelect,
  onEdit,
  onDeactivate,
  onToggleActive,
  onTest,
  locale = "es-MX"
}) {
  useModelCatalogStyle();
  const providerLabel = PROVIDER_INFO[model.provider]?.label ?? model.provider;
  const cost = COST_TIER_INFO[model.cost_tier];
  const onKey = (e) => {
    if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      onSelect?.();
    }
  };
  const act = (fn) => (e) => {
    e.stopPropagation();
    fn();
  };
  return /* @__PURE__ */ jsxs2(
    "article",
    {
      className: `${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-card`,
      "data-selected": selected,
      "data-active": model.is_active,
      tabIndex: 0,
      "aria-label": model.id,
      onClick: onSelect,
      onKeyDown: onKey,
      children: [
        /* @__PURE__ */ jsxs2("div", { className: "fi-mc-card-head", children: [
          /* @__PURE__ */ jsxs2("div", { className: "fi-mc-card-id", children: [
            /* @__PURE__ */ jsx2(ProviderLogoBox, { provider: model.provider }),
            /* @__PURE__ */ jsxs2("div", { style: { minWidth: 0 }, children: [
              /* @__PURE__ */ jsxs2("h3", { className: "fi-mc-card-name", children: [
                model.id,
                model.is_active ? null : /* @__PURE__ */ jsx2("span", { className: "fi-mc-badge", children: "Inactivo" })
              ] }),
              /* @__PURE__ */ jsx2("p", { className: "fi-mc-small", style: { margin: 0 }, children: providerLabel })
            ] })
          ] }),
          /* @__PURE__ */ jsxs2("div", { className: "fi-mc-actions", children: [
            /* @__PURE__ */ jsx2(
              AdminButton,
              {
                variant: "ghost",
                iconOnly: true,
                tone: model.is_active ? "on" : "off",
                icon: model.is_active ? PowerOff : Power,
                "aria-label": model.is_active ? "Desactivar modelo" : "Activar modelo",
                title: model.is_active ? "Desactivar" : "Activar",
                onClick: act(onToggleActive)
              }
            ),
            model.is_active && onTest ? /* @__PURE__ */ jsx2(
              AdminButton,
              {
                variant: "ghost",
                iconOnly: true,
                tone: "secondary",
                icon: FlaskConical,
                "aria-label": "Probar modelo",
                title: "Probar modelo",
                onClick: act(onTest)
              }
            ) : null,
            /* @__PURE__ */ jsx2(AdminButton, { variant: "ghost", iconOnly: true, icon: Edit, "aria-label": "Editar modelo", onClick: act(onEdit) }),
            /* @__PURE__ */ jsx2(
              AdminButton,
              {
                variant: "ghost",
                iconOnly: true,
                tone: "danger",
                icon: Trash2,
                "aria-label": "Eliminar modelo",
                onClick: act(onDeactivate)
              }
            )
          ] })
        ] }),
        /* @__PURE__ */ jsx2("p", { className: "fi-mc-clamp1", children: model.label }),
        model.description ? /* @__PURE__ */ jsx2("p", { className: "fi-mc-clamp2", children: model.description }) : null,
        /* @__PURE__ */ jsxs2("dl", { className: "fi-mc-stats", children: [
          /* @__PURE__ */ jsxs2("div", { className: "fi-mc-mini", children: [
            /* @__PURE__ */ jsx2("dt", { children: "Proveedor" }),
            /* @__PURE__ */ jsxs2("dd", { children: [
              /* @__PURE__ */ jsx2(ProviderLogo, { provider: model.provider, size: 14 }),
              providerLabel
            ] })
          ] }),
          isLocalProvider(model.provider) ? /* @__PURE__ */ jsxs2("div", { className: "fi-mc-mini", children: [
            /* @__PURE__ */ jsx2("dt", { children: "RAM" }),
            /* @__PURE__ */ jsx2("dd", { children: model.size_bytes ? formatBytes(model.size_bytes) : "\u2014" })
          ] }) : /* @__PURE__ */ jsxs2("div", { className: "fi-mc-mini", children: [
            /* @__PURE__ */ jsx2("dt", { children: "Costo" }),
            /* @__PURE__ */ jsx2("dd", { children: cost ? `${cost.symbol} ${cost.label}` : model.cost_tier })
          ] }),
          /* @__PURE__ */ jsxs2("div", { className: "fi-mc-mini", children: [
            /* @__PURE__ */ jsx2("dt", { children: "Max Tokens" }),
            /* @__PURE__ */ jsx2("dd", { children: formatCount(model.max_tokens) })
          ] }),
          /* @__PURE__ */ jsxs2("div", { className: "fi-mc-mini", children: [
            /* @__PURE__ */ jsx2("dt", { children: "Contexto" }),
            /* @__PURE__ */ jsx2("dd", { children: formatCount(model.context_window) })
          ] })
        ] }),
        /* @__PURE__ */ jsxs2("div", { className: "fi-mc-card-foot", children: [
          "Actualizado: ",
          formatDate(model.updated_at, locale)
        ] })
      ]
    }
  );
}

// src/model-catalog/LLMModelGrid.tsx
import { Brain, Loader2, Plus } from "lucide-react";
import { jsx as jsx3, jsxs as jsxs3 } from "react/jsx-runtime";
function LLMModelGrid({
  models,
  loading,
  error,
  selectedId,
  onSelect,
  onEdit,
  onDeactivate,
  onToggleActive,
  onTest,
  onRetry,
  onCreateFirst,
  locale
}) {
  useModelCatalogStyle();
  if (loading) {
    return /* @__PURE__ */ jsxs3("div", { className: `${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-empty`, role: "status", children: [
      /* @__PURE__ */ jsx3(Loader2, { size: 40, className: "fi-admin-spin", "aria-hidden": "true" }),
      /* @__PURE__ */ jsx3("p", { children: "Cargando modelos..." })
    ] });
  }
  if (error) {
    return /* @__PURE__ */ jsx3("div", { className: `${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-empty`, children: /* @__PURE__ */ jsx3(
      AdminAlert,
      {
        action: /* @__PURE__ */ jsx3(AdminButton, { variant: "danger", onClick: onRetry, children: "Reintentar" }),
        children: error
      }
    ) });
  }
  if (models.length === 0) {
    return /* @__PURE__ */ jsxs3("div", { className: `${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-empty`, children: [
      /* @__PURE__ */ jsx3(Brain, { size: 56, "aria-hidden": "true" }),
      /* @__PURE__ */ jsx3("h3", { children: "No hay modelos configurados" }),
      /* @__PURE__ */ jsx3("p", { children: "Los modelos LLM definen qu\xE9 servicios de IA est\xE1n disponibles para asignar a las personas." }),
      onCreateFirst ? /* @__PURE__ */ jsx3(AdminButton, { variant: "primary", icon: Plus, onClick: onCreateFirst, children: "Crear primer modelo" }) : null
    ] });
  }
  return /* @__PURE__ */ jsx3("div", { className: `${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-grid`, children: models.map((model) => /* @__PURE__ */ jsx3(
    LLMModelCard,
    {
      model,
      locale,
      selected: selectedId === model.id,
      onSelect: onSelect ? () => onSelect(model.id) : void 0,
      onEdit: () => onEdit(model),
      onDeactivate: () => onDeactivate(model),
      onToggleActive: () => onToggleActive(model),
      onTest: onTest ? () => onTest(model) : void 0
    },
    model.id
  )) });
}

// src/model-catalog/LLMModelFilterBar.tsx
import { useId } from "react";
import { Filter } from "lucide-react";
import { jsx as jsx4, jsxs as jsxs4 } from "react/jsx-runtime";
function LLMModelFilterBar({
  provider,
  onProviderChange,
  includeInactive,
  onIncludeInactiveChange
}) {
  useModelCatalogStyle();
  const id = useId();
  return /* @__PURE__ */ jsxs4("div", { className: `${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-filters`, children: [
    /* @__PURE__ */ jsxs4("label", { className: "fi-mc-inline", htmlFor: id, children: [
      /* @__PURE__ */ jsx4(Filter, { size: 16, "aria-hidden": "true", className: "fi-mc-muted" }),
      /* @__PURE__ */ jsx4("span", { className: "fi-mc-label", children: "Proveedor" })
    ] }),
    /* @__PURE__ */ jsxs4(
      "select",
      {
        id,
        className: "fi-mc-input",
        value: provider,
        onChange: (e) => onProviderChange(e.target.value),
        children: [
          /* @__PURE__ */ jsx4("option", { value: "", children: "Todos los proveedores" }),
          Object.keys(PROVIDER_INFO).map((key) => /* @__PURE__ */ jsx4("option", { value: key, children: PROVIDER_INFO[key].label }, key))
        ]
      }
    ),
    /* @__PURE__ */ jsxs4("label", { className: "fi-mc-check", style: { marginLeft: "auto" }, children: [
      /* @__PURE__ */ jsx4(
        "input",
        {
          type: "checkbox",
          checked: includeInactive,
          onChange: (e) => onIncludeInactiveChange(e.target.checked)
        }
      ),
      "Mostrar inactivos"
    ] })
  ] });
}

// src/model-catalog/LLMModelFormSheet.tsx
import { useCallback, useId as useId2, useState } from "react";
import { X } from "lucide-react";

// src/model-catalog/ModelSheet.tsx
import { jsx as jsx5 } from "react/jsx-runtime";
function ModelSheet(props) {
  useModelCatalogStyle();
  return /* @__PURE__ */ jsx5(AdminSheet, { ...props, className: FI_MODEL_CATALOG_ROOT_CLASS });
}

// src/model-catalog/LLMModelFormSheet.tsx
import { jsx as jsx6, jsxs as jsxs5 } from "react/jsx-runtime";
function initialValues(model) {
  return {
    id: model?.id ?? "",
    label: model?.label ?? "",
    provider: model?.provider ?? "openai",
    cost_tier: model?.cost_tier ?? "medium",
    max_tokens: model?.max_tokens ?? 4096,
    context_window: model?.context_window ?? 128e3,
    is_active: model?.is_active ?? true,
    description: model?.description ?? ""
  };
}
function sanitizeModelId(value) {
  return value.toLowerCase().replace(/\s/g, "-");
}
function LLMModelFormSheet({ model, store, onClose, onSaved }) {
  const isCreate = !model;
  const titleId = useId2();
  const fieldId = useId2();
  const [values, setValues] = useState(() => initialValues(model));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const set = useCallback((key, value) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  }, []);
  const submit = async (e) => {
    e.preventDefault();
    if (isCreate && !values.id.trim()) return setError("El ID del modelo es requerido");
    if (!values.label.trim()) return setError("El label es requerido");
    setSaving(true);
    setError(null);
    try {
      const { id: _id, ...update } = values;
      const saved = model ? await store.updateModel(model.id, update) : await store.createModel(values);
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Error al guardar"));
    } finally {
      setSaving(false);
    }
  };
  const f = (name) => `${fieldId}-${name}`;
  return /* @__PURE__ */ jsx6(
    ModelSheet,
    {
      onDismiss: onClose,
      labelledBy: titleId,
      header: /* @__PURE__ */ jsxs5("div", { className: "fi-admin-head-row", children: [
        /* @__PURE__ */ jsx6("h2", { id: titleId, className: "fi-mc-title", children: isCreate ? "Nuevo modelo LLM" : "Editar modelo" }),
        /* @__PURE__ */ jsx6(AdminButton, { variant: "ghost", iconOnly: true, icon: X, "aria-label": "Cerrar", onClick: onClose })
      ] }),
      children: /* @__PURE__ */ jsxs5("form", { className: "fi-mc-stack", onSubmit: submit, noValidate: true, children: [
        isCreate ? /* @__PURE__ */ jsxs5("div", { className: "fi-mc-field", children: [
          /* @__PURE__ */ jsx6("label", { className: "fi-mc-label", htmlFor: f("id"), children: "ID del modelo *" }),
          /* @__PURE__ */ jsx6(
            "input",
            {
              id: f("id"),
              className: "fi-mc-input fi-mc-mono",
              value: values.id,
              placeholder: "gpt-4o-mini",
              onChange: (e) => set("id", sanitizeModelId(e.target.value))
            }
          ),
          /* @__PURE__ */ jsx6("p", { className: "fi-mc-hint", children: "Identificador \xFAnico (sin espacios, min\xFAsculas)" })
        ] }) : null,
        /* @__PURE__ */ jsxs5("div", { className: "fi-mc-field", children: [
          /* @__PURE__ */ jsx6("label", { className: "fi-mc-label", htmlFor: f("label"), children: "Label (nombre visible) *" }),
          /* @__PURE__ */ jsx6(
            "input",
            {
              id: f("label"),
              className: "fi-mc-input",
              value: values.label,
              placeholder: "GPT-4o Mini (Balance, $$)",
              onChange: (e) => set("label", e.target.value)
            }
          )
        ] }),
        /* @__PURE__ */ jsxs5("div", { className: "fi-mc-grid2", children: [
          /* @__PURE__ */ jsxs5("div", { className: "fi-mc-field", children: [
            /* @__PURE__ */ jsx6("label", { className: "fi-mc-label", htmlFor: f("provider"), children: "Proveedor" }),
            /* @__PURE__ */ jsx6(
              "select",
              {
                id: f("provider"),
                className: "fi-mc-input",
                value: values.provider,
                onChange: (e) => set("provider", e.target.value),
                children: Object.keys(PROVIDER_INFO).map((key) => /* @__PURE__ */ jsx6("option", { value: key, children: PROVIDER_INFO[key].label }, key))
              }
            )
          ] }),
          /* @__PURE__ */ jsxs5("div", { className: "fi-mc-field", children: [
            /* @__PURE__ */ jsx6("label", { className: "fi-mc-label", htmlFor: f("cost"), children: "Nivel de costo" }),
            /* @__PURE__ */ jsx6(
              "select",
              {
                id: f("cost"),
                className: "fi-mc-input",
                value: values.cost_tier,
                onChange: (e) => set("cost_tier", e.target.value),
                children: Object.keys(COST_TIER_INFO).map((key) => /* @__PURE__ */ jsxs5("option", { value: key, children: [
                  COST_TIER_INFO[key].symbol,
                  " ",
                  COST_TIER_INFO[key].label
                ] }, key))
              }
            )
          ] })
        ] }),
        /* @__PURE__ */ jsxs5("div", { className: "fi-mc-grid2", children: [
          /* @__PURE__ */ jsxs5("div", { className: "fi-mc-field", children: [
            /* @__PURE__ */ jsx6("label", { className: "fi-mc-label", htmlFor: f("max"), children: "Max tokens (output)" }),
            /* @__PURE__ */ jsx6(
              "input",
              {
                id: f("max"),
                type: "number",
                inputMode: "numeric",
                className: "fi-mc-input",
                min: 1,
                max: 1e6,
                value: values.max_tokens,
                onChange: (e) => set("max_tokens", parseInt(e.target.value, 10) || 0)
              }
            )
          ] }),
          /* @__PURE__ */ jsxs5("div", { className: "fi-mc-field", children: [
            /* @__PURE__ */ jsx6("label", { className: "fi-mc-label", htmlFor: f("ctx"), children: "Ventana de contexto" }),
            /* @__PURE__ */ jsx6(
              "input",
              {
                id: f("ctx"),
                type: "number",
                inputMode: "numeric",
                className: "fi-mc-input",
                min: 1024,
                max: 2e6,
                value: values.context_window,
                onChange: (e) => set("context_window", parseInt(e.target.value, 10) || 0)
              }
            )
          ] })
        ] }),
        /* @__PURE__ */ jsxs5("div", { className: "fi-mc-field", children: [
          /* @__PURE__ */ jsx6("label", { className: "fi-mc-label", htmlFor: f("desc"), children: "Descripci\xF3n" }),
          /* @__PURE__ */ jsx6(
            "textarea",
            {
              id: f("desc"),
              className: "fi-mc-input",
              rows: 2,
              placeholder: "Descripci\xF3n del modelo y casos de uso...",
              value: values.description ?? "",
              onChange: (e) => set("description", e.target.value)
            }
          )
        ] }),
        /* @__PURE__ */ jsxs5("label", { className: "fi-mc-check", children: [
          /* @__PURE__ */ jsx6("input", { type: "checkbox", checked: values.is_active, onChange: (e) => set("is_active", e.target.checked) }),
          "Modelo activo (disponible para selecci\xF3n)"
        ] }),
        error ? /* @__PURE__ */ jsx6(AdminAlert, { children: error }) : null,
        /* @__PURE__ */ jsxs5("div", { className: "fi-mc-grid2", children: [
          /* @__PURE__ */ jsx6(AdminButton, { onClick: onClose, children: "Cancelar" }),
          /* @__PURE__ */ jsx6(AdminButton, { type: "submit", variant: "primary", loading: saving, disabled: saving, children: isCreate ? "Crear modelo" : "Guardar cambios" })
        ] })
      ] })
    }
  );
}

// src/model-catalog/ModelTestSheet.tsx
import { useId as useId3 } from "react";
import { CheckCircle2, FlaskConical as FlaskConical2, Loader2 as Loader22, X as X2, XCircle } from "lucide-react";
import { jsx as jsx7, jsxs as jsxs6 } from "react/jsx-runtime";
function ModelTestSheet({ model, running, stage, result, error, close }) {
  const titleId = useId3();
  if (!model) return null;
  const failed = result ? !result.success : false;
  return /* @__PURE__ */ jsxs6(
    ModelSheet,
    {
      onDismiss: close,
      labelledBy: titleId,
      header: /* @__PURE__ */ jsxs6("div", { className: "fi-admin-head-row", children: [
        /* @__PURE__ */ jsxs6("h2", { id: titleId, className: "fi-mc-title", children: [
          running ? /* @__PURE__ */ jsx7(FlaskConical2, { size: 20, "aria-hidden": "true" }) : failed || error ? /* @__PURE__ */ jsx7(XCircle, { size: 20, "aria-hidden": "true" }) : /* @__PURE__ */ jsx7(CheckCircle2, { size: 20, "aria-hidden": "true" }),
          failed || error ? `Error al probar ${model.id}` : `Prueba de ${model.id}`
        ] }),
        /* @__PURE__ */ jsx7(AdminButton, { variant: "ghost", iconOnly: true, icon: X2, "aria-label": "Cerrar", onClick: close })
      ] }),
      footer: /* @__PURE__ */ jsx7("div", { className: "fi-admin-head-row", style: { justifyContent: "flex-end" }, children: /* @__PURE__ */ jsx7(AdminButton, { onClick: close, children: running ? "Cancelar" : "Cerrar" }) }),
      children: [
        running && stage ? /* @__PURE__ */ jsxs6("div", { className: "fi-mc-empty", role: "status", children: [
          /* @__PURE__ */ jsx7(Loader22, { size: 32, className: "fi-admin-spin", "aria-hidden": "true" }),
          /* @__PURE__ */ jsx7("h3", { children: stage.title }),
          /* @__PURE__ */ jsx7("p", { children: stage.text })
        ] }) : null,
        error ? /* @__PURE__ */ jsx7(AdminAlert, { children: error }) : null,
        result ? /* @__PURE__ */ jsxs6("div", { className: "fi-mc-stack", children: [
          /* @__PURE__ */ jsxs6("div", { className: "fi-mc-result", children: [
            /* @__PURE__ */ jsx7("span", { className: "fi-mc-label", children: "Prompt" }),
            /* @__PURE__ */ jsx7("p", { children: result.prompt })
          ] }),
          /* @__PURE__ */ jsxs6("div", { className: "fi-mc-result", "data-tone": result.success ? "success" : "error", children: [
            /* @__PURE__ */ jsx7("span", { className: "fi-mc-label", children: result.success ? "Respuesta del modelo" : "Error" }),
            /* @__PURE__ */ jsx7("p", { children: result.success ? result.response : result.error || "Error desconocido" })
          ] })
        ] }) : null
      ]
    }
  );
}

// src/model-catalog/SystemResourcesPanel.tsx
import { Activity, Cpu, HardDrive, Loader2 as Loader23, RefreshCw, X as X3, Zap } from "lucide-react";
import { Fragment, jsx as jsx8, jsxs as jsxs7 } from "react/jsx-runtime";
function SystemResourcesPanel({ resources, running, loading, error, refresh, unload, unloading }) {
  useModelCatalogStyle();
  return /* @__PURE__ */ jsxs7("section", { className: `${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-panel`, "aria-label": "Recursos del sistema", children: [
    /* @__PURE__ */ jsxs7("div", { className: "fi-mc-panel-head", children: [
      /* @__PURE__ */ jsxs7("h3", { className: "fi-mc-title", children: [
        /* @__PURE__ */ jsx8(Activity, { size: 20, "aria-hidden": "true" }),
        "Recursos del sistema"
      ] }),
      /* @__PURE__ */ jsx8(AdminButton, { variant: "ghost", icon: RefreshCw, loading, disabled: loading, onClick: () => void refresh(), children: "Actualizar" })
    ] }),
    error ? /* @__PURE__ */ jsx8(AdminAlert, { children: error }) : null,
    !resources ? loading ? /* @__PURE__ */ jsxs7("p", { className: "fi-mc-inline fi-mc-muted", role: "status", children: [
      /* @__PURE__ */ jsx8(Loader23, { size: 16, className: "fi-admin-spin", "aria-hidden": "true" }),
      "Cargando recursos..."
    ] }) : null : /* @__PURE__ */ jsxs7(Fragment, { children: [
      /* @__PURE__ */ jsxs7("div", { children: [
        /* @__PURE__ */ jsxs7("div", { className: "fi-mc-row-between", children: [
          /* @__PURE__ */ jsxs7("span", { className: "fi-mc-inline", children: [
            /* @__PURE__ */ jsx8(HardDrive, { size: 16, "aria-hidden": "true", className: "fi-mc-muted" }),
            "Memoria RAM"
          ] }),
          /* @__PURE__ */ jsxs7("span", { className: "fi-mc-mono", children: [
            resources.memory.used_gb.toFixed(1),
            "GB / ",
            resources.memory.total_gb.toFixed(1),
            "GB"
          ] })
        ] }),
        /* @__PURE__ */ jsx8(
          "div",
          {
            className: "fi-mc-meter",
            "data-level": usageLevel(resources.memory.percent_used),
            role: "meter",
            "aria-label": "Memoria RAM usada",
            "aria-valuemin": 0,
            "aria-valuemax": 100,
            "aria-valuenow": Math.round(resources.memory.percent_used),
            children: /* @__PURE__ */ jsx8("div", { style: { width: `${Math.min(100, resources.memory.percent_used)}%` } })
          }
        ),
        /* @__PURE__ */ jsxs7("div", { className: "fi-mc-row-between fi-mc-small", children: [
          /* @__PURE__ */ jsxs7("span", { children: [
            resources.memory.available_gb.toFixed(1),
            "GB disponible"
          ] }),
          /* @__PURE__ */ jsxs7("span", { children: [
            resources.memory.percent_used.toFixed(0),
            "% usado"
          ] })
        ] })
      ] }),
      /* @__PURE__ */ jsxs7("div", { className: "fi-mc-row-between", style: { marginTop: "0.75rem" }, children: [
        /* @__PURE__ */ jsxs7("span", { className: "fi-mc-inline", children: [
          /* @__PURE__ */ jsx8(Cpu, { size: 16, "aria-hidden": "true", className: "fi-mc-muted" }),
          "CPU: ",
          resources.cpu_percent.toFixed(0),
          "%",
          /* @__PURE__ */ jsxs7("span", { className: "fi-mc-muted", children: [
            "(",
            resources.cpu_count,
            " cores)"
          ] })
        ] }),
        /* @__PURE__ */ jsx8("span", { className: "fi-mc-muted", children: resources.platform })
      ] }),
      running ? /* @__PURE__ */ jsxs7("div", { className: "fi-mc-section", children: [
        /* @__PURE__ */ jsxs7("div", { className: "fi-mc-row-between", children: [
          /* @__PURE__ */ jsxs7("span", { className: "fi-mc-inline", children: [
            /* @__PURE__ */ jsx8(Zap, { size: 16, "aria-hidden": "true", className: "fi-mc-muted" }),
            "Modelos en memoria (Ollama)"
          ] }),
          running.ollama_available ? /* @__PURE__ */ jsxs7("span", { className: "fi-mc-inline fi-mc-small", children: [
            /* @__PURE__ */ jsx8("span", { className: "fi-mc-dot", "aria-hidden": "true" }),
            "Ollama activo"
          ] }) : /* @__PURE__ */ jsx8("span", { className: "fi-mc-small", children: "Ollama no disponible" })
        ] }),
        running.models.length === 0 ? /* @__PURE__ */ jsx8("p", { className: "fi-mc-small", children: "Sin modelos cargados \xB7 RAM libre para cargar modelos" }) : /* @__PURE__ */ jsxs7("ul", { className: "fi-mc-running", style: { listStyle: "none", padding: 0 }, children: [
          running.models.map((model) => /* @__PURE__ */ jsxs7("li", { className: "fi-mc-running-item", children: [
            /* @__PURE__ */ jsxs7("span", { className: "fi-mc-inline", children: [
              /* @__PURE__ */ jsx8("span", { className: "fi-mc-proc", "data-processor": model.processor, children: model.processor.toUpperCase() }),
              /* @__PURE__ */ jsx8("span", { className: "fi-mc-mono", children: model.name }),
              /* @__PURE__ */ jsxs7("span", { className: "fi-mc-small", children: [
                model.size_gb,
                "GB"
              ] })
            ] }),
            /* @__PURE__ */ jsxs7("span", { className: "fi-mc-inline", children: [
              /* @__PURE__ */ jsx8("span", { className: "fi-mc-small", children: formatTimeUntil(model.until) }),
              /* @__PURE__ */ jsx8(
                AdminButton,
                {
                  variant: "ghost",
                  iconOnly: true,
                  tone: "danger",
                  icon: X3,
                  loading: unloading === model.name,
                  disabled: unloading === model.name,
                  "aria-label": `Descargar ${model.name} de memoria`,
                  title: "Descargar de memoria",
                  onClick: () => void unload(model.name)
                }
              )
            ] })
          ] }, model.model_id)),
          /* @__PURE__ */ jsxs7("li", { className: "fi-mc-small", children: [
            "Total en memoria: ",
            running.total_loaded_gb.toFixed(1),
            "GB"
          ] })
        ] })
      ] }) : null
    ] })
  ] });
}

// src/model-catalog/ModelCatalogDrawer.tsx
import { useId as useId4 } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle,
  Cpu as Cpu2,
  DatabaseZap,
  Download,
  HardDrive as HardDrive2,
  Inbox,
  Keyboard,
  Library,
  Loader2 as Loader24,
  RefreshCw as RefreshCw2,
  Search,
  Sparkles,
  Trash2 as Trash22,
  X as X4
} from "lucide-react";

// src/model-catalog/useCatalogKeyboardNavigation.ts
import { useEffect, useRef, useState as useState2 } from "react";
function isEditable(target) {
  return target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));
}
function useCatalogKeyboardNavigation({ open, models, installing, onInstall }) {
  const [selectedIndex, setSelectedIndex] = useState2(-1);
  const listRef = useRef(null);
  const searchRef = useRef(null);
  useEffect(() => {
    setSelectedIndex(-1);
  }, [models.length]);
  useEffect(() => {
    if (!open) return;
    const ownsKey = (target) => target === searchRef.current || target === document.body || target === listRef.current?.closest('[role="dialog"]');
    const onKey = (e) => {
      if (e.key === "/") {
        if (isEditable(e.target)) return;
        e.preventDefault();
        searchRef.current?.focus();
        return;
      }
      if (!ownsKey(e.target)) return;
      const total = models.length;
      if (total === 0) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % total);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + total) % total);
      } else if (e.key === "Enter" && selectedIndex >= 0) {
        const model = models[selectedIndex];
        if (model && !model.is_installed && !(model.id in installing)) {
          e.preventDefault();
          onInstall(model);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, models, selectedIndex, installing, onInstall]);
  useEffect(() => {
    if (selectedIndex < 0 || !listRef.current) return;
    const items = listRef.current.querySelectorAll("[data-catalog-row]");
    items[selectedIndex]?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [selectedIndex]);
  return { selectedIndex, listRef, searchRef };
}

// src/model-catalog/useModelCatalog.ts
import { useCallback as useCallback2, useEffect as useEffect2, useMemo, useRef as useRef2, useState as useState3 } from "react";
var defaultRemoveCatalogMessage = (model) => `\xBFEliminar ${model.name}?

Se borrar\xE1 del disco. Podr\xE1s reinstalarlo despu\xE9s.`;
var idleStates = () => ({
  ollama: { status: "idle", models: [] },
  gpt4all: { status: "idle", models: [] },
  huggingface: { status: "idle", models: [] }
});
function useModelCatalog(store, {
  open,
  onModelsChanged,
  confirm = defaultModelCatalogConfirm,
  notify = silentNotify,
  removeConfirmMessage = defaultRemoveCatalogMessage
}) {
  const storeRef = useRef2(store);
  storeRef.current = store;
  const changedRef = useRef2(onModelsChanged);
  changedRef.current = onModelsChanged;
  const [sourceStates, setSourceStates] = useState3(idleStates);
  const [filter, setFilter] = useState3("all");
  const [searchQuery, setSearchQuery] = useState3("");
  const [maxSizeGb, setMaxSizeGb] = useState3(void 0);
  const [installing, setInstalling] = useState3({});
  const [installErrors, setInstallErrors] = useState3({});
  const [syncing, setSyncing] = useState3(false);
  const listAborts = useRef2({});
  const installAborts = useRef2({});
  const allModels = useMemo(() => CATALOG_SOURCES.flatMap((s) => sourceStates[s].models), [sourceStates]);
  const statuses = CATALOG_SOURCES.map((s) => sourceStates[s].status);
  const loading = statuses.includes("loading");
  const allLoaded = statuses.every((s) => s === "loaded" || s === "error");
  const allErrors = statuses.every((s) => s === "error");
  const models = useMemo(() => {
    if (filter === "installed") return allModels.filter((m) => m.is_installed);
    if (filter !== "all") return sourceStates[filter].models;
    return allModels;
  }, [allModels, sourceStates, filter]);
  const installedCount = useMemo(() => allModels.filter((m) => m.is_installed).length, [allModels]);
  const showFeatured = filter === "all" && !searchQuery;
  const featuredModels = useMemo(
    () => showFeatured ? models.filter(isFeaturedModel).slice(0, 3) : [],
    [models, showFeatured]
  );
  const displayedModels = useMemo(
    () => showFeatured ? models.filter((m) => !isFeaturedModel(m)) : models,
    [models, showFeatured]
  );
  const loadSource = useCallback2(
    async (source) => {
      listAborts.current[source]?.abort();
      const controller = new AbortController();
      listAborts.current[source] = controller;
      setSourceStates((prev) => ({ ...prev, [source]: { ...prev[source], status: "loading", error: void 0 } }));
      try {
        const list = await storeRef.current.listCatalog({
          source,
          query: searchQuery || void 0,
          maxSizeGb,
          signal: controller.signal
        });
        if (controller.signal.aborted) return;
        setSourceStates((prev) => ({ ...prev, [source]: { status: "loaded", models: list } }));
      } catch (err) {
        if (controller.signal.aborted || err instanceof Error && err.name === "AbortError") return;
        setSourceStates((prev) => ({
          ...prev,
          [source]: { status: "error", models: [], error: errorMessage(err, `Error al cargar ${source}`) }
        }));
      }
    },
    [searchQuery, maxSizeGb]
  );
  const reload = useCallback2(() => {
    setSourceStates(idleStates());
    const sources = filter === "all" || filter === "installed" ? CATALOG_SOURCES : [filter];
    sources.forEach((source) => void loadSource(source));
  }, [filter, loadSource]);
  useEffect2(() => {
    if (open) {
      reload();
      return;
    }
    for (const source of CATALOG_SOURCES) listAborts.current[source]?.abort();
  }, [open, reload]);
  useEffect2(() => {
    const lists = listAborts.current;
    const installs = installAborts.current;
    return () => {
      Object.values(lists).forEach((c) => c?.abort());
      Object.values(installs).forEach((c) => c.abort());
    };
  }, []);
  const markInstalled = useCallback2((modelId, isInstalled) => {
    setSourceStates((prev) => {
      const next = { ...prev };
      for (const source of CATALOG_SOURCES) {
        next[source] = {
          ...next[source],
          models: next[source].models.map((m) => m.id === modelId ? { ...m, is_installed: isInstalled } : m)
        };
      }
      return next;
    });
  }, []);
  const dropInstalling = (modelId) => setInstalling((prev) => {
    const next = { ...prev };
    delete next[modelId];
    return next;
  });
  const install = useCallback2(
    async (model) => {
      if (model.id in installAborts.current) return;
      const controller = new AbortController();
      installAborts.current[model.id] = controller;
      setInstalling((prev) => ({ ...prev, [model.id]: 0 }));
      setInstallErrors((prev) => {
        const next = { ...prev };
        delete next[model.id];
        return next;
      });
      try {
        await storeRef.current.installCatalogModel(model.id, {
          signal: controller.signal,
          onProgress: (p) => setInstalling((prev) => ({ ...prev, [model.id]: p.progress_percent }))
        });
      } catch (err) {
        delete installAborts.current[model.id];
        if (controller.signal.aborted) return;
        dropInstalling(model.id);
        const message = errorMessage(err, "Error al instalar el modelo");
        setInstallErrors((prev) => ({ ...prev, [model.id]: message }));
        notify("error", `${model.name}: ${message}`);
        return;
      }
      delete installAborts.current[model.id];
      dropInstalling(model.id);
      markInstalled(model.id, true);
      try {
        await storeRef.current.createModel(catalogModelToCreate(model));
        notify("success", `${model.name} instalado y registrado`);
      } catch (err) {
        notify(
          "success",
          isAlreadyRegisteredError(err) ? `${model.name} instalado (ya estaba registrado)` : `${model.name} instalado (registro manual requerido)`
        );
      }
      changedRef.current?.();
    },
    [markInstalled, notify]
  );
  const remove = useCallback2(
    async (model) => {
      if (!await confirm(removeConfirmMessage(model))) return false;
      try {
        await storeRef.current.removeCatalogModel(model.id);
        markInstalled(model.id, false);
        notify("success", `${model.name} eliminado`);
        changedRef.current?.();
        return true;
      } catch (err) {
        const message = errorMessage(err, "Error al eliminar");
        setInstallErrors((prev) => ({ ...prev, [model.id]: message }));
        notify("error", message);
        return false;
      }
    },
    [confirm, removeConfirmMessage, markInstalled, notify]
  );
  const syncInstalled = useCallback2(async () => {
    const installed = allModels.filter((m) => m.is_installed);
    if (installed.length === 0) {
      notify("error", "No hay modelos instalados para sincronizar");
      return;
    }
    setSyncing(true);
    let synced = 0;
    let skipped = 0;
    let failed = 0;
    for (const model of installed) {
      try {
        await storeRef.current.createModel(catalogModelToCreate(model));
        synced += 1;
      } catch (err) {
        if (isAlreadyRegisteredError(err)) skipped += 1;
        else failed += 1;
      }
    }
    setSyncing(false);
    if (synced > 0) {
      notify("success", `Sincronizados: ${synced} nuevos${skipped > 0 ? `, ${skipped} existentes` : ""}`);
      changedRef.current?.();
    } else if (skipped > 0) {
      notify("success", `Todos los ${skipped} modelos ya estaban registrados`);
    } else {
      notify("error", `Error al sincronizar (${failed} errores)`);
    }
  }, [allModels, notify]);
  return {
    sourceStates,
    filter,
    setFilter,
    searchQuery,
    setSearchQuery,
    maxSizeGb,
    setMaxSizeGb,
    installing,
    installErrors,
    syncing,
    allModels,
    models,
    featuredModels,
    displayedModels,
    installedCount,
    loading,
    allLoaded,
    allErrors,
    reload,
    install,
    remove,
    syncInstalled
  };
}

// src/model-catalog/ModelCatalogDrawer.tsx
import { Fragment as Fragment2, jsx as jsx9, jsxs as jsxs8 } from "react/jsx-runtime";
function ModelCatalogDrawer({
  open,
  onClose,
  store,
  onModelsChanged,
  confirm,
  notify,
  removableSources = ["ollama"]
}) {
  const titleId = useId4();
  const catalog = useModelCatalog(store, { open, onModelsChanged, confirm, notify });
  const { selectedIndex, listRef, searchRef } = useCatalogKeyboardNavigation({
    open,
    models: catalog.displayedModels,
    installing: catalog.installing,
    onInstall: catalog.install
  });
  if (!open) return null;
  const tabs = [
    { key: "all", label: "Todos", icon: Library },
    { key: "installed", label: "Instalados", icon: CheckCircle, count: catalog.installedCount },
    { key: "gpt4all", label: "GPT4All" },
    { key: "huggingface", label: "HF" },
    { key: "ollama", label: "Ollama" }
  ];
  const row = (model, extra) => /* @__PURE__ */ jsx9(
    CatalogModelRow,
    {
      model,
      featured: extra.featured,
      selected: extra.selected,
      navigable: extra.index !== void 0,
      progress: catalog.installing[model.id],
      error: catalog.installErrors[model.id],
      removable: removableSources.includes(model.source),
      onInstall: () => void catalog.install(model),
      onRemove: () => void catalog.remove(model)
    },
    model.id
  );
  return /* @__PURE__ */ jsxs8(
    ModelSheet,
    {
      onDismiss: onClose,
      labelledBy: titleId,
      placement: "side",
      bodyRef: listRef,
      header: /* @__PURE__ */ jsxs8(Fragment2, { children: [
        /* @__PURE__ */ jsxs8("div", { className: "fi-admin-head-row", children: [
          /* @__PURE__ */ jsxs8("div", { children: [
            /* @__PURE__ */ jsxs8("h2", { id: titleId, className: "fi-mc-title", children: [
              /* @__PURE__ */ jsx9(Library, { size: 22, "aria-hidden": "true" }),
              "Cat\xE1logo de modelos"
            ] }),
            /* @__PURE__ */ jsx9("p", { className: "fi-mc-subtitle", children: catalog.loading ? `Cargando... ${catalog.allModels.length} modelos` : `${catalog.allModels.length} modelos \xB7 ${catalog.installedCount} instalados` })
          ] }),
          /* @__PURE__ */ jsx9(AdminButton, { variant: "ghost", iconOnly: true, icon: X4, "aria-label": "Cerrar", onClick: onClose })
        ] }),
        /* @__PURE__ */ jsx9(SourceStatusBar, { states: catalog.sourceStates }),
        /* @__PURE__ */ jsxs8("div", { className: "fi-mc-toolbar", children: [
          /* @__PURE__ */ jsxs8("div", { className: "fi-mc-search", children: [
            /* @__PURE__ */ jsx9(Search, { size: 16, "aria-hidden": "true" }),
            /* @__PURE__ */ jsx9(
              "input",
              {
                ref: searchRef,
                type: "search",
                className: "fi-mc-input",
                "aria-label": "Buscar modelos",
                placeholder: "Buscar modelos... (presiona /)",
                value: catalog.searchQuery,
                onChange: (e) => catalog.setSearchQuery(e.target.value)
              }
            )
          ] }),
          /* @__PURE__ */ jsx9(
            "select",
            {
              className: "fi-mc-input",
              "aria-label": "Tama\xF1o m\xE1ximo",
              value: catalog.maxSizeGb?.toString() ?? "",
              onChange: (e) => catalog.setMaxSizeGb(e.target.value ? Number(e.target.value) : void 0),
              children: CATALOG_SIZE_OPTIONS.map((opt) => /* @__PURE__ */ jsx9("option", { value: opt.value, children: opt.label }, opt.value))
            }
          ),
          /* @__PURE__ */ jsx9(
            AdminButton,
            {
              iconOnly: true,
              icon: RefreshCw2,
              loading: catalog.loading,
              disabled: catalog.loading,
              "aria-label": "Recargar cat\xE1logo",
              title: "Recargar cat\xE1logo",
              onClick: catalog.reload
            }
          ),
          /* @__PURE__ */ jsx9(
            AdminButton,
            {
              iconOnly: true,
              icon: DatabaseZap,
              loading: catalog.syncing,
              disabled: catalog.loading || catalog.syncing || catalog.installedCount === 0,
              "aria-label": "Sincronizar modelos instalados",
              title: "Sincronizar modelos instalados al registro",
              onClick: () => void catalog.syncInstalled()
            }
          )
        ] }),
        /* @__PURE__ */ jsx9("div", { className: "fi-mc-tabs", role: "tablist", "aria-label": "Fuente", children: tabs.map((tab) => /* @__PURE__ */ jsxs8(
          AdminButton,
          {
            role: "tab",
            "aria-selected": catalog.filter === tab.key,
            className: "fi-mc-tab",
            icon: tab.icon,
            onClick: () => catalog.setFilter(tab.key),
            children: [
              tab.icon ? null : /* @__PURE__ */ jsx9(ProviderLogo, { provider: tab.key, size: 16 }),
              tab.label,
              tab.count !== void 0 ? /* @__PURE__ */ jsx9("span", { className: "fi-mc-count", children: tab.count }) : null
            ]
          },
          tab.key
        )) })
      ] }),
      footer: /* @__PURE__ */ jsxs8("div", { className: "fi-mc-keys", children: [
        /* @__PURE__ */ jsxs8("span", { className: "fi-mc-inline", children: [
          /* @__PURE__ */ jsx9(Keyboard, { size: 14, "aria-hidden": "true" }),
          "\u2191\u2193 navegar \xB7 Enter instalar \xB7 Esc cerrar"
        ] }),
        /* @__PURE__ */ jsx9("span", { children: "/ para buscar" })
      ] }),
      children: [
        catalog.loading && catalog.models.length === 0 ? /* @__PURE__ */ jsx9("div", { className: "fi-mc-list", role: "status", "aria-label": "Cargando cat\xE1logo", children: Array.from({ length: 5 }, (_, i) => /* @__PURE__ */ jsx9("div", { className: "fi-mc-skel" }, i)) }) : null,
        catalog.allErrors && !catalog.loading ? /* @__PURE__ */ jsx9(
          AdminAlert,
          {
            action: /* @__PURE__ */ jsx9(AdminButton, { variant: "danger", onClick: catalog.reload, children: "Reintentar" }),
            children: "Error al cargar todas las fuentes"
          }
        ) : null,
        catalog.featuredModels.length > 0 ? /* @__PURE__ */ jsxs8("section", { children: [
          /* @__PURE__ */ jsxs8("h3", { className: "fi-mc-section-title", "data-tone": "featured", children: [
            /* @__PURE__ */ jsx9(Sparkles, { size: 14, "aria-hidden": "true" }),
            "DESTACADOS"
          ] }),
          /* @__PURE__ */ jsx9("ul", { className: "fi-mc-list", children: catalog.featuredModels.map((m) => row(m, { featured: true })) })
        ] }) : null,
        catalog.displayedModels.length > 0 ? /* @__PURE__ */ jsxs8("section", { children: [
          catalog.filter === "all" && !catalog.searchQuery ? /* @__PURE__ */ jsxs8("h3", { className: "fi-mc-section-title", children: [
            "TODOS LOS MODELOS (",
            catalog.displayedModels.length,
            ")"
          ] }) : null,
          /* @__PURE__ */ jsx9("ul", { className: "fi-mc-list", children: catalog.displayedModels.map((m, index) => row(m, { index, selected: index === selectedIndex })) })
        ] }) : null,
        !catalog.loading && catalog.allLoaded && catalog.models.length === 0 && !catalog.allErrors ? /* @__PURE__ */ jsxs8("div", { className: "fi-mc-empty", children: [
          catalog.filter === "installed" ? /* @__PURE__ */ jsx9(Inbox, { size: 44, "aria-hidden": "true" }) : /* @__PURE__ */ jsx9(Search, { size: 44, "aria-hidden": "true" }),
          /* @__PURE__ */ jsx9("h3", { children: catalog.filter === "installed" ? "No hay modelos instalados" : "Sin resultados" }),
          /* @__PURE__ */ jsx9("p", { children: catalog.filter === "installed" ? "Explora el cat\xE1logo para instalar modelos." : catalog.searchQuery ? `No hay modelos que coincidan con "${catalog.searchQuery}".` : "Intenta con otros filtros." })
        ] }) : null
      ]
    }
  );
}
function SourceStatusBar({ states }) {
  return /* @__PURE__ */ jsx9("div", { className: "fi-mc-sources", children: CATALOG_SOURCES.map((source) => {
    const state = states[source];
    return /* @__PURE__ */ jsxs8("span", { className: "fi-mc-chip", "data-status": state.status, title: state.error, children: [
      state.status === "loading" ? /* @__PURE__ */ jsx9(Loader24, { size: 14, className: "fi-admin-spin", "aria-hidden": "true" }) : null,
      state.status === "error" ? /* @__PURE__ */ jsx9(AlertCircle, { size: 14, "aria-hidden": "true" }) : null,
      /* @__PURE__ */ jsx9(ProviderLogo, { provider: source, size: 14 }),
      SOURCE_INFO[source].label,
      state.status === "loading" ? /* @__PURE__ */ jsx9("span", { className: "fi-mc-count", children: "Cargando..." }) : null,
      state.status === "loaded" ? /* @__PURE__ */ jsx9("span", { className: "fi-mc-count", children: state.models.length }) : null,
      state.status === "error" ? /* @__PURE__ */ jsx9("span", { className: "fi-mc-count", children: "Error" }) : null
    ] }, source);
  }) });
}
function CatalogModelRow({
  model,
  progress,
  error,
  featured = false,
  selected = false,
  navigable = false,
  removable = false,
  onInstall,
  onRemove
}) {
  const installing = progress !== void 0;
  const percent = Math.round(progress ?? 0);
  return /* @__PURE__ */ jsxs8(
    "li",
    {
      className: "fi-mc-row",
      "data-catalog-row": navigable ? "" : void 0,
      "data-featured": featured,
      "data-installed": model.is_installed,
      "data-selected": selected,
      "aria-label": model.name,
      children: [
        /* @__PURE__ */ jsx9("span", { title: SOURCE_INFO[model.source]?.label, children: /* @__PURE__ */ jsx9(ProviderLogo, { provider: model.source, size: 24 }) }),
        /* @__PURE__ */ jsxs8("div", { className: "fi-mc-row-info", children: [
          /* @__PURE__ */ jsxs8("div", { className: "fi-mc-inline", style: { maxWidth: "100%" }, children: [
            /* @__PURE__ */ jsx9("span", { className: "fi-mc-row-name", children: model.name }),
            model.is_installed ? /* @__PURE__ */ jsxs8("span", { className: "fi-mc-badge", "data-tone": "installed", children: [
              /* @__PURE__ */ jsx9(Check, { size: 12, "aria-hidden": "true" }),
              "Instalado"
            ] }) : featured ? /* @__PURE__ */ jsx9("span", { className: "fi-mc-badge", "data-tone": "featured", children: "Popular" }) : null
          ] }),
          /* @__PURE__ */ jsxs8("div", { className: "fi-mc-row-meta", children: [
            /* @__PURE__ */ jsxs8("span", { className: "fi-mc-inline", children: [
              /* @__PURE__ */ jsx9(HardDrive2, { size: 12, "aria-hidden": "true" }),
              formatBytes(model.size_bytes)
            ] }),
            model.ram_required_gb ? /* @__PURE__ */ jsxs8("span", { className: "fi-mc-inline", children: [
              /* @__PURE__ */ jsx9(Cpu2, { size: 12, "aria-hidden": "true" }),
              model.ram_required_gb.toFixed(1),
              " GB"
            ] }) : null,
            /* @__PURE__ */ jsx9("span", { children: QUANT_INFO[model.quantization]?.label ?? model.quantization }),
            model.parameters ? /* @__PURE__ */ jsx9("span", { children: model.parameters }) : null
          ] }),
          installing ? /* @__PURE__ */ jsxs8(Fragment2, { children: [
            /* @__PURE__ */ jsx9(
              "div",
              {
                className: "fi-mc-meter",
                "data-tone": "catalog",
                role: "progressbar",
                "aria-label": `Descarga de ${model.name}`,
                "aria-valuemin": 0,
                "aria-valuemax": 100,
                "aria-valuenow": percent,
                children: /* @__PURE__ */ jsx9("div", { style: { width: `${percent}%` } })
              }
            ),
            /* @__PURE__ */ jsxs8("span", { className: "fi-mc-small", children: [
              "Instalando... ",
              percent,
              "%"
            ] })
          ] }) : null,
          error ? /* @__PURE__ */ jsx9("p", { className: "fi-mc-row-error", role: "alert", children: error }) : null
        ] }),
        installing ? /* @__PURE__ */ jsx9(Loader24, { size: 20, className: "fi-admin-spin", "aria-hidden": "true" }) : model.is_installed ? removable ? /* @__PURE__ */ jsx9(
          AdminButton,
          {
            variant: "ghost",
            iconOnly: true,
            tone: "danger",
            icon: Trash22,
            "aria-label": `Eliminar ${model.name}`,
            title: "Eliminar",
            onClick: onRemove
          }
        ) : null : /* @__PURE__ */ jsx9(AdminButton, { variant: "primary", icon: Download, "aria-label": `Instalar ${model.name}`, onClick: onInstall, children: "Instalar" })
      ]
    }
  );
}

// src/model-catalog/useLLMModels.ts
import { useCallback as useCallback3, useEffect as useEffect3, useRef as useRef3, useState as useState4 } from "react";
var defaultDeactivateMessage = (model) => `\xBFEliminar el modelo "${model.id}"?

El modelo ser\xE1 desactivado y dejar\xE1 de estar disponible para las personas.`;
function useLLMModels(store, {
  confirm = defaultModelCatalogConfirm,
  notify = silentNotify,
  deactivateConfirmMessage = defaultDeactivateMessage
} = {}) {
  const storeRef = useRef3(store);
  storeRef.current = store;
  const [models, setModels] = useState4([]);
  const [loading, setLoading] = useState4(true);
  const [error, setError] = useState4(null);
  const [actionError, setActionError] = useState4(null);
  const [selectedId, setSelectedId] = useState4(null);
  const [includeInactive, setIncludeInactive] = useState4(false);
  const [provider, setProvider] = useState4("");
  const reload = useCallback3(async () => {
    setLoading(true);
    setError(null);
    try {
      setModels(await storeRef.current.listModels({ includeInactive, provider: provider || void 0 }));
    } catch (err) {
      setError(errorMessage(err, "Error al cargar los modelos"));
    } finally {
      setLoading(false);
    }
  }, [includeInactive, provider]);
  useEffect3(() => {
    void reload();
  }, [reload]);
  const replace = useCallback3((model) => {
    setModels(
      (prev) => prev.some((m) => m.id === model.id) ? prev.map((m) => m.id === model.id ? model : m) : [...prev, model]
    );
  }, []);
  const fail = useCallback3(
    (err, fallback) => {
      const message = errorMessage(err, fallback);
      setActionError(message);
      notify("error", message);
    },
    [notify]
  );
  const deactivate = useCallback3(
    async (model) => {
      if (!await confirm(deactivateConfirmMessage(model))) return false;
      setActionError(null);
      try {
        await storeRef.current.deactivateModel(model.id);
        setModels((prev) => prev.map((m) => m.id === model.id ? { ...m, is_active: false } : m));
        setSelectedId((current) => current === model.id ? null : current);
        notify("success", "Modelo desactivado correctamente");
        return true;
      } catch (err) {
        fail(err, "Error al eliminar el modelo");
        return false;
      }
    },
    [confirm, deactivateConfirmMessage, notify, fail]
  );
  const toggleActive = useCallback3(
    async (model) => {
      setActionError(null);
      try {
        const updated = await storeRef.current.updateModel(model.id, { is_active: !model.is_active });
        replace(updated);
        notify("success", updated.is_active ? "Modelo activado" : "Modelo desactivado");
      } catch (err) {
        fail(err, "Error al cambiar el estado del modelo");
      }
    },
    [replace, notify, fail]
  );
  return {
    models,
    loading,
    error,
    reload,
    selectedId,
    setSelectedId,
    includeInactive,
    setIncludeInactive,
    provider,
    setProvider,
    upsert: replace,
    deactivate,
    toggleActive,
    actionError,
    clearActionError: useCallback3(() => setActionError(null), [])
  };
}

// src/model-catalog/useSystemResources.ts
import { useCallback as useCallback4, useEffect as useEffect4, useRef as useRef4, useState as useState5 } from "react";
function useSystemResources(store, { pollIntervalMs = 1e4, notify = silentNotify } = {}) {
  const storeRef = useRef4(store);
  storeRef.current = store;
  const [resources, setResources] = useState5(null);
  const [running, setRunning] = useState5(null);
  const [loading, setLoading] = useState5(true);
  const [error, setError] = useState5(null);
  const [unloading, setUnloading] = useState5(null);
  const refresh = useCallback4(async () => {
    setLoading(true);
    try {
      const [nextResources, nextRunning] = await Promise.all([
        storeRef.current.getSystemResources(),
        storeRef.current.listRunningModels()
      ]);
      setResources(nextResources);
      setRunning(nextRunning);
      setError(null);
    } catch (err) {
      setError(errorMessage(err, "No se pudieron cargar los recursos del sistema"));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect4(() => {
    void refresh();
    if (!pollIntervalMs) return;
    const timer = setInterval(() => void refresh(), pollIntervalMs);
    return () => clearInterval(timer);
  }, [refresh, pollIntervalMs]);
  const unload = useCallback4(
    async (modelName) => {
      setUnloading(modelName);
      try {
        await storeRef.current.unloadRunningModel(modelName);
        notify("success", `Modelo ${modelName} descargado de memoria`);
        await refresh();
      } catch (err) {
        const message = errorMessage(err, "Error al descargar el modelo de memoria");
        setError(message);
        notify("error", message);
      } finally {
        setUnloading(null);
      }
    },
    [notify, refresh]
  );
  return { resources, running, loading, error, refresh, unload, unloading };
}

// src/model-catalog/useModelTest.ts
import { useCallback as useCallback5, useEffect as useEffect5, useRef as useRef5, useState as useState6 } from "react";
function modelTestStages(model) {
  if (isLocalProvider(model.provider)) {
    return [
      { title: `Probando ${model.label}...`, text: "Iniciando conexi\xF3n con Ollama", delay: 0 },
      { title: "Cargando modelo en memoria...", text: "Los modelos locales requieren cargarse en RAM", delay: 3e3 },
      { title: "Generando respuesta...", text: "Esto puede tardar varios minutos para modelos grandes", delay: 15e3 },
      { title: "Procesando...", text: "El modelo est\xE1 respondiendo a la consulta", delay: 6e4 },
      { title: "Casi listo...", text: "Finalizando generaci\xF3n de respuesta", delay: 18e4 }
    ];
  }
  return [
    { title: `Probando ${model.label}...`, text: "Conectando con la API", delay: 0 },
    { title: "Generando respuesta...", text: "El modelo est\xE1 procesando la consulta", delay: 3e3 }
  ];
}
function useModelTest(store) {
  const storeRef = useRef5(store);
  storeRef.current = store;
  const timers = useRef5([]);
  const runId = useRef5(0);
  const [model, setModel] = useState6(null);
  const [running, setRunning] = useState6(false);
  const [stage, setStage] = useState6(null);
  const [result, setResult] = useState6(null);
  const [error, setError] = useState6(null);
  const clearTimers = useCallback5(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);
  useEffect5(() => clearTimers, [clearTimers]);
  const run = useCallback5(
    async (next) => {
      clearTimers();
      const id = ++runId.current;
      const stages = modelTestStages(next);
      setModel(next);
      setResult(null);
      setError(null);
      setRunning(true);
      setStage(stages[0]);
      timers.current = stages.slice(1).map((s) => setTimeout(() => setStage(s), s.delay));
      try {
        const outcome = await storeRef.current.testModel(next.id);
        if (id === runId.current) setResult(outcome);
      } catch (err) {
        if (id === runId.current) setError(errorMessage(err, "Error al probar el modelo"));
      } finally {
        if (id === runId.current) {
          clearTimers();
          setRunning(false);
          setStage(null);
        }
      }
    },
    [clearTimers]
  );
  const close = useCallback5(() => {
    runId.current += 1;
    clearTimers();
    setModel(null);
    setRunning(false);
    setStage(null);
    setResult(null);
    setError(null);
  }, [clearTimers]);
  return { model, running, stage, result, error, run, close };
}
export {
  CATALOG_SIZE_OPTIONS,
  CATALOG_SOURCES,
  COST_TIER_INFO,
  CatalogModelRow,
  FEATURED_MODEL_IDS,
  FI_MODEL_CATALOG_ROOT_CLASS,
  LLMModelCard,
  LLMModelFilterBar,
  LLMModelFormSheet,
  LLMModelGrid,
  ModelCatalogDrawer,
  ModelSheet,
  ModelTestSheet,
  PROVIDER_INFO,
  ProviderLogo,
  ProviderLogoBox,
  QUANT_INFO,
  SOURCE_INFO,
  SystemResourcesPanel,
  catalogModelToCreate,
  defaultDeactivateMessage,
  defaultModelCatalogConfirm,
  defaultRemoveCatalogMessage,
  ensureModelCatalogStyle,
  formatBytes,
  formatCount,
  formatTimeUntil,
  isLocalProvider,
  modelTestStages,
  sanitizeModelId,
  usageLevel,
  useCatalogKeyboardNavigation,
  useLLMModels,
  useModelCatalog,
  useModelCatalogStyle,
  useModelTest,
  useSystemResources
};
//# sourceMappingURL=index.js.map