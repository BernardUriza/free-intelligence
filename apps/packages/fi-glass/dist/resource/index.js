'use client';

// src/resource/resourceStyle.ts
import { useEffect } from "react";

// src/theme/breakpoints.ts
var FI_MOBILE_BREAKPOINT_PX = 768;
var FI_MOBILE_QUERY = `(max-width: ${FI_MOBILE_BREAKPOINT_PX}px)`;
var FI_TOUCH_QUERY = `(pointer: coarse), ${FI_MOBILE_QUERY}`;

// src/theme/glass-tokens.generated.ts
var glassTokens = {
  /** slate-950. --glass-chat-body y --glass-chat-bg-from del preset. OJO: og118 web re-tinta --glass-chat-bg-from a #0a0e16 (--og-bg-deep en globals.css); el iPhone hoy pinta el default del preset, no el re-tint — divergencia heredada, documentada, no resuelta aquí. */
  bgDeep: "#020617",
  /** slate-900. --glass-chat-bg-mid, el centro del barrido diagonal del fondo. */
  bgMid: "#0f172a",
  /** emerald-400. --og-accent en globals.css de og118 — el acento del CONSUMER, no del preset (el preset arranca su gradiente en accentDeep). */
  accent: "#34d399",
  /** emerald-600. --glass-chat-accent-from del preset; tambien el extremo final del gradiente del botón de enviar de og118. */
  accentDeep: "#059669",
  /** cyan-600. --glass-chat-accent-to: cierra el gradiente header/CTA del preset. Hoy sólo la web lo usa. */
  accentTo: "#0891b2",
  /** emerald-300. --glass-chat-accent-text. Hoy sólo la web lo usa. */
  accentText: "#6ee7b7",
  /** --og-accent-muted en globals.css. OJO: globals.css tiene un fallback var(--og-accent-muted, #94a3b8) que no coincide con la definición de :root — bug preexistente de la web. */
  accentMuted: "#a3a3a3",
  /** red-400. --og-danger y el fallback de --fi-sidebar-item-danger en sidebarItemStyle.ts. */
  danger: "#f87171",
  /** --glass-chat-text, el texto primario sobre el vidrio. */
  text: "#ffffff",
  /** slate-200. El color de body en og118 y content.user en messages/styles.ts. La web pinta al asistente un paso más claro (slate-100, text-slate-100); el iPhone usa este mismo para ambos lados — matiz heredado. */
  textBody: "#e2e8f0",
  /** slate-400. --glass-chat-text-muted: placeholders y subtítulos. */
  textMuted: "#94a3b8",
  /** slate-500. Timestamps (MessageAuthorHeader), placeholders terciarios. */
  textFaint: "#64748b",
  /** slate-800/60. --glass-chat-surface: el relleno esmerilado del composer. */
  surface: "rgba(30, 41, 59, 0.6)",
  /** slate-600/40. --glass-chat-surface-border. */
  surfaceBorder: "rgba(71, 85, 105, 0.4)",
  /** emerald-600/32. --glass-chat-bubble-user: lavado esmeralda translúcido, no sólido — el sólido leía como verde WhatsApp. */
  bubbleUser: "rgba(5, 150, 105, 0.32)",
  /** emerald-400/25. --glass-chat-bubble-user-border. */
  bubbleUserBorder: "rgba(52, 211, 153, 0.25)",
  /** slate-800/55. --glass-chat-bubble-assistant. */
  bubbleAssistant: "rgba(30, 41, 59, 0.55)",
  /** slate-600/35. --glass-chat-bubble-border. */
  bubbleBorder: "rgba(71, 85, 105, 0.35)",
  /** --glass-chat-bg-glow del preset: el resplandor radial apenas-visible sobre el fondo. OJO: og118 web lo re-tinta a rgba(52, 211, 153, 0.06) — 'og emerald, not preset cyan'; el iPhone hoy pinta el cyan del preset — divergencia heredada, documentada, no resuelta aquí. */
  glow: "rgba(8, 145, 178, 0.07)",
  /** violet-600/80. avatar.user en messages/styles.ts: el chip de autor del usuario. */
  authorUser: "rgba(124, 58, 237, 0.8)",
  /** --fi-author-agent-fg en MessageAuthorHeader.tsx: texto oscuro sobre el chip ámbar del agente. */
  authorAgentText: "#0a0f1e",
  /** slate-300. El nombre del hablante en MessageAuthorHeader.tsx (meta.name). */
  authorName: "#cbd5e1",
  /** amber-400/80. typing.dot en messages/styles.ts. */
  typingDot: "rgba(251, 191, 36, 0.8)",
  /** amber-300/90. markdownStyles.code — el ámbar del código inline, distinto a propósito del esmeralda de los links. */
  codeInline: "rgba(252, 211, 77, 0.9)",
  /** slate-900/80. markdownStyles.pre. */
  codeBlockBg: "rgba(15, 23, 42, 0.8)",
  /** slate-700/30. Borde de markdownStyles.pre. */
  codeBlockBorder: "rgba(51, 65, 85, 0.3)",
  /** white/3. markdownStyles.blockquote. */
  quoteBg: "rgba(255, 255, 255, 0.03)",
  /** amber-500/60. El filete izquierdo del blockquote. */
  quoteAccent: "rgba(245, 158, 11, 0.6)",
  /** emerald-500/30. Borde del selector de elemento (Og118ElementSelector). */
  chipBorder: "rgba(16, 185, 129, 0.3)",
  /** white/5. Relleno del selector de elemento. */
  chipFill: "rgba(255, 255, 255, 0.05)",
  /** El tinte .is-selected de la fila del sidebar (sidebarItemStyle.ts). */
  itemSelectedBg: "rgba(52, 211, 153, 0.08)",
  /** El borde .is-selected de la fila del sidebar. */
  itemSelectedBorder: "rgba(52, 211, 153, 0.3)",
  /** white/4. Fallback de --fi-sidebar-item-hover-bg. */
  itemHover: "rgba(255, 255, 255, 0.04)",
  /** slate-600. Fallback de --fi-sidebar-item-meta-color: la hora de la fila. */
  itemMeta: "#475569",
  /** slate-500. Fallback de --fi-sidebar-item-action-color: los botones de la fila. */
  itemAction: "#64748b",
  /** white/6. Los bordes del rail (.og-sidebar, .og-sidebar-foot, .og-sidebar-archived). */
  sidebarDivider: "rgba(255, 255, 255, 0.06)",
  /** white/4. Fondo de .og-sidebar-search. */
  searchFill: "rgba(255, 255, 255, 0.04)",
  /** white/10. Borde de .og-sidebar-search. */
  searchBorder: "rgba(255, 255, 255, 0.1)",
  /** emerald-500/30. El badge del elemento seleccionado (bg-emerald-500/30). */
  badgeSelected: "rgba(16, 185, 129, 0.3)",
  /** emerald-100. Texto del badge seleccionado (text-emerald-100). */
  badgeSelectedText: "#d1fae5",
  /** emerald-500/10. Relleno del chip de engine (bg-emerald-500/10). */
  engineChipFill: "rgba(16, 185, 129, 0.1)",
  /** slate-600. Fondo del swipe de archivar — affordance NATIVA del iPhone, sin gemelo web; el tono viene de la misma escala slate del rail. */
  archiveSwipe: "#475569",
  /** Texto oscuro sobre el gradiente esmeralda del botón de enviar (.og-send-btn color). */
  sendText: "#052e1a",
  /** El outline del enviar deshabilitado (.og-send-btn:disabled): mantiene la FORMA del control en el estado que más se ve. */
  sendDisabledBorder: "rgba(148, 163, 184, 0.28)",
  /** red-600/90. .og-stop-btn: el rojo dice 'esto lo detiene'. */
  stopFill: "rgba(220, 38, 38, 0.9)",
  /** red-400/60. Borde de .og-stop-btn. */
  stopBorder: "rgba(248, 113, 113, 0.6)",
  /** red-100. Texto de .og-stop-btn. */
  stopText: "#fee2e2",
  /** --glass-chat-radius (rounded-2xl): la esquina del composer y las superficies grandes. */
  radius: "16px",
  /** La esquina de la fila del sidebar (sidebarItemStyle.ts). */
  itemRadius: "10px",
  /** Fallback de --fi-item-gap (densidad comfortable). */
  itemGap: "0.4rem",
  /** Padding vertical de la fila (primera mitad de --fi-item-padding comfortable). */
  itemPadV: "0.55rem",
  /** Padding horizontal de la fila (segunda mitad de --fi-item-padding comfortable). */
  itemPadH: "0.6rem",
  /** Tipografía del título de la fila. */
  itemTitleSize: "0.85rem",
  /** Tipografía del subtítulo/preview de la fila. */
  itemSubtitleSize: "0.75rem",
  /** Tipografía de la hora/meta de la fila. */
  itemMetaSize: "0.68rem",
  /** --glass-chat-shadow (≈ shadow-2xl). Sólo la web: en SwiftUI la elevación se compone distinto. */
  shadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
  /** --glass-chat-watermark-opacity. Sólo la web: el watermark es del shell web. */
  watermarkOpacity: "0.08"
};

