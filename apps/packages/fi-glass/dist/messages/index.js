'use client';

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

// src/messages/normalizeStreamedMarkdown.ts
var FENCE_SPLIT = /(```[\s\S]*?(?:```|$))/;
var GLUED_HEADING = /([.!?:;,)\]"'»…])(#{1,6} )/g;
function normalizeStreamedMarkdown(content) {
  if (!content.includes("#")) return content;
  return content.split(FENCE_SPLIT).map(
    (segment, i) => i % 2 === 1 ? segment : segment.replace(GLUED_HEADING, "$1\n\n$2")
  ).join("");
}

// src/messages/MessageContent.tsx
import { jsx, jsxs } from "react/jsx-runtime";
var mdComponents = {
  p: ({ children }) => /* @__PURE__ */ jsx("p", { className: markdownStyles.p, children }),
  strong: ({ children }) => /* @__PURE__ */ jsx("strong", { className: markdownStyles.strong, children }),
  em: ({ children }) => /* @__PURE__ */ jsx("em", { className: markdownStyles.em, children }),
  code: ({ children }) => /* @__PURE__ */ jsx("code", { className: markdownStyles.code, children }),
  pre: ({ children }) => /* @__PURE__ */ jsx("pre", { className: markdownStyles.pre, children }),
  ul: ({ children }) => /* @__PURE__ */ jsx("ul", { className: markdownStyles.ul, children }),
  ol: ({ children }) => /* @__PURE__ */ jsx("ol", { className: markdownStyles.ol, children }),
  li: ({ children }) => /* @__PURE__ */ jsxs("li", { className: markdownStyles.li, children: [
    /* @__PURE__ */ jsx("span", { className: markdownStyles.bullet, children: "\u2022" }),
    /* @__PURE__ */ jsx("span", { className: "flex-1", children })
  ] }),
  h1: ({ children }) => /* @__PURE__ */ jsx("h1", { className: markdownStyles.h1, children }),
  h2: ({ children }) => /* @__PURE__ */ jsx("h2", { className: markdownStyles.h2, children }),
  h3: ({ children }) => /* @__PURE__ */ jsx("h3", { className: markdownStyles.h3, children }),
  blockquote: ({ children }) => /* @__PURE__ */ jsx("blockquote", { className: markdownStyles.blockquote, children }),
  a: ({ href, children }) => /* @__PURE__ */ jsx(
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
  return /* @__PURE__ */ jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], components: mdComponents, children: normalizeStreamedMarkdown(content) });
}
var MessageContent = memo(function MessageContent2({
  isUser,
  content,
  isStreaming = false,
  renderMarkdown = defaultRenderMarkdown
}) {
  const { content: styles } = messageStyles;
  return /* @__PURE__ */ jsxs(
    "div",
    {
      className: `${styles.base} ${isUser ? styles.user : styles.assistant} ${styles.indent}`,
      children: [
        isUser ? (
          // User: plain text, preserve whitespace
          /* @__PURE__ */ jsx("p", { className: "whitespace-pre-wrap", children: content })
        ) : (
          // Assistant: markdown (overridable)
          renderMarkdown(content)
        ),
        isStreaming && /* @__PURE__ */ jsx("span", { className: "inline-block w-1.5 h-4 bg-amber-400/80 ml-0.5 animate-pulse rounded-sm" })
      ]
    }
  );
});

// src/messages/CopyButton.tsx
import { memo as memo2, useCallback, useState } from "react";
import { Copy, Check } from "lucide-react";
import { jsx as jsx2 } from "react/jsx-runtime";
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
  const [copied, setCopied] = useState(false);
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
  return /* @__PURE__ */ jsx2(
    "button",
    {
      onClick: handleCopy,
      className: `${base} ${copied ? active : idle}`,
      title: copied ? copiedLabel : copyLabel,
      "aria-label": copied ? copiedLabel : `${copyLabel} mensaje`,
      children: copied ? /* @__PURE__ */ jsx2(Check, { className: icon }) : /* @__PURE__ */ jsx2(Copy, { className: icon })
    }
  );
});

// src/messages/MessageBubble.tsx
import { memo as memo3 } from "react";
import { jsx as jsx3, jsxs as jsxs2 } from "react/jsx-runtime";
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
  return /* @__PURE__ */ jsxs2(
    "article",
    {
      className: `${styles.base} ${styles.borderRadius} ${isUser ? styles.user : styles.assistant} ${className || ""}`,
      role: "article",
      "aria-label": ariaLabel,
      children: [
        header && /* @__PURE__ */ jsx3("div", { className: "flex items-center gap-2 mb-1", children: header }),
        reasoning && /* @__PURE__ */ jsx3("div", { className: "mt-3 mb-3", children: reasoning }),
        children,
        badge && /* @__PURE__ */ jsx3("div", { className: "mt-2", children: badge }),
        actions
      ]
    }
  );
});

// src/messages/MessageList.tsx
import { jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
function MessageList({
  groups,
  renderItem,
  renderDivider,
  containerClassName,
  groupClassName,
  header,
  footer
}) {
  return /* @__PURE__ */ jsxs3("div", { className: containerClassName, children: [
    header,
    groups.map((group) => /* @__PURE__ */ jsxs3("div", { children: [
      renderDivider?.(group.key),
      /* @__PURE__ */ jsx4("div", { className: groupClassName, children: group.items.map((item, idx) => renderItem(item, idx)) })
    ] }, group.key)),
    footer
  ] });
}
export {
  CopyButton,
  MessageBubble,
  MessageContent,
  MessageList,
  markdownStyles,
  messageStyles,
  normalizeStreamedMarkdown
};
//# sourceMappingURL=index.js.map