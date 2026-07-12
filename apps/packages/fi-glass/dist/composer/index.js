'use client';

// src/composer/AutoResizeTextarea.tsx
import {
  forwardRef,
  useEffect,
  useId,
  useImperativeHandle,
  useRef,
  useState
} from "react";
import { jsx, jsxs } from "react/jsx-runtime";
var AutoResizeTextarea = forwardRef(function AutoResizeTextarea2({
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
  const textareaRef = useRef(null);
  useImperativeHandle(ref, () => textareaRef.current);
  const [rows, setRows] = useState(1);
  const generatedId = useId();
  const resolvedId = id ?? `fi-glass-composer-${generatedId}`;
  const resolvedName = name ?? resolvedId;
  useEffect(() => {
    if (!textareaRef.current) return;
    const textarea = textareaRef.current;
    textarea.rows = 1;
    textarea.style.height = "auto";
    const computed = window.getComputedStyle(textarea);
    const parsed = parseFloat(computed.lineHeight);
    const lineHeight = Number.isFinite(parsed) && parsed > 0 ? parsed : 20;
    const newRows = Math.max(
      1,
      Math.min(Math.ceil(textarea.scrollHeight / lineHeight), maxRows)
    );
    setRows(newRows);
    textarea.rows = newRows;
    textarea.style.height = `${newRows * lineHeight}px`;
    textarea.style.width = "100%";
  }, [value, maxRows]);
  const charCount = typeof value === "string" ? value.length : 0;
  const isNearLimit = maxLength && charCount > maxLength * 0.9;
  const isOverLimit = maxLength && charCount > maxLength;
  return /* @__PURE__ */ jsxs("div", { className: `relative ${wrapperClassName}`, style: wrapperStyle, children: [
    /* @__PURE__ */ jsx(
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
    showCounter && maxLength && /* @__PURE__ */ jsxs("div", { className: isOverLimit ? "chat-char-counter-error" : isNearLimit ? "chat-char-counter-warning" : "chat-char-counter-ok", children: [
      charCount,
      "/",
      maxLength
    ] })
  ] });
});

// src/composer/Composer.tsx
import { jsx as jsx2 } from "react/jsx-runtime";
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
  return /* @__PURE__ */ jsx2("div", { className: areaClassName, children: /* @__PURE__ */ jsx2(
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
import { useEffect as useEffect2 } from "react";
import { jsx as jsx3, jsxs as jsxs2 } from "react/jsx-runtime";
var COMPOSER_FRAME_STYLE_ID = "fi-composer-frame-style";
var CSS = `
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
`;
function ensureComposerFrameStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(COMPOSER_FRAME_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = COMPOSER_FRAME_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}
function useComposerFrameStyle() {
  useEffect2(() => {
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
  footerStartClassName
}) {
  useComposerFrameStyle();
  return /* @__PURE__ */ jsxs2("div", { className, style, "data-fi-composer-frame": "", children: [
    filled(header) && /* @__PURE__ */ jsx3("div", { className: headerClassName, "data-fi-composer-slot": "header", children: header }),
    children,
    (filled(footer) || filled(footerStart)) && /* @__PURE__ */ jsxs2(
      "div",
      {
        className: footerClassName,
        style: footerStyle,
        "data-fi-composer-slot": "footer",
        children: [
          filled(footerStart) && /* @__PURE__ */ jsx3("div", { className: footerStartClassName, "data-fi-composer-slot": "footer-start", children: footerStart }),
          footer
        ]
      }
    )
  ] });
}

// src/composer/useComposerImages.ts
import { useCallback, useRef as useRef2, useState as useState2 } from "react";
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
  const [drafts, setDrafts] = useState2([]);
  const draftsRef = useRef2(drafts);
  draftsRef.current = drafts;
  const onErrorRef = useRef2(onError);
  onErrorRef.current = onError;
  const addFiles = useCallback(
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
  const remove = useCallback((id) => {
    setDrafts((prev) => prev.filter((d) => d.id !== id));
  }, []);
  const clear = useCallback(() => setDrafts([]), []);
  const toMessageImages = useCallback(
    () => draftsRef.current.map((d) => ({ mediaType: d.mediaType, data: d.data })),
    []
  );
  const handlePaste = useCallback(
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

// src/composer/ComposerImageAttachments.tsx
import { useRef as useRef3 } from "react";
import { X } from "lucide-react";
import { jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
function ComposerImageChips({
  drafts,
  onRemove,
  disabled = false,
  className,
  removeLabel = "Quitar imagen"
}) {
  if (drafts.length === 0) return null;
  return /* @__PURE__ */ jsx4(
    "div",
    {
      className,
      "data-fi-image-chips": "",
      style: { display: "flex", flexWrap: "wrap", gap: "0.5rem" },
      children: drafts.map((draft) => /* @__PURE__ */ jsxs3("div", { style: { position: "relative" }, children: [
        /* @__PURE__ */ jsx4(
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
        /* @__PURE__ */ jsx4(
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
            children: /* @__PURE__ */ jsx4(X, { size: 12, "aria-hidden": true })
          }
        )
      ] }, draft.id))
    }
  );
}
function useImagePicker(onFiles) {
  const inputRef = useRef3(null);
  const input = /* @__PURE__ */ jsx4(
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
import { Fragment, useEffect as useEffect3, useRef as useRef4, useState as useState3 } from "react";
import { createPortal } from "react-dom";
import { Fragment as Fragment2, jsx as jsx5, jsxs as jsxs4 } from "react/jsx-runtime";
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
  const [open, setOpen] = useState3(false);
  const triggerRef = useRef4(null);
  const [position, setPosition] = useState3({ top: 0, left: 0 });
  useEffect3(() => {
    if (open && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPosition({ top: rect.top - 8, left: rect.left });
    }
  }, [open]);
  useEffect3(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);
  if (actions.length === 0) return null;
  const triggerProps = triggerAttribute ? { [triggerAttribute]: "" } : {};
  return /* @__PURE__ */ jsxs4(Fragment2, { children: [
    /* @__PURE__ */ jsx5(
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
      /* @__PURE__ */ jsxs4(Fragment2, { children: [
        /* @__PURE__ */ jsx5(
          "div",
          {
            className: "fixed inset-0 z-[9998]",
            onClick: () => setOpen(false),
            "aria-hidden": "true"
          }
        ),
        /* @__PURE__ */ jsx5(
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
              const item = /* @__PURE__ */ jsxs4(
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
                    /* @__PURE__ */ jsx5("span", { children: action.label })
                  ]
                },
                action.id
              );
              const divider = action.dividerBefore ? /* @__PURE__ */ jsx5(
                "div",
                {
                  className: dividerClassName,
                  style: dividerClassName ? void 0 : { height: 1, margin: "0.25rem 0", background: "rgba(255,255,255,0.08)" }
                }
              ) : null;
              return action.wrapperClassName ? /* @__PURE__ */ jsxs4("div", { className: action.wrapperClassName, children: [
                divider,
                item
              ] }, action.id) : /* @__PURE__ */ jsxs4(Fragment, { children: [
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
import { jsx as jsx6 } from "react/jsx-runtime";
function ComposerActions({
  actions,
  disabled = false,
  label = "A\xF1adir",
  className,
  iconClassName,
  menuClassName,
  itemClassName
}) {
  return /* @__PURE__ */ jsx6(
    ActionMenu,
    {
      actions,
      trigger: /* @__PURE__ */ jsx6(Plus, { size: 18, "aria-hidden": true, className: iconClassName }),
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
export {
  AutoResizeTextarea,
  COMPOSER_IMAGE_ACCEPT,
  COMPOSER_IMAGE_MEDIA_TYPES,
  Composer,
  ComposerActions,
  ComposerFrame,
  ComposerImageChips,
  DEFAULT_MAX_IMAGES,
  ensureComposerFrameStyle,
  useComposerFrameStyle,
  useComposerImages,
  useImagePicker
};
//# sourceMappingURL=index.js.map