// src/resource/resourceStyle.ts
var FI_INDEX_HEADER_CLASS = "fi-resource-index-header";
var FI_INDEX_TITLE_CLASS = "fi-resource-index-title";
var FI_INDEX_ACTIONS_CLASS = "fi-resource-index-actions";
var FI_SEARCH_CLASS = "fi-resource-search";
var FI_CARD_GRID_CLASS = "fi-resource-card-grid";
var FI_CARD_CLASS = "fi-resource-card";
var FI_CARD_TITLE_CLASS = "fi-resource-card-title";
var FI_CARD_DESC_CLASS = "fi-resource-card-desc";
var FI_CARD_META_CLASS = "fi-resource-card-meta";
var FI_DETAIL_CLASS = "fi-workspace-detail";
var FI_DETAIL_MAIN_CLASS = "fi-workspace-main";
var FI_DETAIL_RAIL_CLASS = "fi-workspace-rail";
var FI_RAIL_STACK_CLASS = "fi-rail-stack";
var FI_RAIL_PANEL_CLASS = "fi-rail-panel";
var FI_RAIL_PANEL_HEAD_CLASS = "fi-rail-panel-head";
var FI_RAIL_PANEL_TITLE_CLASS = "fi-rail-panel-title";
var FI_METER_CLASS = "fi-capacity-meter";
var FI_METER_TRACK_CLASS = "fi-capacity-meter-track";
var FI_METER_FILL_CLASS = "fi-capacity-meter-fill";
var FI_METER_LABEL_CLASS = "fi-capacity-meter-label";
var FI_DOC_GRID_CLASS = "fi-doc-grid";
var FI_DOC_CARD_CLASS = "fi-doc-card";
var FI_DOC_CARD_TITLE_CLASS = "fi-doc-card-title";
var FI_DOC_CARD_META_CLASS = "fi-doc-card-meta";
var FI_DOC_CARD_BADGE_CLASS = "fi-doc-card-badge";
var FI_BREADCRUMB_CLASS = "fi-workspace-breadcrumb";
var RESOURCE_STYLE_ID = "fi-resource-style";
var CSS = `
.${FI_INDEX_HEADER_CLASS} {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.${FI_INDEX_TITLE_CLASS} {
  font-size: var(--fi-resource-title-size, 1.5rem);
  font-weight: 500;
  color: var(--glass-chat-text, ${glassTokens.text});
  margin: 0;
}
.${FI_INDEX_ACTIONS_CLASS} {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.${FI_SEARCH_CLASS} {
  width: 100%;
  box-sizing: border-box;
  height: var(--fi-resource-search-height, 40px);
  border-radius: 10px;
  padding: 0 0.75rem;
  color: var(--glass-chat-text, ${glassTokens.text});
  background: var(--fi-resource-search-fill, ${glassTokens.searchFill});
  border: 1px solid var(--fi-resource-search-border, ${glassTokens.searchBorder});
  outline: none;
}
.${FI_SEARCH_CLASS}:focus-visible {
  box-shadow: 0 0 0 2px var(--glass-chat-accent-from, ${glassTokens.accentDeep});
}
.${FI_CARD_GRID_CLASS} {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
  grid-auto-rows: 1fr;
  list-style: none;
  margin: 0;
  padding: 0;
}
@media not all and ${FI_MOBILE_QUERY} {
  .${FI_CARD_GRID_CLASS} {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1.5rem;
  }
}
.${FI_CARD_CLASS} {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  height: 100%;
  box-sizing: border-box;
  border-radius: 12px;
  text-align: left;
  cursor: pointer;
  border: 1px solid var(--fi-resource-card-border, ${glassTokens.surfaceBorder});
  background: var(--fi-resource-card-bg, ${glassTokens.surface});
  color: inherit;
  text-decoration: none;
  transition: background 0.12s ease, transform 0.12s ease;
}
.${FI_CARD_CLASS}:hover {
  background: var(--fi-resource-card-hover-bg, ${glassTokens.itemHover});
}
.${FI_CARD_CLASS}:active {
  transform: scale(0.98);
}
.${FI_CARD_CLASS}:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--glass-chat-accent-from, ${glassTokens.accentDeep});
}
.${FI_CARD_TITLE_CLASS} {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--glass-chat-text, ${glassTokens.text});
}
.${FI_CARD_DESC_CLASS} {
  font-size: 0.875rem;
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.${FI_CARD_META_CLASS} {
  margin-top: auto;
  font-size: 0.8125rem;
  color: var(--fi-resource-card-meta-color, ${glassTokens.itemMeta});
}
.${FI_DETAIL_CLASS} {
  display: flex;
  align-items: flex-start;
  gap: 1.5rem;
}
.${FI_DETAIL_MAIN_CLASS} {
  flex: 1 1 auto;
  min-width: 0;
}
.${FI_DETAIL_RAIL_CLASS} {
  flex: 0 0 var(--fi-resource-rail-width, 352px);
  width: var(--fi-resource-rail-width, 352px);
  max-width: 100%;
}
@media ${FI_MOBILE_QUERY} {
  /* The rail stacks UNDER the main column \u2014 it never becomes a 352px sliver
     beside a crushed conversation. */
  .${FI_DETAIL_CLASS} {
    flex-direction: column;
    gap: 1rem;
  }
  .${FI_DETAIL_RAIL_CLASS} {
    flex: 1 1 auto;
    width: 100%;
  }
}
.${FI_RAIL_STACK_CLASS} {
  display: flex;
  flex-direction: column;
  border: 0.5px solid var(--fi-resource-rail-border, ${glassTokens.surfaceBorder});
  border-radius: 16px;
  overflow: hidden;
}
.${FI_RAIL_PANEL_CLASS} {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
}
.${FI_RAIL_PANEL_CLASS} + .${FI_RAIL_PANEL_CLASS} {
  border-top: 1px solid var(--fi-resource-rail-divider, ${glassTokens.sidebarDivider});
}
.${FI_RAIL_PANEL_HEAD_CLASS} {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.${FI_RAIL_PANEL_TITLE_CLASS} {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-chat-text, ${glassTokens.text});
}
.${FI_METER_CLASS} {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.${FI_METER_TRACK_CLASS} {
  height: 4px;
  border-radius: 2px;
  overflow: hidden;
  background: var(--fi-resource-meter-track, ${glassTokens.chipFill});
}
.${FI_METER_FILL_CLASS} {
  height: 100%;
  border-radius: 2px;
  background: var(--fi-resource-meter-fill, ${glassTokens.accent});
  transition: width 0.2s ease;
}
.${FI_METER_LABEL_CLASS} {
  font-size: 0.75rem;
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
}
.${FI_DOC_GRID_CLASS} {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.${FI_DOC_CARD_CLASS} {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-height: var(--fi-resource-doc-card-height, 120px);
  padding: 0.6rem;
  box-sizing: border-box;
  border-radius: 10px;
  text-align: left;
  border: 1px solid var(--fi-resource-card-border, ${glassTokens.surfaceBorder});
  background: var(--fi-resource-card-bg, ${glassTokens.surface});
  color: inherit;
  cursor: pointer;
}
.${FI_DOC_CARD_CLASS}:hover {
  background: var(--fi-resource-card-hover-bg, ${glassTokens.itemHover});
}
.${FI_DOC_CARD_TITLE_CLASS} {
  font-size: 0.8125rem;
  color: var(--glass-chat-text, ${glassTokens.text});
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.${FI_DOC_CARD_META_CLASS} {
  margin-top: auto;
  font-size: 0.75rem;
  color: var(--fi-resource-card-meta-color, ${glassTokens.itemMeta});
}
.${FI_DOC_CARD_BADGE_CLASS} {
  align-self: flex-start;
  font-size: 0.6875rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  border: 1px solid var(--fi-resource-badge-border, ${glassTokens.chipBorder});
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
}
@media ${FI_TOUCH_QUERY} {
  /* Measured at a phone viewport and caught below the minimum: the search box
     shipped at the 40px it was copied from, and 40 is not 44. A control the
     thumb has to hit is a touch target no matter how elegant the spec was. */
  .${FI_SEARCH_CLASS} {
    height: auto;
    min-height: var(--fi-touch-target, 44px);
  }
}
.${FI_BREADCRUMB_CLASS} {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  font-size: 0.8125rem;
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
}
.${FI_BREADCRUMB_CLASS} a,
.${FI_BREADCRUMB_CLASS} button {
  color: inherit;
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  cursor: pointer;
  text-decoration: none;
}
.${FI_BREADCRUMB_CLASS} a:hover,
.${FI_BREADCRUMB_CLASS} button:hover {
  color: var(--glass-chat-text, ${glassTokens.text});
}
`;
function ensureResourceStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(RESOURCE_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = RESOURCE_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}
function useResourceStyle() {
  useEffect(() => {
    ensureResourceStyle();
  }, []);
}

