'use client';

// src/theme/accentClasses.ts
var ACCENT_TEXT = "text-[color:var(--fi-accent,#34d399)]";
var ACCENT_TEXT_LIGHT_HOVER = "hover:text-[color:color-mix(in_srgb,var(--fi-accent,#34d399)_70%,white)]";
var ACCENT_BG_SOFT = "bg-[color:color-mix(in_srgb,var(--fi-accent,#34d399)_20%,transparent)]";

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
      active: `${ACCENT_BG_SOFT} ${ACCENT_TEXT}`,
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
  ul: "my-2 pl-5 space-y-1.5 list-disc marker:text-slate-500",
  ol: "my-2 pl-5 space-y-1.5 list-decimal marker:text-slate-400",
  li: "pl-0.5 text-slate-200",
  h1: "text-lg font-semibold text-white mt-4 mb-2",
  h2: "text-base font-semibold text-white mt-3 mb-1.5",
  h3: "text-sm font-semibold text-slate-100 mt-2 mb-1",
  blockquote: "my-3 px-4 py-3 rounded-lg bg-white/[0.03] border border-slate-700/40 border-l-2 border-l-amber-500/60 text-slate-200 text-[13.5px]",
  // The consumer's accent, not amber: amber-400 sat one shade off inline `code`.
  link: `${ACCENT_TEXT} ${ACCENT_TEXT_LIGHT_HOVER} underline underline-offset-2 transition-colors`
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
import { useEffect, useId, useRef, useState } from "react";
import { jsx, jsxs } from "react/jsx-runtime";
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
  const contentRef = useRef(null);
  const [expanded, setExpanded] = useState(false);
  const [overflowing, setOverflowing] = useState(false);
  useEffect(() => {
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
  return /* @__PURE__ */ jsxs("div", { className, children: [
    /* @__PURE__ */ jsx(
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
    overflowing && /* @__PURE__ */ jsx(
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
import { jsx as jsx2, jsxs as jsxs2 } from "react/jsx-runtime";
var mdComponents = {
  p: ({ children }) => /* @__PURE__ */ jsx2("p", { className: markdownStyles.p, children }),
  strong: ({ children }) => /* @__PURE__ */ jsx2("strong", { className: markdownStyles.strong, children }),
  em: ({ children }) => /* @__PURE__ */ jsx2("em", { className: markdownStyles.em, children }),
  code: ({ children }) => /* @__PURE__ */ jsx2("code", { className: markdownStyles.code, children }),
  pre: ({ children }) => /* @__PURE__ */ jsx2("pre", { className: markdownStyles.pre, children }),
  ul: ({ children }) => /* @__PURE__ */ jsx2("ul", { className: markdownStyles.ul, children }),
  ol: ({ children }) => /* @__PURE__ */ jsx2("ol", { className: markdownStyles.ol, children }),
  li: ({ children }) => /* @__PURE__ */ jsx2("li", { className: markdownStyles.li, children }),
  h1: ({ children }) => /* @__PURE__ */ jsx2("h1", { className: markdownStyles.h1, children }),
  h2: ({ children }) => /* @__PURE__ */ jsx2("h2", { className: markdownStyles.h2, children }),
  h3: ({ children }) => /* @__PURE__ */ jsx2("h3", { className: markdownStyles.h3, children }),
  blockquote: ({ children }) => /* @__PURE__ */ jsx2("blockquote", { className: markdownStyles.blockquote, children }),
  a: ({ href, children }) => /* @__PURE__ */ jsx2("a", { href, className: markdownStyles.link, target: "_blank", rel: "noopener noreferrer", children })
};
function defaultRenderMarkdown(content) {
  return /* @__PURE__ */ jsx2(ReactMarkdown, { remarkPlugins: [remarkGfm, remarkBreaks], components: mdComponents, children: normalizeStreamedMarkdown(content) });
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
    /* @__PURE__ */ jsx2("p", { className: "whitespace-pre-wrap", children: content })
  ) : (
    // Assistant: markdown (overridable)
    renderMarkdown(content)
  );
  return /* @__PURE__ */ jsxs2(
    "div",
    {
      className: `${styles.base} ${isUser ? styles.user : styles.assistant} ${styles.indent}`,
      children: [
        collapsible && !isStreaming ? /* @__PURE__ */ jsx2(
          CollapsibleText,
          {
            maxHeight: collapsedMaxHeight,
            showMoreLabel,
            showLessLabel,
            toggleClassName: collapseToggleClassName,
            children: body
          }
        ) : body,
        isStreaming && /* @__PURE__ */ jsx2("span", { className: "inline-block w-1.5 h-4 bg-amber-400/80 ml-0.5 animate-pulse rounded-sm" })
      ]
    }
  );
});

// src/messages/CopyButton.tsx
import { memo as memo2, useCallback, useState as useState2 } from "react";
import { Copy, Check } from "lucide-react";

// src/shell/touchTarget.ts
import { useEffect as useEffect2 } from "react";

// src/theme/breakpoints.ts
var FI_MOBILE_BREAKPOINT_PX = 768;
var FI_MOBILE_QUERY = `(max-width: ${FI_MOBILE_BREAKPOINT_PX}px)`;
var FI_TOUCH_QUERY = `(pointer: coarse), ${FI_MOBILE_QUERY}`;

// src/shell/touchTarget.ts
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
        box-sizing: border-box;
      }
      :where(.${FI_TOUCH_TARGET_CLASS}) {
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
    }
  `;
  document.head.appendChild(el);
}
function useTouchTargetStyle() {
  useEffect2(() => {
    ensureTouchTargetStyle();
  }, []);
}

// src/messages/CopyButton.tsx
import { jsx as jsx3 } from "react/jsx-runtime";
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
  const [copied, setCopied] = useState2(false);
  useTouchTargetStyle();
  const { actions } = messageStyles;
  const base = className ?? actions.button.base;
  const idle = idleClassName ?? actions.button.idle;
  const active = activeClassName ?? actions.button.active;
  const icon = iconClassName ?? actions.icon;
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), resetMs);
    } catch (err) {
      onError?.(err);
    }
  }, [content, onError, resetMs]);
  return /* @__PURE__ */ jsx3(
    "button",
    {
      onClick: handleCopy,
      className: `${FI_TOUCH_TARGET_CLASS} ${base} ${copied ? active : idle}`,
      title: copied ? copiedLabel : copyLabel,
      "aria-label": copied ? copiedLabel : `${copyLabel} mensaje`,
      children: copied ? /* @__PURE__ */ jsx3(Check, { className: icon }) : /* @__PURE__ */ jsx3(Copy, { className: icon })
    }
  );
});

// src/messages/MessageBubble.tsx
import { memo as memo3, useEffect as useEffect4, useRef as useRef2, useState as useState3 } from "react";

// src/messages/messageActionsStyle.ts
import { useEffect as useEffect3 } from "react";
var FI_MSG_ACTIONS_CLASS = "fi-msg-actions";
var FI_MSG_FOOTER_CLASS = "fi-msg-footer";
var FI_MSG_BADGE_CLASS = "fi-msg-badge";
var MESSAGE_ACTIONS_STYLE_ID = "fi-msg-actions-style";
var CSS = `
.${FI_MSG_FOOTER_CLASS} {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  column-gap: 0.5rem;
  margin-top: 0.25rem;
}
.${FI_MSG_BADGE_CLASS} {
  min-width: 0;
}
@media (hover: hover) and (pointer: fine) {
  .${FI_MSG_ACTIONS_CLASS} {
    opacity: 0;
    transition: opacity 0.15s ease;
  }
  article:hover > .${FI_MSG_FOOTER_CLASS} > .${FI_MSG_ACTIONS_CLASS},
  .${FI_MSG_ACTIONS_CLASS}:focus-within {
    opacity: 1;
  }
}
@media (pointer: coarse) {
  .${FI_MSG_ACTIONS_CLASS} {
    display: none;
  }
  article[data-fi-last-message] > .${FI_MSG_FOOTER_CLASS} > .${FI_MSG_ACTIONS_CLASS},
  article[data-fi-actions-open] > .${FI_MSG_FOOTER_CLASS} > .${FI_MSG_ACTIONS_CLASS} {
    display: block;
  }
  article:not([data-fi-last-message]):not([data-fi-actions-open]) > .${FI_MSG_FOOTER_CLASS}:not(:has(> .${FI_MSG_BADGE_CLASS})) {
    display: none;
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
  useEffect3(() => {
    ensureMessageActionsStyle();
  }, []);
}

// src/messages/MessageBubble.tsx
import { jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
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
  const [actionsOpen, setActionsOpen] = useState3(false);
  const selfToken = useRef2({});
  useEffect4(() => {
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
  return /* @__PURE__ */ jsxs3(
    "article",
    {
      className: `fi-msg-appear ${styles.base} ${styles.borderRadius} ${isUser ? styles.user : styles.assistant} ${className || ""}`,
      role: "article",
      "aria-label": ariaLabel,
      "data-fi-last-message": isLatest || void 0,
      "data-fi-actions-open": actionsOpen || void 0,
      onClick: onBubbleClick,
      children: [
        header && /* @__PURE__ */ jsx4("div", { className: "flex items-center gap-1.5 mb-0.5", children: header }),
        reasoning && /* @__PURE__ */ jsx4("div", { className: "mt-3 mb-3", children: reasoning }),
        children,
        (badge || actions != null && actions !== false) && /* @__PURE__ */ jsxs3("div", { className: FI_MSG_FOOTER_CLASS, children: [
          badge && /* @__PURE__ */ jsx4("div", { className: FI_MSG_BADGE_CLASS, children: badge }),
          actions != null && actions !== false && /* @__PURE__ */ jsx4("div", { className: FI_MSG_ACTIONS_CLASS, children: actions })
        ] })
      ]
    }
  );
});

// src/messages/MessageImages.tsx
import { jsx as jsx5 } from "react/jsx-runtime";
function MessageImages({
  images,
  className,
  imageClassName,
  altLabel = "Imagen adjunta"
}) {
  if (!images || images.length === 0) return null;
  return /* @__PURE__ */ jsx5(
    "div",
    {
      className,
      "data-fi-message-images": "",
      style: { display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.5rem" },
      children: images.map((img, i) => /* @__PURE__ */ jsx5(
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

// src/messages/MessageReactions.tsx
import { jsx as jsx6 } from "react/jsx-runtime";
var rowStyle = {
  display: "flex",
  flexWrap: "wrap",
  gap: "0.375rem",
  marginTop: "0.5rem"
};
var chipStyle = {
  display: "inline-flex",
  alignItems: "center",
  padding: "0.125rem 0.5rem",
  borderRadius: "9999px",
  border: "1px solid var(--fi-reaction-border, rgba(127, 127, 127, 0.35))",
  background: "var(--fi-reaction-bg, rgba(127, 127, 127, 0.12))",
  fontSize: "0.9375rem",
  lineHeight: 1.4
};
function MessageReactions({
  reactions,
  className,
  chipClassName,
  ariaLabel = "Reacciones"
}) {
  const chips = (reactions ?? []).map((r) => r.trim()).filter(Boolean);
  if (chips.length === 0) return null;
  return /* @__PURE__ */ jsx6("div", { className, "data-fi-message-reactions": "", role: "list", "aria-label": ariaLabel, style: rowStyle, children: chips.map((emoji, i) => /* @__PURE__ */ jsx6("span", { role: "listitem", className: chipClassName, style: chipStyle, children: emoji }, `${emoji}-${i}`)) });
}

// src/messages/MessageAuthorHeader.tsx
import { Fragment, jsx as jsx7, jsxs as jsxs4 } from "react/jsx-runtime";
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
  return /* @__PURE__ */ jsxs4(Fragment, { children: [
    /* @__PURE__ */ jsx7(
      "span",
      {
        "aria-hidden": true,
        "data-fi-author-avatar": "",
        style: {
          ...AVATAR,
          background: isUser ? "var(--fi-author-user-bg, rgba(124,58,237,0.8))" : "var(--fi-author-agent-bg, var(--fi-accent, #34d399))",
          color: isUser ? "var(--fi-author-user-fg, #fff)" : "var(--fi-author-agent-fg, #0a0f1e)"
        },
        children: avatarToken(author)
      }
    ),
    /* @__PURE__ */ jsx7("span", { "data-fi-author-name": "", style: { fontSize: 13, fontWeight: 500, color: "#cbd5e1" }, children: author.name }),
    author.engine && /* @__PURE__ */ jsx7(
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
    time && /* @__PURE__ */ jsx7("span", { style: { fontSize: 11, color: "#64748b", fontVariantNumeric: "tabular-nums" }, children: time })
  ] });
}
function defaultMessageHeader(message, agentAuthor, userAuthor, locale) {
  const isUser = message.role === "user";
  const author = message.author ?? (isUser ? userAuthor : agentAuthor);
  return /* @__PURE__ */ jsx7(
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
import { jsx as jsx8, jsxs as jsxs5 } from "react/jsx-runtime";
function MessageModelBadge({
  model,
  title = "Generado por {model}",
  label = "Powered by"
}) {
  return /* @__PURE__ */ jsxs5(
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
        /* @__PURE__ */ jsx8("span", { style: { color: "var(--fi-accent, #34d399)" }, children: model })
      ]
    }
  );
}
function defaultMessageBadge(message) {
  if (message.role !== "assistant") return void 0;
  const model = message.trace?.model?.trim();
  if (!model) return void 0;
  return /* @__PURE__ */ jsx8(MessageModelBadge, { model });
}

// src/messages/MessageList.tsx
import { jsx as jsx9, jsxs as jsxs6 } from "react/jsx-runtime";
function MessageList({
  groups,
  renderItem,
  renderDivider,
  containerClassName,
  groupClassName,
  header,
  footer
}) {
  return /* @__PURE__ */ jsxs6("div", { className: containerClassName, children: [
    header,
    groups.map((group) => /* @__PURE__ */ jsxs6("div", { children: [
      renderDivider?.(group.key),
      /* @__PURE__ */ jsx9("div", { className: groupClassName, children: group.items.map((item, idx) => renderItem(item, idx)) })
    ] }, group.key)),
    footer
  ] });
}
export {
  CollapsibleText,
  CopyButton,
  FI_MSG_ACTIONS_CLASS,
  FI_MSG_BADGE_CLASS,
  FI_MSG_FOOTER_CLASS,
  MessageAuthorHeader,
  MessageBubble,
  MessageContent,
  MessageImages,
  MessageList,
  MessageModelBadge,
  MessageReactions,
  defaultMessageBadge,
  defaultMessageHeader,
  ensureMessageActionsStyle,
  markdownStyles,
  messageStyles,
  normalizeStreamedMarkdown,
  useMessageActionsStyle
};
//# sourceMappingURL=index.js.map