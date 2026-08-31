'use client';

// src/form/Field.tsx
import { useId } from "react";

// src/form/formStyle.ts
import { useEffect } from "react";

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

// src/form/formStyle.ts
var FI_FIELD_CLASS = "fi-field";
var FI_FIELD_LABEL_CLASS = "fi-field-label";
var FI_FIELD_CONTROL_CLASS = "fi-field-control";
var FI_FIELD_HINT_CLASS = "fi-field-hint";
var FI_FIELD_ERROR_CLASS = "fi-field-error";
var FI_FIELD_GRID_CLASS = "fi-field-grid";
var FI_CHECKBOX_CLASS = "fi-field-checkbox";
var FI_CHECKBOX_LABEL_CLASS = "fi-field-checkbox-label";
var FI_FORM_ACTIONS_CLASS = "fi-form-actions";
var FI_BUTTON_CLASS = "fi-button";
var FI_BUTTON_QUIET_CLASS = "fi-button-quiet";
var FI_BUTTON_DANGER_CLASS = "fi-button-danger";
var FORM_STYLE_ID = "fi-form-style";
var CSS = `
.${FI_FIELD_CLASS} {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}
.${FI_FIELD_LABEL_CLASS} {
  font-size: var(--fi-field-label-size, ${glassTokens.itemMetaSize});
  letter-spacing: 0.3px;
  text-transform: uppercase;
  color: var(--fi-field-label-color, var(--glass-chat-text-muted, ${glassTokens.textMuted}));
}
.${FI_FIELD_LABEL_CLASS}[data-required]::after {
  content: '*';
  color: var(--fi-field-invalid, ${glassTokens.danger});
  margin-inline-start: 0.2em;
}
.${FI_FIELD_CONTROL_CLASS} {
  /* Self-declared like resourceStyle does: width:100% + padding relies on
     border-box, and og118 only ever supplied it via Tailwind preflight. The
     first consumer without Tailwind (consulta-medica web, 2026-08-31) got
     controls 21px wider than their grid columns, climbing onto the neighbour
     field. A component's geometry cannot depend on the host's reset. */
  box-sizing: border-box;
  width: 100%;
  min-height: var(--fi-touch-target, 44px);
  padding: 0.45rem 0.6rem;
  font: inherit;
  color: var(--glass-chat-text, ${glassTokens.text});
  background: var(--fi-field-fill, ${glassTokens.searchFill});
  border: 1px solid var(--fi-field-border, ${glassTokens.searchBorder});
  border-radius: var(--fi-field-radius, ${glassTokens.itemRadius});
}
textarea.${FI_FIELD_CONTROL_CLASS} {
  min-height: 5rem;
  resize: vertical;
}
.${FI_FIELD_CONTROL_CLASS}::placeholder {
  color: var(--glass-chat-text-muted, ${glassTokens.textFaint});
}
.${FI_FIELD_CONTROL_CLASS}:focus-visible {
  outline: 2px solid var(--fi-accent, ${glassTokens.accentText});
  outline-offset: 1px;
}
.${FI_FIELD_CONTROL_CLASS}:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.${FI_FIELD_CONTROL_CLASS}[aria-invalid='true'] {
  border-color: var(--fi-field-invalid, ${glassTokens.danger});
}
.${FI_FIELD_HINT_CLASS} {
  font-size: ${glassTokens.itemMetaSize};
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
}
.${FI_FIELD_ERROR_CLASS} {
  font-size: ${glassTokens.itemMetaSize};
  color: var(--fi-field-invalid, ${glassTokens.danger});
}
.${FI_FIELD_GRID_CLASS} {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(var(--fi-field-min, 12rem), 1fr));
  gap: var(--fi-field-gap, 0.75rem);
}
.${FI_CHECKBOX_CLASS} {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: var(--fi-touch-target, 44px);
}
.${FI_CHECKBOX_CLASS} input {
  inline-size: 1rem;
  block-size: 1rem;
  accent-color: var(--fi-accent, ${glassTokens.accent});
}
.${FI_CHECKBOX_LABEL_CLASS} {
  font-size: ${glassTokens.itemSubtitleSize};
  color: var(--glass-chat-text, ${glassTokens.textBody});
}
.${FI_FORM_ACTIONS_CLASS} {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
}
.${FI_BUTTON_CLASS} {
  min-height: var(--fi-touch-target, 44px);
  padding: 0.5rem 1.1rem;
  font: inherit;
  font-weight: 600;
  color: var(--fi-button-text, ${glassTokens.sendText});
  background-image: linear-gradient(
    to right,
    var(--glass-chat-accent-from, ${glassTokens.accentDeep}),
    var(--glass-chat-accent-to, ${glassTokens.accentTo})
  );
  border: 0;
  border-radius: var(--fi-field-radius, ${glassTokens.itemRadius});
  cursor: pointer;
}
.${FI_BUTTON_CLASS}:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.${FI_BUTTON_CLASS}:focus-visible {
  outline: 2px solid var(--fi-accent, ${glassTokens.accentText});
  outline-offset: 2px;
}
.${FI_BUTTON_QUIET_CLASS} {
  background-image: none;
  background: transparent;
  color: var(--fi-accent, ${glassTokens.accentText});
  border: 1px solid var(--fi-field-border, ${glassTokens.surfaceBorder});
}
.${FI_BUTTON_DANGER_CLASS} {
  background-image: none;
  background: transparent;
  color: var(--fi-field-invalid, ${glassTokens.danger});
  border: 1px solid var(--fi-field-invalid, ${glassTokens.danger});
}
`;
function ensureFormStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(FORM_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = FORM_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}
function useFormStyle() {
  useEffect(() => {
    ensureFormStyle();
  }, []);
}