// src/resource/ResourceIndexHeader.tsx
import { jsx, jsxs } from "react/jsx-runtime";
function ResourceIndexHeader({
  title,
  sortSlot,
  actionSlot,
  className
}) {
  useResourceStyle();
  return /* @__PURE__ */ jsxs("header", { className: className ? `${FI_INDEX_HEADER_CLASS} ${className}` : FI_INDEX_HEADER_CLASS, children: [
    typeof title === "string" ? /* @__PURE__ */ jsx("h1", { className: FI_INDEX_TITLE_CLASS, children: title }) : title,
    (sortSlot || actionSlot) && /* @__PURE__ */ jsxs("div", { className: FI_INDEX_ACTIONS_CLASS, children: [
      sortSlot,
      actionSlot
    ] })
  ] });
}

// src/resource/ResourceSearchInput.tsx
import { jsx as jsx2 } from "react/jsx-runtime";
function ResourceSearchInput({
  value,
  onChange,
  placeholder,
  ariaLabel,
  className
}) {
  useResourceStyle();
  return /* @__PURE__ */ jsx2(
    "input",
    {
      type: "search",
      className: className ? `${FI_SEARCH_CLASS} ${className}` : FI_SEARCH_CLASS,
      value,
      placeholder,
      "aria-label": ariaLabel,
      onChange: (e) => onChange(e.target.value)
    }
  );
}
function filterByQuery(items, query, fields) {
  const needle = fold(query);
  if (!needle) return items;
  return items.filter(
    (item) => fields(item).some((field) => fold(field ?? "").includes(needle))
  );
}
function fold(value) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

