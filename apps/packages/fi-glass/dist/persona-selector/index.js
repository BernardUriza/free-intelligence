'use client';

// src/persona-selector/PersonaSelector.tsx
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState
} from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Check } from "lucide-react";
import { Fragment, jsx, jsxs } from "react/jsx-runtime";
var TRIGGER_DEFAULT = "flex w-full items-center justify-between rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm transition-colors";
var CONTENT_BASE = "rounded-md border border-slate-700 bg-slate-800 p-1 shadow-lg";
var ITEM_BASE = "cursor-pointer rounded-lg px-3 py-2 text-left transition-all";
function PersonaSelector({
  personas,
  selected,
  onSelect,
  getPersonaId,
  loading = false,
  getPersonaLabel,
  getPersonaDescription,
  renderPersonaIcon,
  renderPersonaBadge,
  renderPersonaMeta,
  renderTriggerValue,
  renderHeader,
  renderFooter,
  renderLoading,
  placeholder = "Seleccionar...",
  className = "relative",
  triggerClassName,
  contentClassName = "",
  ariaLabel
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  const triggerRef = useRef(null);
  const contentRef = useRef(null);
  const reactId = useId();
  const triggerId = `persona-trigger-${reactId}`;
  const contentId = `persona-content-${reactId}`;
  const close = useCallback(() => setIsOpen(false), []);
  useEffect(() => {
    if (!isOpen) return;
    const handle = (event) => {
      const target = event.target;
      if (triggerRef.current?.contains(target) || contentRef.current?.contains(target)) {
        return;
      }
      setIsOpen(false);
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [isOpen]);
  useEffect(() => {
    if (!isOpen) return;
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const baseTop = rect.bottom + window.scrollY + 4;
    const left = rect.left + window.scrollX;
    const width = rect.width;
    setPosition({ top: baseTop, left, width });
    const raf = requestAnimationFrame(() => {
      const el = contentRef.current;
      if (!el) return;
      const height = el.offsetHeight;
      const spaceBelow = window.innerHeight - rect.bottom;
      if (spaceBelow < height && rect.top > height) {
        setPosition({ top: rect.top + window.scrollY - height - 4, left, width });
      }
    });
    return () => cancelAnimationFrame(raf);
  }, [isOpen]);
  useEffect(() => {
    if (!isOpen) return;
    const raf = requestAnimationFrame(() => {
      const content2 = contentRef.current;
      if (!content2) return;
      const sel = content2.querySelector(
        '[role="option"][aria-selected="true"]'
      );
      const first = content2.querySelector('[role="option"]');
      (sel || first)?.focus();
    });
    return () => cancelAnimationFrame(raf);
  }, [isOpen]);
  const handleOptionKeyDown = (event) => {
    const key = event.key;
    if (key === "Enter" || key === " ") {
      event.preventDefault();
      event.currentTarget.click();
      return;
    }
    if (key === "Escape") {
      event.preventDefault();
      setIsOpen(false);
      triggerRef.current?.focus();
      return;
    }
    if (key === "ArrowDown" || key === "ArrowUp") {
      event.preventDefault();
      const root = event.currentTarget.closest(
        "[data-persona-content]"
      );
      const options = root ? Array.from(root.querySelectorAll('[role="option"]')) : [];
      if (!options.length) return;
      const idx = options.indexOf(event.currentTarget);
      const nextIdx = key === "ArrowDown" ? (idx + 1) % options.length : (idx - 1 + options.length) % options.length;
      options[nextIdx]?.focus();
    }
  };
  if (loading) {
    return renderLoading ? /* @__PURE__ */ jsx(Fragment, { children: renderLoading() }) : /* @__PURE__ */ jsx("div", { role: "status", "aria-live": "polite", children: "Cargando..." });
  }
  const selectedPersona = personas.find((p) => getPersonaId(p) === selected);
  const triggerInner = renderTriggerValue ? renderTriggerValue(selectedPersona, isOpen) : selectedPersona && getPersonaLabel ? getPersonaLabel(selectedPersona) : placeholder;
  const content = isOpen ? /* @__PURE__ */ jsxs(
    "div",
    {
      ref: contentRef,
      id: contentId,
      role: "listbox",
      "aria-labelledby": triggerId,
      tabIndex: -1,
      "data-persona-content": true,
      style: {
        position: "fixed",
        top: `${position.top}px`,
        left: `${position.left}px`,
        minWidth: `${position.width}px`,
        zIndex: 9999
      },
      className: `${CONTENT_BASE} ${contentClassName}`.trim(),
      children: [
        renderHeader?.({ count: personas.length }),
        personas.map((persona) => {
          const id = getPersonaId(persona);
          const isSelected = id === selected;
          const ctx = { selected: isSelected };
          const badge = renderPersonaBadge?.(persona, ctx);
          const meta = renderPersonaMeta?.(persona);
          const description = getPersonaDescription?.(persona);
          return /* @__PURE__ */ jsxs(
            "div",
            {
              role: "option",
              "aria-selected": isSelected,
              tabIndex: 0,
              onClick: () => {
                onSelect(id);
                setIsOpen(false);
              },
              onKeyDown: handleOptionKeyDown,
              className: `${ITEM_BASE} hover:bg-slate-700/60 ${isSelected ? "bg-purple-500/20 border-purple-500/50 border" : "bg-slate-700/30 border border-transparent"}`,
              children: [
                /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-2 mb-1", children: [
                  renderPersonaIcon?.(persona, ctx),
                  /* @__PURE__ */ jsx(
                    "span",
                    {
                      className: `font-medium text-sm ${isSelected ? "text-purple-200" : "text-slate-200"}`,
                      children: getPersonaLabel?.(persona) ?? id
                    }
                  ),
                  isSelected && /* @__PURE__ */ jsx(Check, { className: "w-4 h-4 fi-text-purple ml-auto" })
                ] }),
                description && /* @__PURE__ */ jsx("p", { className: "fi-text-xs mb-2 line-clamp-2", children: description }),
                (badge || meta) && /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-2 flex-wrap", children: [
                  badge,
                  meta
                ] })
              ]
            },
            id
          );
        }),
        renderFooter?.({ close })
      ]
    }
  ) : null;
  return /* @__PURE__ */ jsxs("div", { className, "data-persona-root": true, children: [
    /* @__PURE__ */ jsxs(
      "button",
      {
        ref: triggerRef,
        id: triggerId,
        type: "button",
        onClick: () => setIsOpen((v) => !v),
        "aria-haspopup": "listbox",
        "aria-expanded": isOpen,
        "aria-controls": isOpen ? contentId : void 0,
        "aria-label": ariaLabel,
        className: triggerClassName ?? TRIGGER_DEFAULT,
        children: [
          triggerInner,
          /* @__PURE__ */ jsx(
            ChevronDown,
            {
              className: `h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`
            }
          )
        ]
      }
    ),
    content && createPortal(content, document.body)
  ] });
}
export {
  PersonaSelector
};
//# sourceMappingURL=index.js.map