// src/form/Field.tsx
import { jsx, jsxs } from "react/jsx-runtime";
function Field({ label, children, hint, error, required, className }) {
  useFormStyle();
  const base = useId();
  const controlId = `${base}-control`;
  const hintId = hint ? `${base}-hint` : void 0;
  const errorId = error ? `${base}-error` : void 0;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || void 0;
  return /* @__PURE__ */ jsxs("div", { className: className ? `${FI_FIELD_CLASS} ${className}` : FI_FIELD_CLASS, children: [
    /* @__PURE__ */ jsx(
      "label",
      {
        className: FI_FIELD_LABEL_CLASS,
        htmlFor: controlId,
        "data-required": required || void 0,
        children: label
      }
    ),
    children({
      id: controlId,
      "aria-describedby": describedBy,
      "aria-invalid": error ? true : void 0,
      "aria-required": required || void 0
    }),
    hint ? /* @__PURE__ */ jsx("span", { className: FI_FIELD_HINT_CLASS, id: hintId, children: hint }) : null,
    error ? /* @__PURE__ */ jsx("span", { className: FI_FIELD_ERROR_CLASS, id: errorId, role: "alert", children: error }) : null
  ] });
}

// src/form/Button.tsx
import { forwardRef } from "react";
import { jsx as jsx2 } from "react/jsx-runtime";
var TONE = {
  primary: "",
  quiet: FI_BUTTON_QUIET_CLASS,
  danger: FI_BUTTON_DANGER_CLASS
};
var Button = forwardRef(function Button2({ tone = "primary", className, type, ...rest }, ref) {
  useFormStyle();
  const classes = [FI_BUTTON_CLASS, TONE[tone], className].filter(Boolean).join(" ");
  return /* @__PURE__ */ jsx2("button", { ref, type: type ?? "button", className: classes, ...rest });
});

// src/form/controls.tsx
import {
  forwardRef as forwardRef2,
  useId as useId2
} from "react";
import { jsx as jsx3, jsxs as jsxs2 } from "react/jsx-runtime";
function join(...parts) {
  return parts.filter(Boolean).join(" ");
}
var TextInput = forwardRef2(
  function TextInput2({ className, ...rest }, ref) {
    useFormStyle();
    return /* @__PURE__ */ jsx3("input", { ref, className: join(FI_FIELD_CONTROL_CLASS, className), ...rest });
  }
);
var TextArea = forwardRef2(
  function TextArea2({ className, ...rest }, ref) {
    useFormStyle();
    return /* @__PURE__ */ jsx3("textarea", { ref, className: join(FI_FIELD_CONTROL_CLASS, className), ...rest });
  }
);
var Select = forwardRef2(
  function Select2({ options, placeholder, className, ...rest }, ref) {
    useFormStyle();
    return /* @__PURE__ */ jsxs2("select", { ref, className: join(FI_FIELD_CONTROL_CLASS, className), ...rest, children: [
      placeholder ? /* @__PURE__ */ jsx3("option", { value: "", disabled: true, children: placeholder }) : null,
      options.map((o) => /* @__PURE__ */ jsx3("option", { value: o.value, disabled: o.disabled, children: o.label }, o.value))
    ] });
  }
);
var Checkbox = forwardRef2(
  function Checkbox2({ label, wrapperClassName, className, id, ...rest }, ref) {
    useFormStyle();
    const auto = useId2();
    const inputId = id ?? auto;
    return /* @__PURE__ */ jsxs2("div", { className: join(FI_CHECKBOX_CLASS, wrapperClassName), children: [
      /* @__PURE__ */ jsx3("input", { ref, id: inputId, type: "checkbox", className, ...rest }),
      /* @__PURE__ */ jsx3("label", { className: FI_CHECKBOX_LABEL_CLASS, htmlFor: inputId, children: label })
    ] });
  }
);
function FieldGrid({ children, minColumn, className }) {
  useFormStyle();
  return /* @__PURE__ */ jsx3(
    "div",
    {
      className: join(FI_FIELD_GRID_CLASS, className),
      style: minColumn ? { "--fi-field-min": minColumn } : void 0,
      children
    }
  );
}
function FormActions({ children, className }) {
  useFormStyle();
  return /* @__PURE__ */ jsx3("div", { className: join(FI_FORM_ACTIONS_CLASS, className), children });
}
export {
  Button,
  Checkbox,
  FI_BUTTON_CLASS,
  FI_BUTTON_DANGER_CLASS,
  FI_BUTTON_QUIET_CLASS,
  FI_CHECKBOX_CLASS,
  FI_CHECKBOX_LABEL_CLASS,
  FI_FIELD_CLASS,
  FI_FIELD_CONTROL_CLASS,
  FI_FIELD_ERROR_CLASS,
  FI_FIELD_GRID_CLASS,
  FI_FIELD_HINT_CLASS,
  FI_FIELD_LABEL_CLASS,
  FI_FORM_ACTIONS_CLASS,
  Field,
  FieldGrid,
  FormActions,
  Select,
  TextArea,
  TextInput,
  ensureFormStyle,
  useFormStyle
};
//# sourceMappingURL=index.js.map