// src/shell/touchTarget.ts
import { useEffect as useEffect2 } from "react";
var FI_TOUCH_TARGET_CLASS = "fi-touch-target";
var TOUCH_TARGET_STYLE_ID = "fi-touch-target-style";
function ensureTouchTargetStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(TOUCH_TARGET_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = TOUCH_TARGET_STYLE_ID;
  el.textContent = `
    @media ${FI_TOUCH_QUERY} {
      .${FI_TOUCH_TARGET_CLASS} {
        min-width: var(--fi-touch-target, 44px);
        min-height: var(--fi-touch-target, 44px);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
      }
    }
  `;
  document.head.appendChild(el);
}
function withTouchTarget(className) {
  return className ? `${FI_TOUCH_TARGET_CLASS} ${className}` : FI_TOUCH_TARGET_CLASS;
}

// src/resource/ResourceCardGrid.tsx
import { Fragment, jsx as jsx3, jsxs as jsxs2 } from "react/jsx-runtime";
function ResourceCard({
  title,
  description,
  meta,
  href,
  onClick,
  className
}) {
  useResourceStyle();
  const body = /* @__PURE__ */ jsxs2(Fragment, { children: [
    /* @__PURE__ */ jsx3("span", { className: FI_CARD_TITLE_CLASS, children: title }),
    description ? /* @__PURE__ */ jsx3("span", { className: FI_CARD_DESC_CLASS, children: description }) : null,
    meta != null ? /* @__PURE__ */ jsx3("span", { className: FI_CARD_META_CLASS, children: meta }) : null
  ] });
  const classes = withTouchTarget(className ? `${FI_CARD_CLASS} ${className}` : FI_CARD_CLASS);
  if (href) {
    return /* @__PURE__ */ jsx3("a", { className: classes, href, onClick, children: body });
  }
  return /* @__PURE__ */ jsx3("button", { type: "button", className: classes, onClick, children: body });
}
function ResourceCardGrid({
  children,
  emptyState,
  ariaLabel,
  className
}) {
  useResourceStyle();
  const items = children.filter(Boolean);
  if (items.length === 0 && emptyState != null) return /* @__PURE__ */ jsx3(Fragment, { children: emptyState });
  return /* @__PURE__ */ jsx3(
    "ul",
    {
      className: className ? `${FI_CARD_GRID_CLASS} ${className}` : FI_CARD_GRID_CLASS,
      "aria-label": ariaLabel,
      children: items.map((child, i) => /* @__PURE__ */ jsx3("li", { children: child }, i))
    }
  );
}

