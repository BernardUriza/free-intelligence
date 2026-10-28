'use client';

import {
  glassTokens
} from "./chunk-LO4SF24V.js";
import {
  ensureTouchTargetStyle,
  withTouchTarget
} from "./chunk-SMPLGG7E.js";
import {
  FI_MOBILE_QUERY,
  FI_TOUCH_QUERY
} from "./chunk-HJ2CVNCV.js";

// src/admin-kit/controls.tsx
import { useEffect, useRef } from "react";
import { AlertCircle, Loader2 } from "lucide-react";

// src/admin-kit/adminKitStyle.ts
import { useInsertionEffect } from "react";
var STYLE_ID = "fi-admin-kit-style";
var ACCENT = `var(--fi-admin-accent, ${glassTokens.accent})`;
var SECONDARY = "var(--fi-admin-secondary, #a78bfa)";
var TEXT = `var(--glass-chat-text, ${glassTokens.text})`;
var DANGER = `var(--fi-admin-danger, ${glassTokens.danger})`;
var BORDER = `var(--fi-admin-border, ${glassTokens.surfaceBorder})`;
var FIELD_BG = `var(--fi-admin-field-bg, ${glassTokens.searchFill})`;
var PANEL_BG = `var(--fi-admin-panel-bg, ${glassTokens.bgMid})`;
var LINE = (side) => `border-${side}-width: 1px; border-${side}-style: solid; border-${side}-color: ${BORDER};`;
var CSS = `
.fi-admin-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; min-height: 36px;
  padding: 0.5rem 0.9rem; border-radius: 10px; font: inherit; font-size: 0.875rem; font-weight: 500; white-space: nowrap;
  cursor: pointer; color: ${TEXT}; background: ${FIELD_BG}; border-width: 1px; border-style: solid; border-color: ${BORDER};
}
.fi-admin-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.fi-admin-btn:focus-visible { outline: none; box-shadow: 0 0 0 2px ${ACCENT}; }
.fi-admin-btn[data-variant="primary"] { color: #04130d; background: ${ACCENT}; border-color: transparent; }
.fi-admin-btn[data-variant="ghost"] { background: transparent; border-color: transparent; }
.fi-admin-btn[data-variant="ghost"]:hover:not(:disabled) { background: ${glassTokens.itemHover}; }
.fi-admin-btn[data-variant="danger"] { color: ${DANGER}; background: transparent; border-color: rgba(248, 113, 113, 0.35); }
.fi-admin-btn[data-tone="danger"]:hover:not(:disabled) { color: ${DANGER}; }
.fi-admin-btn[data-tone="on"] { color: ${ACCENT}; }
.fi-admin-btn[data-tone="off"] { color: ${glassTokens.textFaint}; }
.fi-admin-btn[data-tone="secondary"] { color: ${SECONDARY}; }
.fi-admin-btn[data-icon-only] { padding: 0.4rem; min-width: 36px; }
.fi-admin-spin { animation: fi-admin-spin 1s linear infinite; }
@keyframes fi-admin-spin { to { transform: rotate(360deg); } }
.fi-admin-alert {
  display: flex; align-items: flex-start; gap: 0.5rem; margin: 0; padding: 0.75rem; border-radius: 10px;
  color: ${DANGER}; background: rgba(248, 113, 113, 0.08); border-width: 1px; border-style: solid; border-color: rgba(248, 113, 113, 0.35);
}
.fi-admin-alert > span { flex: 1 1 auto; min-width: 0; }
.fi-admin-overlay { position: fixed; inset: 0; z-index: 50; display: flex; color: ${TEXT}; font-size: 0.875rem; }
.fi-admin-backdrop { position: absolute; inset: 0; background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px); }
.fi-admin-sheet {
  position: relative; display: flex; flex-direction: column; margin: auto; width: 100%;
  max-width: var(--fi-admin-sheet-width, 40rem); max-height: calc(100dvh - 2rem); background: ${PANEL_BG};
  border-width: 1px; border-style: solid; border-color: ${BORDER}; border-radius: 16px; overflow: hidden; box-shadow: 0 24px 48px rgba(0, 0, 0, 0.45);
}
.fi-admin-sheet:focus { outline: none; }
.fi-admin-overlay[data-placement="side"] .fi-admin-sheet {
  margin: 0 0 0 auto; height: 100dvh; max-height: none; max-width: var(--fi-admin-panel-width, 48rem); border-radius: 0; border: 0; ${LINE("left")}
}
.fi-admin-sheet-head, .fi-admin-sheet-foot { flex: 0 0 auto; padding: 1rem 1.5rem; }
.fi-admin-sheet-head { ${LINE("bottom")} }
.fi-admin-sheet-foot { ${LINE("top")} }
.fi-admin-sheet-body { flex: 1 1 auto; overflow-y: auto; padding: 1.25rem 1.5rem; }
.fi-admin-head-row { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap; }
@media ${FI_MOBILE_QUERY} {
  .fi-admin-sheet, .fi-admin-overlay[data-placement="side"] .fi-admin-sheet {
    margin: 0; max-width: none; max-height: none; height: 100dvh; border-radius: 0; border: 0;
  }
  .fi-admin-sheet-head { padding: calc(0.75rem + env(safe-area-inset-top)) 0.75rem 0.75rem; }
  .fi-admin-sheet-body { padding: 1rem 0.75rem; }
  .fi-admin-sheet-foot { padding: 0.75rem 0.75rem calc(0.75rem + env(safe-area-inset-bottom)); }
}
@media ${FI_TOUCH_QUERY} {
  .fi-admin-btn { min-height: var(--fi-touch-target, 44px); }
  .fi-admin-btn[data-icon-only] { min-width: var(--fi-touch-target, 44px); }
}
`;
function ensureAdminKitStyle() {
  if (typeof document === "undefined") return;
  ensureTouchTargetStyle();
  if (document.getElementById(STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}
function useAdminKitStyle() {
  useInsertionEffect(() => {
    ensureAdminKitStyle();
  }, []);
}

// src/admin-kit/controls.tsx
import { jsx, jsxs } from "react/jsx-runtime";
function AdminButton({
  variant = "default",
  tone,
  icon: Icon,
  loading = false,
  iconOnly = false,
  className,
  children,
  ...rest
}) {
  useAdminKitStyle();
  const LeadIcon = loading ? Loader2 : Icon;
  return /* @__PURE__ */ jsxs(
    "button",
    {
      type: "button",
      ...rest,
      className: withTouchTarget(className ? `fi-admin-btn ${className}` : "fi-admin-btn"),
      "data-variant": variant,
      "data-tone": tone,
      "data-icon-only": iconOnly ? "" : void 0,
      children: [
        LeadIcon ? /* @__PURE__ */ jsx(LeadIcon, { size: 16, "aria-hidden": "true", className: loading ? "fi-admin-spin" : void 0 }) : null,
        children
      ]
    }
  );
}
function AdminAlert({ children, action }) {
  useAdminKitStyle();
  return /* @__PURE__ */ jsxs("div", { className: "fi-admin-alert", role: "alert", children: [
    /* @__PURE__ */ jsx(AlertCircle, { size: 18, "aria-hidden": "true" }),
    /* @__PURE__ */ jsx("span", { children }),
    action
  ] });
}
var openSheets = [];
var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
function trapTab(e) {
  if (e.key !== "Tab" || e.target.closest('[role="dialog"]') !== e.currentTarget) return;
  const items = [...e.currentTarget.querySelectorAll(FOCUSABLE)];
  if (items.length === 0) {
    e.preventDefault();
    return;
  }
  const first = items[0];
  const last = items[items.length - 1];
  const active = document.activeElement;
  if (e.shiftKey && (active === first || active === e.currentTarget)) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && active === last) {
    e.preventDefault();
    first.focus();
  }
}
function AdminSheet({
  onDismiss,
  labelledBy,
  placement = "center",
  className,
  header,
  footer,
  bodyRef,
  children
}) {
  useAdminKitStyle();
  const dismissRef = useRef(onDismiss);
  dismissRef.current = onDismiss;
  const dialogRef = useRef(null);
  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    if (dialog && !dialog.contains(document.activeElement)) dialog.focus();
    return () => {
      if (opener?.isConnected) opener.focus();
    };
  }, []);
  useEffect(() => {
    const token = /* @__PURE__ */ Symbol("admin-sheet");
    openSheets.push(token);
    const onKey = (e) => {
      if (e.key === "Escape" && openSheets[openSheets.length - 1] === token) dismissRef.current();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      openSheets.splice(openSheets.indexOf(token), 1);
    };
  }, []);
  return /* @__PURE__ */ jsxs("div", { className: className ? `fi-admin-overlay ${className}` : "fi-admin-overlay", "data-placement": placement, children: [
    /* @__PURE__ */ jsx("div", { className: "fi-admin-backdrop", onClick: onDismiss, "aria-hidden": "true" }),
    /* @__PURE__ */ jsxs(
      "div",
      {
        ref: dialogRef,
        className: "fi-admin-sheet",
        role: "dialog",
        "aria-modal": "true",
        "aria-labelledby": labelledBy,
        tabIndex: -1,
        onKeyDown: trapTab,
        children: [
          /* @__PURE__ */ jsx("div", { className: "fi-admin-sheet-head", children: header }),
          /* @__PURE__ */ jsx("div", { className: "fi-admin-sheet-body", ref: bodyRef, children }),
          footer ? /* @__PURE__ */ jsx("div", { className: "fi-admin-sheet-foot", children: footer }) : null
        ]
      }
    )
  ] });
}

export {
  ensureAdminKitStyle,
  useAdminKitStyle,
  AdminButton,
  AdminAlert,
  AdminSheet
};
//# sourceMappingURL=chunk-VQSI5OGB.js.map