// src/resource/WorkspaceDetailLayout.tsx
import { jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
function WorkspaceDetailLayout({
  children,
  rail,
  railWidth,
  railLabel,
  className
}) {
  useResourceStyle();
  const style = railWidth != null ? {
    ["--fi-resource-rail-width"]: typeof railWidth === "number" ? `${railWidth}px` : railWidth
  } : void 0;
  return /* @__PURE__ */ jsxs3(
    "div",
    {
      className: className ? `${FI_DETAIL_CLASS} ${className}` : FI_DETAIL_CLASS,
      style,
      children: [
        /* @__PURE__ */ jsx4("div", { className: FI_DETAIL_MAIN_CLASS, children }),
        rail != null && /* @__PURE__ */ jsx4("aside", { className: FI_DETAIL_RAIL_CLASS, "aria-label": railLabel, children: rail })
      ]
    }
  );
}

// src/resource/RailPanel.tsx
import { jsx as jsx5, jsxs as jsxs4 } from "react/jsx-runtime";
function RailPanel({ title, children, actionSlot, className }) {
  useResourceStyle();
  return /* @__PURE__ */ jsxs4("section", { className: className ? `${FI_RAIL_PANEL_CLASS} ${className}` : FI_RAIL_PANEL_CLASS, children: [
    /* @__PURE__ */ jsxs4("div", { className: FI_RAIL_PANEL_HEAD_CLASS, children: [
      typeof title === "string" ? /* @__PURE__ */ jsx5("span", { className: FI_RAIL_PANEL_TITLE_CLASS, children: title }) : title,
      actionSlot
    ] }),
    children
  ] });
}
function RailPanelStack({ children, className }) {
  useResourceStyle();
  return /* @__PURE__ */ jsx5("div", { className: className ? `${FI_RAIL_STACK_CLASS} ${className}` : FI_RAIL_STACK_CLASS, children });
}

// src/resource/CapacityMeter.tsx
import { jsx as jsx6, jsxs as jsxs5 } from "react/jsx-runtime";
function CapacityMeter({ used, max, label, className }) {
  useResourceStyle();
  const bounded = max != null;
  const percent = bounded ? clamp(max === 0 ? 100 : used / max * 100) : null;
  return /* @__PURE__ */ jsxs5("div", { className: className ? `${FI_METER_CLASS} ${className}` : FI_METER_CLASS, children: [
    percent != null && /* @__PURE__ */ jsx6(
      "div",
      {
        className: FI_METER_TRACK_CLASS,
        role: "progressbar",
        "aria-valuenow": Math.round(percent),
        "aria-valuemin": 0,
        "aria-valuemax": 100,
        children: /* @__PURE__ */ jsx6("div", { className: FI_METER_FILL_CLASS, style: { width: `${percent}%` } })
      }
    ),
    /* @__PURE__ */ jsx6("span", { className: FI_METER_LABEL_CLASS, children: label(percent) })
  ] });
}
function clamp(value) {
  if (!Number.isFinite(value) || value < 0) return 0;
  return value > 100 ? 100 : value;
}

// src/resource/DocCard.tsx
import { Fragment as Fragment2, jsx as jsx7, jsxs as jsxs6 } from "react/jsx-runtime";
function DocCard({ title, meta, badge, onClick, className }) {
  useResourceStyle();
  return /* @__PURE__ */ jsxs6(
    "button",
    {
      type: "button",
      className: withTouchTarget(
        className ? `${FI_DOC_CARD_CLASS} ${className}` : FI_DOC_CARD_CLASS
      ),
      onClick,
      title,
      children: [
        badge ? /* @__PURE__ */ jsx7("span", { className: FI_DOC_CARD_BADGE_CLASS, children: badge }) : null,
        /* @__PURE__ */ jsx7("span", { className: FI_DOC_CARD_TITLE_CLASS, children: title }),
        meta != null ? /* @__PURE__ */ jsx7("span", { className: FI_DOC_CARD_META_CLASS, children: meta }) : null
      ]
    }
  );
}
function DocCardGrid({ children, emptyState, ariaLabel, className }) {
  useResourceStyle();
  const items = children.filter(Boolean);
  if (items.length === 0 && emptyState != null) return /* @__PURE__ */ jsx7(Fragment2, { children: emptyState });
  return /* @__PURE__ */ jsx7(
    "ul",
    {
      className: className ? `${FI_DOC_GRID_CLASS} ${className}` : FI_DOC_GRID_CLASS,
      "aria-label": ariaLabel,
      children: items.map((child, i) => /* @__PURE__ */ jsx7("li", { children: child }, i))
    }
  );
}

// src/resource/WorkspaceBreadcrumb.tsx
import { Fragment as Fragment3, useEffect as useEffect3 } from "react";
import { jsx as jsx8, jsxs as jsxs7 } from "react/jsx-runtime";
function WorkspaceBreadcrumb({
  crumbs,
  separator = "/",
  ariaLabel,
  className
}) {
  useResourceStyle();
  useEffect3(() => ensureTouchTargetStyle(), []);
  return /* @__PURE__ */ jsx8(
    "nav",
    {
      className: className ? `${FI_BREADCRUMB_CLASS} ${className}` : FI_BREADCRUMB_CLASS,
      "aria-label": ariaLabel,
      children: crumbs.map((crumb, i) => {
        const last = i === crumbs.length - 1;
        return /* @__PURE__ */ jsxs7(Fragment3, { children: [
          i > 0 && /* @__PURE__ */ jsx8("span", { "aria-hidden": "true", children: separator }),
          crumb.href ? /* @__PURE__ */ jsx8(
            "a",
            {
              className: withTouchTarget(),
              href: crumb.href,
              onClick: crumb.onClick,
              "aria-current": last ? "page" : void 0,
              children: crumb.label
            }
          ) : crumb.onClick ? /* @__PURE__ */ jsx8(
            "button",
            {
              type: "button",
              className: withTouchTarget(),
              onClick: crumb.onClick,
              "aria-current": last ? "page" : void 0,
              children: crumb.label
            }
          ) : /* @__PURE__ */ jsx8("span", { "aria-current": last ? "page" : void 0, children: crumb.label })
        ] }, i);
      })
    }
  );
}
export {
  CapacityMeter,
  DocCard,
  DocCardGrid,
  FI_BREADCRUMB_CLASS,
  FI_CARD_CLASS,
  FI_CARD_DESC_CLASS,
  FI_CARD_GRID_CLASS,
  FI_CARD_META_CLASS,
  FI_CARD_TITLE_CLASS,
  FI_DETAIL_CLASS,
  FI_DETAIL_MAIN_CLASS,
  FI_DETAIL_RAIL_CLASS,
  FI_DOC_CARD_BADGE_CLASS,
  FI_DOC_CARD_CLASS,
  FI_DOC_CARD_META_CLASS,
  FI_DOC_CARD_TITLE_CLASS,
  FI_DOC_GRID_CLASS,
  FI_INDEX_ACTIONS_CLASS,
  FI_INDEX_HEADER_CLASS,
  FI_INDEX_TITLE_CLASS,
  FI_METER_CLASS,
  FI_METER_FILL_CLASS,
  FI_METER_LABEL_CLASS,
  FI_METER_TRACK_CLASS,
  FI_RAIL_PANEL_CLASS,
  FI_RAIL_PANEL_HEAD_CLASS,
  FI_RAIL_PANEL_TITLE_CLASS,
  FI_RAIL_STACK_CLASS,
  FI_SEARCH_CLASS,
  RailPanel,
  RailPanelStack,
  ResourceCard,
  ResourceCardGrid,
  ResourceIndexHeader,
  ResourceSearchInput,
  WorkspaceBreadcrumb,
  WorkspaceDetailLayout,
  ensureResourceStyle,
  filterByQuery,
  useResourceStyle
};
//# sourceMappingURL=index.js.map