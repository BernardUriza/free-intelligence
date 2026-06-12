'use client';

// src/theme/glass-theme.ts
var glassTheme = {
  blur: "12px",
  blurCompact: "8px",
  opacity: 0.8,
  saturation: "180%",
  surfaceLight: "255, 255, 255",
  borderLight: "rgba(255, 255, 255, 0.18)",
  surfaceDark: "rgba(15, 23, 42, 0.7)",
  borderDark: "rgba(148, 163, 184, 0.2)"
};

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
  li: ({ children }) => /* @__PURE__ */ jsxs2("li", { className: markdownStyles.li, children: [
    /* @__PURE__ */ jsx2("span", { className: markdownStyles.bullet, children: "\u2022" }),
    /* @__PURE__ */ jsx2("span", { className: "flex-1", children })
  ] }),
  h1: ({ children }) => /* @__PURE__ */ jsx2("h1", { className: markdownStyles.h1, children }),
  h2: ({ children }) => /* @__PURE__ */ jsx2("h2", { className: markdownStyles.h2, children }),
  h3: ({ children }) => /* @__PURE__ */ jsx2("h3", { className: markdownStyles.h3, children }),
  blockquote: ({ children }) => /* @__PURE__ */ jsx2("blockquote", { className: markdownStyles.blockquote, children }),
  a: ({ href, children }) => /* @__PURE__ */ jsx2("a", { href, className: markdownStyles.link, target: "_blank", rel: "noopener noreferrer", children })
};
function defaultRenderMarkdown(content) {
  return /* @__PURE__ */ jsx2(ReactMarkdown, { remarkPlugins: [remarkGfm], components: mdComponents, children: normalizeStreamedMarkdown(content) });
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
      className: `${base} ${copied ? active : idle}`,
      title: copied ? copiedLabel : copyLabel,
      "aria-label": copied ? copiedLabel : `${copyLabel} mensaje`,
      children: copied ? /* @__PURE__ */ jsx3(Check, { className: icon }) : /* @__PURE__ */ jsx3(Copy, { className: icon })
    }
  );
});

// src/messages/MessageBubble.tsx
import { memo as memo3 } from "react";
import { jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
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
  return /* @__PURE__ */ jsxs3(
    "article",
    {
      className: `fi-msg-appear ${styles.base} ${styles.borderRadius} ${isUser ? styles.user : styles.assistant} ${className || ""}`,
      role: "article",
      "aria-label": ariaLabel,
      children: [
        header && /* @__PURE__ */ jsx4("div", { className: "flex items-center gap-2 mb-1", children: header }),
        reasoning && /* @__PURE__ */ jsx4("div", { className: "mt-3 mb-3", children: reasoning }),
        children,
        badge && /* @__PURE__ */ jsx4("div", { className: "mt-2", children: badge }),
        actions
      ]
    }
  );
});

// src/messages/MessageList.tsx
import { jsx as jsx5, jsxs as jsxs4 } from "react/jsx-runtime";
function MessageList({
  groups,
  renderItem,
  renderDivider,
  containerClassName,
  groupClassName,
  header,
  footer
}) {
  return /* @__PURE__ */ jsxs4("div", { className: containerClassName, children: [
    header,
    groups.map((group) => /* @__PURE__ */ jsxs4("div", { children: [
      renderDivider?.(group.key),
      /* @__PURE__ */ jsx5("div", { className: groupClassName, children: group.items.map((item, idx) => renderItem(item, idx)) })
    ] }, group.key)),
    footer
  ] });
}

// src/composer/AutoResizeTextarea.tsx
import {
  forwardRef,
  useEffect as useEffect2,
  useImperativeHandle,
  useRef as useRef2,
  useState as useState3
} from "react";
import { jsx as jsx6, jsxs as jsxs5 } from "react/jsx-runtime";
var AutoResizeTextarea = forwardRef(function AutoResizeTextarea2({
  value,
  onChange,
  maxRows = 5,
  showCounter = false,
  maxLength,
  wrapperClassName = "",
  wrapperStyle,
  className = "",
  ...props
}, ref) {
  const textareaRef = useRef2(null);
  useImperativeHandle(ref, () => textareaRef.current);
  const [rows, setRows] = useState3(1);
  useEffect2(() => {
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
  return /* @__PURE__ */ jsxs5("div", { className: `relative ${wrapperClassName}`, style: wrapperStyle, children: [
    /* @__PURE__ */ jsx6(
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
});

// src/composer/Composer.tsx
import { jsx as jsx7 } from "react/jsx-runtime";
function Composer({
  message,
  loading = false,
  placeholder = "Escribe tu mensaje...",
  onMessageChange,
  onSend,
  maxRows = 5,
  areaClassName,
  wrapperClassName,
  wrapperStyle,
  textareaClassName,
  textareaRef
}) {
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };
  return /* @__PURE__ */ jsx7("div", { className: areaClassName, children: /* @__PURE__ */ jsx7(
    AutoResizeTextarea,
    {
      ref: textareaRef,
      value: message,
      onChange: (e) => onMessageChange(e.target.value),
      onKeyDown: handleKeyDown,
      placeholder,
      disabled: loading,
      maxRows,
      showCounter: false,
      wrapperClassName,
      wrapperStyle,
      className: textareaClassName
    }
  ) });
}

// src/voice/recording/RecordingButton.tsx
import { forwardRef as forwardRef2 } from "react";
import { Loader2 } from "lucide-react";

// src/voice/recording/types.ts
var BUTTON_SIZES = {
  sm: {
    button: "rec-btn-sm",
    icon: "rec-icon-sm",
    ring: "rec-ring-sm"
  },
  md: {
    button: "rec-btn-md",
    icon: "rec-icon-md",
    ring: "rec-ring-md"
  },
  lg: {
    button: "rec-btn-lg",
    icon: "rec-icon-lg",
    ring: "rec-ring-lg"
  },
  xl: {
    button: "rec-btn-xl",
    icon: "rec-icon-xl",
    ring: "rec-ring-xl"
  }
};
var COLOR_THEMES = {
  medical: {
    idle: "rec-theme-medical-idle",
    starting: "rec-theme-medical-starting",
    recording: "rec-theme-medical-recording",
    pausing: "rec-theme-medical-pausing",
    paused: "rec-theme-medical-paused",
    resuming: "rec-theme-medical-resuming",
    processing: "rec-theme-medical-processing",
    stopping: "rec-theme-medical-stopping",
    finalized: "rec-theme-medical-finalized"
  },
  chat: {
    idle: "rec-theme-chat-idle",
    starting: "rec-theme-chat-starting",
    recording: "rec-theme-chat-recording",
    pausing: "rec-theme-chat-pausing",
    paused: "rec-theme-chat-paused",
    resuming: "rec-theme-chat-resuming",
    processing: "rec-theme-chat-processing",
    stopping: "rec-theme-chat-stopping",
    finalized: "rec-theme-chat-finalized"
  },
  minimal: {
    idle: "rec-theme-minimal-idle",
    starting: "rec-theme-minimal-starting",
    recording: "rec-theme-minimal-recording",
    pausing: "rec-theme-minimal-pausing",
    paused: "rec-theme-minimal-paused",
    resuming: "rec-theme-minimal-resuming",
    processing: "rec-theme-minimal-processing",
    stopping: "rec-theme-minimal-stopping",
    finalized: "rec-theme-minimal-finalized"
  }
};
var STATUS_TEXT_ES = {
  idle: "Presiona para comenzar",
  starting: "Iniciando...",
  recording: "Grabando...",
  pausing: "Pausando...",
  paused: "Pausado",
  resuming: "Reanudando...",
  processing: "Procesando...",
  stopping: "Finalizando...",
  finalized: "Completado"
};
var STATUS_TEXT_EN = {
  idle: "Press to start",
  starting: "Starting...",
  recording: "Recording...",
  pausing: "Pausing...",
  paused: "Paused",
  resuming: "Resuming...",
  processing: "Processing...",
  stopping: "Stopping...",
  finalized: "Complete"
};

// src/voice/recording/RecordingButton.tsx
import { jsx as jsx8 } from "react/jsx-runtime";
var RecordingButton = forwardRef2(
  function RecordingButton2({
    size = "md",
    bgColor,
    icon: Icon,
    iconSpin = false,
    iconColor = "rec-icon-white",
    disabled = false,
    onClick,
    ariaLabel,
    className = "",
    borderStyle = "",
    animate = ""
  }, ref) {
    const sizeConfig = BUTTON_SIZES[size];
    const DisplayIcon = iconSpin ? Loader2 : Icon;
    return /* @__PURE__ */ jsx8(
      "button",
      {
        ref,
        onClick,
        disabled,
        "aria-label": ariaLabel,
        className: `fi-recording-btn-base ${sizeConfig.button} ${bgColor} ${borderStyle} ${animate} ${disabled ? "rec-btn-disabled" : "rec-btn-enabled"} ${className}`,
        children: /* @__PURE__ */ jsx8(
          DisplayIcon,
          {
            className: `${sizeConfig.icon} ${iconColor} ${iconSpin ? "rec-icon-spin" : ""}`
          }
        )
      }
    );
  }
);

// src/voice/recording/PulseRings.tsx
import { motion } from "framer-motion";
import { Fragment, jsx as jsx9, jsxs as jsxs6 } from "react/jsx-runtime";
function PingRings({ color = "yellow-500" }) {
  const bgClass = `rec-pulse-bg-${color}`;
  return /* @__PURE__ */ jsxs6(Fragment, { children: [
    /* @__PURE__ */ jsx9(
      "div",
      {
        className: `rec-pulse-ping-primary ${bgClass}`
      }
    ),
    /* @__PURE__ */ jsx9(
      "div",
      {
        className: `rec-pulse-ping-secondary ${bgClass}`,
        style: { animation: "pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite" }
      }
    )
  ] });
}
function ConcentricRings({ color = "yellow-500" }) {
  const borderClass = `rec-pulse-border-${color}`;
  const rings = [
    { scale: 1.3, opacity: 0.4, delay: 0 },
    { scale: 1.5, opacity: 0.3, delay: 0.2 },
    { scale: 1.7, opacity: 0.2, delay: 0.4 }
  ];
  return /* @__PURE__ */ jsx9(Fragment, { children: rings.map((ring, i) => /* @__PURE__ */ jsx9(
    motion.div,
    {
      className: `rec-pulse-concentric ${borderClass}`,
      initial: { scale: 1, opacity: ring.opacity },
      animate: {
        scale: [1, ring.scale, 1],
        opacity: [ring.opacity, ring.opacity * 0.5, ring.opacity]
      },
      transition: {
        duration: 1.5,
        repeat: Infinity,
        ease: "easeInOut",
        delay: ring.delay
      }
    },
    i
  )) });
}
function VADRings({
  audioLevel = 0,
  isSilent = true
}) {
  const audioScale = !isSilent ? Math.max(1, 1 + audioLevel / 255 * 1) : 1;
  const ringColor = isSilent ? "rgb(239, 68, 68)" : "rgb(34, 197, 94)";
  const rings = [
    { baseScale: 1.2, opacityBase: 0.6 },
    { baseScale: 1.4, opacityBase: 0.4 },
    { baseScale: 1.6, opacityBase: 0.2 }
  ];
  return /* @__PURE__ */ jsx9(Fragment, { children: rings.map((ring, i) => /* @__PURE__ */ jsx9(
    motion.div,
    {
      className: "rec-pulse-vad",
      style: { borderColor: ringColor },
      animate: {
        scale: audioScale * ring.baseScale,
        opacity: ring.opacityBase
      },
      transition: {
        duration: 0.2,
        // Transición suave pero rápida para seguir el ritmo
        ease: "easeOut"
      }
    },
    i
  )) });
}
function PulseRings({
  style,
  color = "yellow-500",
  audioLevel = 0,
  isSilent = true,
  className = ""
}) {
  if (style === "none") return null;
  return /* @__PURE__ */ jsxs6("div", { className: `rec-pulse-container ${className}`, children: [
    style === "ping" && /* @__PURE__ */ jsx9(PingRings, { color }),
    style === "rings" && /* @__PURE__ */ jsx9(ConcentricRings, { color }),
    style === "vad" && /* @__PURE__ */ jsx9(VADRings, { audioLevel, isSilent })
  ] });
}

// src/voice/recording/RecordingTimer.tsx
import { motion as motion2 } from "framer-motion";
import { jsx as jsx10, jsxs as jsxs7 } from "react/jsx-runtime";
function formatRecordingTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}
var SIZE_CLASSES = {
  sm: "rec-timer-sm",
  md: "rec-timer-md",
  lg: "rec-timer-lg"
};
function RecordingTimer({
  time,
  visible = true,
  size = "md",
  showDot = false,
  textColor = "rec-timer-text-white",
  dotColor = "rec-timer-dot-red",
  className = ""
}) {
  if (!visible || time <= 0) return null;
  return /* @__PURE__ */ jsxs7("div", { className: `rec-timer-wrap ${SIZE_CLASSES[size]} ${className}`, children: [
    showDot && /* @__PURE__ */ jsx10(
      motion2.div,
      {
        className: `rec-timer-dot ${dotColor}`,
        animate: { opacity: [1, 0.3, 1] },
        transition: {
          duration: 1.5,
          repeat: Infinity,
          ease: "easeInOut"
        }
      }
    ),
    /* @__PURE__ */ jsx10("span", { className: `${textColor} rec-timer-value`, children: formatRecordingTime(time) })
  ] });
}

// src/voice/recording/StatusText.tsx
import { Loader2 as Loader22 } from "lucide-react";
import { motion as motion3 } from "framer-motion";
import { jsx as jsx11, jsxs as jsxs8 } from "react/jsx-runtime";
function StatusText({
  text,
  color = "rec-status-color-default",
  showLoader = false,
  animate = false,
  className = ""
}) {
  const content = /* @__PURE__ */ jsxs8("div", { className: `rec-status-wrap ${color} ${className}`, children: [
    showLoader && /* @__PURE__ */ jsx11(Loader22, { className: "rec-status-loader" }),
    /* @__PURE__ */ jsx11("p", { className: "rec-status-text", children: text })
  ] });
  if (animate) {
    return /* @__PURE__ */ jsx11(
      motion3.div,
      {
        initial: { opacity: 0.7 },
        animate: { opacity: [0.7, 1, 0.7] },
        transition: { duration: 1.5, repeat: Infinity, ease: "easeInOut" },
        children: content
      }
    );
  }
  return content;
}

// src/voice/VoiceMicButton.tsx
import { Mic, Square, Loader2 as Loader23 } from "lucide-react";
import { motion as motion4 } from "framer-motion";
import { jsx as jsx12, jsxs as jsxs9 } from "react/jsx-runtime";
function deriveState(isRecording, isTranscribing) {
  if (isTranscribing && !isRecording) return "processing";
  if (isRecording) return "recording";
  return "idle";
}
function getButtonColor(state, isSilent) {
  if (state === "recording") {
    return isSilent ? "bg-red-500 hover:bg-red-600 text-white" : "bg-green-500 hover:bg-green-600 text-white";
  }
  if (state === "processing") {
    return "bg-blue-500 text-white";
  }
  return "bg-gray-200 hover:bg-gray-300 text-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200";
}
function VoiceMicButton({
  isRecording,
  isTranscribing,
  audioLevel,
  isSilent,
  recordingTime,
  onStart,
  onStop,
  className = ""
}) {
  const state = deriveState(isRecording, isTranscribing);
  const isDisabled = isTranscribing && !isRecording;
  const handleClick = () => {
    if (isRecording) {
      onStop();
    } else if (!isTranscribing) {
      onStart();
    }
  };
  const icon = isTranscribing ? Loader23 : isRecording ? Square : Mic;
  const iconColor = state === "idle" ? "text-gray-700 dark:text-gray-200" : "text-white";
  return /* @__PURE__ */ jsxs9("div", { className: `relative inline-flex items-center gap-3 ${className}`, children: [
    /* @__PURE__ */ jsxs9("div", { className: "relative", children: [
      isRecording && /* @__PURE__ */ jsx12(
        PulseRings,
        {
          style: "vad",
          audioLevel,
          isSilent
        }
      ),
      /* @__PURE__ */ jsx12(
        motion4.div,
        {
          animate: {
            scale: isRecording && !isSilent ? [1, 1.05, 1] : 1
          },
          transition: {
            duration: 0.6,
            repeat: isRecording && !isSilent ? Infinity : 0,
            ease: "easeInOut"
          },
          children: /* @__PURE__ */ jsx12(
            RecordingButton,
            {
              size: "md",
              bgColor: getButtonColor(state, isSilent),
              icon,
              iconSpin: isTranscribing && !isRecording,
              iconColor,
              disabled: isDisabled,
              onClick: handleClick,
              ariaLabel: isRecording ? "Detener grabaci\xF3n" : "Iniciar grabaci\xF3n de voz",
              className: "relative z-10"
            }
          )
        }
      )
    ] }),
    isRecording && /* @__PURE__ */ jsx12(
      motion4.div,
      {
        initial: { opacity: 0, x: -10 },
        animate: { opacity: 1, x: 0 },
        exit: { opacity: 0, x: -10 },
        children: /* @__PURE__ */ jsx12(
          RecordingTimer,
          {
            time: recordingTime,
            size: "sm",
            showDot: true,
            textColor: "text-gray-700 dark:text-gray-300"
          }
        )
      }
    ),
    isTranscribing && !isRecording && /* @__PURE__ */ jsx12(
      motion4.div,
      {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        className: "text-sm text-blue-600 dark:fi-text-primary font-medium",
        children: "Transcribiendo..."
      }
    )
  ] });
}

// src/voice/SpeakButton.tsx
import { Volume2, Loader2 as Loader24, Play } from "lucide-react";
import { jsx as jsx13 } from "react/jsx-runtime";
var ICON_SIZE = { xs: "w-3 h-3", sm: "w-3.5 h-3.5", md: "w-4 h-4" };
var PAD_SIZE = { xs: "p-1", sm: "p-1.5", md: "p-2" };
function formatVoiceName(voiceId) {
  const match = voiceId.match(/([A-Z][a-z]+)Neural$/);
  if (match) return match[1];
  return voiceId.charAt(0).toUpperCase() + voiceId.slice(1);
}
function SpeakButton({
  content,
  voice = "nova",
  isUserMessage = false,
  onOpenPlayer,
  busy = false,
  cached = false,
  size = "sm",
  className,
  iconClassName,
  title,
  busyTitle = "Generando audio\u2026",
  cachedTitle = "Reproducir (ya generado)"
}) {
  const voiceDisplay = formatVoiceName(voice);
  const icon = iconClassName ?? ICON_SIZE[size];
  const label = busy ? busyTitle : cached ? cachedTitle : title ?? `Escuchar (${voiceDisplay})`;
  return /* @__PURE__ */ jsx13(
    "button",
    {
      type: "button",
      onClick: () => {
        if (!busy) onOpenPlayer(content, voice, isUserMessage);
      },
      disabled: busy,
      "aria-busy": busy,
      className: className ?? PAD_SIZE[size],
      title: label,
      "aria-label": busy ? busyTitle : cached ? cachedTitle : `Escuchar mensaje con voz ${voiceDisplay}`,
      children: busy ? /* @__PURE__ */ jsx13(Loader24, { className: `${icon} animate-spin` }) : cached ? /* @__PURE__ */ jsx13(Play, { className: icon }) : /* @__PURE__ */ jsx13(Volume2, { className: icon })
    }
  );
}

// src/voice/createAudioPlayer.ts
function clampSeekTarget(seconds, duration) {
  if (!Number.isFinite(seconds)) return 0;
  const lowerBounded = Math.max(0, seconds);
  if (Number.isFinite(duration) && duration > 0) {
    return Math.min(lowerBounded, duration);
  }
  return lowerBounded;
}
var INITIAL = {
  status: "idle",
  isPlaying: false,
  isLoading: false,
  error: null,
  currentSrc: null,
  duration: 0,
  currentTime: 0
};
function defaultCreateElement() {
  if (typeof Audio === "undefined") {
    throw new Error(
      "createAudioPlayer: no Audio constructor available. Run in a browser, or inject `createElement` for non-DOM environments/tests."
    );
  }
  return new Audio();
}
function isBlob(source) {
  return typeof Blob !== "undefined" && source instanceof Blob;
}
function createAudioPlayer(options = {}) {
  const {
    createElement = defaultCreateElement,
    createObjectURL = (blob) => URL.createObjectURL(blob),
    revokeObjectURL = (url) => URL.revokeObjectURL(url),
    onError,
    onEnded
  } = options;
  let state = { ...INITIAL };
  let el = null;
  let ownedUrl = null;
  let disposed = false;
  const listeners = /* @__PURE__ */ new Set();
  function emit() {
    for (const l of listeners) l();
  }
  function setState(patch) {
    state = { ...state, ...patch };
    emit();
  }
  const onLoadedMetadata = () => {
    setState({
      isLoading: false,
      duration: Number.isFinite(el?.duration) ? el.duration : 0
    });
  };
  const onTimeUpdate = () => {
    if (el) setState({ currentTime: el.currentTime });
  };
  const onPlaying = () => {
    setState({ status: "playing", isPlaying: true, isLoading: false, error: null });
  };
  const onPause = () => {
    if (state.status !== "idle" && state.status !== "error") {
      setState({ status: "paused", isPlaying: false });
    }
  };
  const onEndedEvt = () => {
    setState({ status: "idle", isPlaying: false, currentTime: 0 });
    onEnded?.();
  };
  const onErrorEvt = () => {
    const err = new Error("audio element error");
    setState({ status: "error", isPlaying: false, isLoading: false, error: err });
    onError?.(err, "audioPlayer:element");
  };
  function ensureElement() {
    if (el) return el;
    el = createElement();
    el.addEventListener("loadedmetadata", onLoadedMetadata);
    el.addEventListener("timeupdate", onTimeUpdate);
    el.addEventListener("playing", onPlaying);
    el.addEventListener("play", onPlaying);
    el.addEventListener("pause", onPause);
    el.addEventListener("ended", onEndedEvt);
    el.addEventListener("error", onErrorEvt);
    return el;
  }
  function releaseOwnedUrl() {
    if (ownedUrl) {
      revokeObjectURL(ownedUrl);
      ownedUrl = null;
    }
  }
  function load(source) {
    if (disposed) return;
    const element = ensureElement();
    releaseOwnedUrl();
    let url;
    if (isBlob(source)) {
      url = createObjectURL(source);
      ownedUrl = url;
    } else {
      url = source.url;
    }
    element.src = url;
    element.load();
    setState({
      status: "loading",
      isLoading: true,
      isPlaying: false,
      error: null,
      currentSrc: url,
      currentTime: 0,
      duration: 0
    });
  }
  async function play() {
    if (disposed || !el) return;
    try {
      await el.play();
      setState({ status: "playing", isPlaying: true, error: null });
    } catch (error) {
      setState({
        status: "error",
        isPlaying: false,
        error: error instanceof Error ? error : new Error(String(error))
      });
      onError?.(error, "audioPlayer:play");
    }
  }
  function pause() {
    if (disposed || !el) return;
    el.pause();
    setState({ status: "paused", isPlaying: false });
  }
  function stop() {
    if (disposed || !el) return;
    el.pause();
    el.currentTime = 0;
    el.src = "";
    releaseOwnedUrl();
    setState({
      status: "idle",
      isPlaying: false,
      isLoading: false,
      currentSrc: null,
      currentTime: 0
    });
  }
  async function toggle() {
    if (state.isPlaying) {
      pause();
      return;
    }
    await play();
  }
  function seek(seconds) {
    if (disposed || !el) return;
    const target = clampSeekTarget(seconds, state.duration);
    el.currentTime = target;
    setState({ currentTime: target });
  }
  function seekBy(deltaSeconds) {
    if (disposed || !el) return;
    const base = Number.isFinite(el.currentTime) ? el.currentTime : state.currentTime;
    seek(base + deltaSeconds);
  }
  function dispose() {
    if (disposed) return;
    disposed = true;
    if (el) {
      el.pause();
      el.removeEventListener("loadedmetadata", onLoadedMetadata);
      el.removeEventListener("timeupdate", onTimeUpdate);
      el.removeEventListener("playing", onPlaying);
      el.removeEventListener("play", onPlaying);
      el.removeEventListener("pause", onPause);
      el.removeEventListener("ended", onEndedEvt);
      el.removeEventListener("error", onErrorEvt);
    }
    releaseOwnedUrl();
    listeners.clear();
  }
  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    load,
    play,
    pause,
    stop,
    toggle,
    seek,
    seekBy,
    dispose
  };
}

// src/voice/useAudioPlayer.ts
import { useEffect as useEffect3, useMemo, useRef as useRef3, useSyncExternalStore } from "react";
function useAudioPlayer(opts = {}) {
  const cbRef = useRef3(opts);
  cbRef.current = opts;
  const controller = useMemo(
    () => createAudioPlayer({
      onError: (e, ctx) => cbRef.current.onError?.(e, ctx),
      onEnded: () => cbRef.current.onEnded?.(),
      ...opts.deps
    }),
    // One controller for the component's lifetime; deps are read once by design.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );
  useEffect3(() => () => controller.dispose(), [controller]);
  const state = useSyncExternalStore(
    controller.subscribe,
    controller.getState,
    controller.getState
  );
  return {
    ...state,
    load: controller.load,
    play: controller.play,
    pause: controller.pause,
    stop: controller.stop,
    toggle: controller.toggle,
    seek: controller.seek,
    seekBy: controller.seekBy,
    playSource: async (source) => {
      controller.load(source);
      await controller.play();
    }
  };
}

// src/voice/AudioPlayer.tsx
import { Play as Play2, Pause, Square as Square2, Loader2 as Loader25, AlertCircle } from "lucide-react";
import { useEffect as useEffect4 } from "react";
import { jsx as jsx14, jsxs as jsxs10 } from "react/jsx-runtime";
var ICON = "w-4 h-4";
var BTN = "p-2 disabled:opacity-40";
function AudioPlayer({
  source,
  autoPlay = false,
  onError,
  onEnded,
  className,
  buttonClassName,
  iconClassName
}) {
  const player = useAudioPlayer({ onError, onEnded });
  const { load, play, toggle, stop, isPlaying, isLoading, error, currentSrc } = player;
  useEffect4(() => {
    if (!source) return;
    load(source);
    if (autoPlay) void play();
  }, [source, autoPlay]);
  const hasSource = currentSrc !== null;
  const btnClass = buttonClassName ?? BTN;
  const iconClass = iconClassName ?? ICON;
  return /* @__PURE__ */ jsxs10("div", { className, "data-fi-audio-player": "", children: [
    /* @__PURE__ */ jsx14(
      "button",
      {
        type: "button",
        onClick: () => void toggle(),
        disabled: !hasSource || isLoading,
        "aria-pressed": isPlaying,
        "aria-label": isPlaying ? "Pausar audio" : "Reproducir audio",
        className: btnClass,
        children: isLoading ? /* @__PURE__ */ jsx14(Loader25, { className: `${iconClass} animate-spin`, "aria-hidden": true }) : isPlaying ? /* @__PURE__ */ jsx14(Pause, { className: iconClass, "aria-hidden": true }) : /* @__PURE__ */ jsx14(Play2, { className: iconClass, "aria-hidden": true })
      }
    ),
    /* @__PURE__ */ jsx14(
      "button",
      {
        type: "button",
        onClick: stop,
        disabled: !hasSource,
        "aria-label": "Detener audio",
        className: btnClass,
        children: /* @__PURE__ */ jsx14(Square2, { className: iconClass, "aria-hidden": true })
      }
    ),
    error ? /* @__PURE__ */ jsxs10("span", { role: "alert", className: "inline-flex items-center gap-1 text-xs", children: [
      /* @__PURE__ */ jsx14(AlertCircle, { className: iconClass, "aria-hidden": true }),
      "Error de audio"
    ] }) : null
  ] });
}

// src/voice/RichAudioPlayer.tsx
import {
  Play as Play3,
  Pause as Pause2,
  Square as Square3,
  Loader2 as Loader26,
  AlertCircle as AlertCircle2,
  RotateCcw,
  RotateCw
} from "lucide-react";
import { useEffect as useEffect5 } from "react";
import { jsx as jsx15, jsxs as jsxs11 } from "react/jsx-runtime";
var ICON2 = "w-4 h-4";
var BTN2 = "p-2 disabled:opacity-40";
function formatPlaybackTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor(total % 3600 / 60);
  const s = total % 60;
  const ss = String(s).padStart(2, "0");
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${ss}`;
  return `${m}:${ss}`;
}
function RichAudioPlayer({
  source,
  autoPlay = false,
  skipSeconds = 10,
  showTime = true,
  onError,
  onEnded,
  className,
  buttonClassName,
  iconClassName,
  progressClassName
}) {
  const player = useAudioPlayer({ onError, onEnded });
  const {
    load,
    play,
    toggle,
    stop,
    seek,
    seekBy,
    isPlaying,
    isLoading,
    error,
    currentSrc,
    duration,
    currentTime
  } = player;
  useEffect5(() => {
    if (!source) return;
    load(source);
    if (autoPlay) void play();
  }, [source, autoPlay]);
  const hasSource = currentSrc !== null;
  const canSeek = hasSource && duration > 0;
  const btnClass = buttonClassName ?? BTN2;
  const iconClass = iconClassName ?? ICON2;
  const positionLabel = `${formatPlaybackTime(currentTime)} / ${formatPlaybackTime(
    duration
  )}`;
  return /* @__PURE__ */ jsxs11(
    "div",
    {
      className,
      "data-fi-audio-player": "rich",
      role: "group",
      "aria-label": "Controles de reproducci\xF3n de audio",
      children: [
        /* @__PURE__ */ jsx15(
          "button",
          {
            type: "button",
            onClick: () => seekBy(-skipSeconds),
            disabled: !canSeek,
            "aria-label": `Retroceder ${skipSeconds} segundos`,
            className: btnClass,
            children: /* @__PURE__ */ jsx15(RotateCcw, { className: iconClass, "aria-hidden": true })
          }
        ),
        /* @__PURE__ */ jsx15(
          "button",
          {
            type: "button",
            onClick: () => void toggle(),
            disabled: !hasSource || isLoading,
            "aria-pressed": isPlaying,
            "aria-label": isPlaying ? "Pausar audio" : "Reproducir audio",
            className: btnClass,
            children: isLoading ? /* @__PURE__ */ jsx15(Loader26, { className: `${iconClass} animate-spin`, "aria-hidden": true }) : isPlaying ? /* @__PURE__ */ jsx15(Pause2, { className: iconClass, "aria-hidden": true }) : /* @__PURE__ */ jsx15(Play3, { className: iconClass, "aria-hidden": true })
          }
        ),
        /* @__PURE__ */ jsx15(
          "button",
          {
            type: "button",
            onClick: stop,
            disabled: !hasSource,
            "aria-label": "Detener audio",
            className: btnClass,
            children: /* @__PURE__ */ jsx15(Square3, { className: iconClass, "aria-hidden": true })
          }
        ),
        /* @__PURE__ */ jsx15(
          "button",
          {
            type: "button",
            onClick: () => seekBy(skipSeconds),
            disabled: !canSeek,
            "aria-label": `Avanzar ${skipSeconds} segundos`,
            className: btnClass,
            children: /* @__PURE__ */ jsx15(RotateCw, { className: iconClass, "aria-hidden": true })
          }
        ),
        /* @__PURE__ */ jsx15(
          "input",
          {
            type: "range",
            min: 0,
            max: duration > 0 ? duration : 0,
            step: 0.1,
            value: Math.min(currentTime, duration > 0 ? duration : currentTime),
            onChange: (e) => seek(Number(e.target.value)),
            disabled: !canSeek,
            "aria-label": "Progreso de reproducci\xF3n",
            "aria-valuetext": positionLabel,
            className: progressClassName,
            "data-fi-audio-progress": ""
          }
        ),
        showTime ? /* @__PURE__ */ jsx15("span", { "data-fi-audio-time": "", "aria-hidden": true, className: "text-xs tabular-nums", children: positionLabel }) : null,
        error ? /* @__PURE__ */ jsxs11("span", { role: "alert", className: "inline-flex items-center gap-1 text-xs", children: [
          /* @__PURE__ */ jsx15(AlertCircle2, { className: iconClass, "aria-hidden": true }),
          "Error de audio"
        ] }) : null
      ]
    }
  );
}

// src/voice/AudioVisualizer.tsx
import { jsx as jsx16 } from "react/jsx-runtime";
var MIN_BAR_PCT = 4;
function normalizeLevels(levels) {
  return levels.map(
    (v) => !Number.isFinite(v) ? 0 : v < 0 ? 0 : v > 1 ? 1 : v
  );
}
function resampleLevels(levels, count) {
  if (count <= 0) return [];
  if (levels.length === 0) return new Array(count).fill(0);
  if (levels.length === count) return levels.slice();
  const out = [];
  for (let i = 0; i < count; i++) {
    const idx = Math.min(
      levels.length - 1,
      Math.floor(i / count * levels.length)
    );
    out.push(levels[idx]);
  }
  return out;
}
function AudioVisualizer({
  levels,
  variant = "bars",
  active = true,
  barCount,
  label = "Visualizador de nivel de audio",
  className,
  barClassName,
  color
}) {
  const normalized = normalizeLevels(levels);
  if (variant === "pulse") {
    const peak = active && normalized.length ? Math.max(...normalized) : 0;
    const scale = 1 + peak;
    return /* @__PURE__ */ jsx16(
      "div",
      {
        role: "img",
        "aria-label": label,
        className,
        "data-fi-audio-visualizer": "pulse",
        "data-active": active ? "" : void 0,
        children: /* @__PURE__ */ jsx16(
          "span",
          {
            "data-fi-pulse-core": "",
            style: {
              display: "inline-block",
              transform: `scale(${scale})`,
              borderColor: color
            }
          }
        )
      }
    );
  }
  const count = barCount && barCount > 0 ? barCount : normalized.length;
  const bars = resampleLevels(normalized, count);
  return /* @__PURE__ */ jsx16(
    "div",
    {
      role: "img",
      "aria-label": label,
      className,
      "data-fi-audio-visualizer": "bars",
      "data-active": active ? "" : void 0,
      style: { display: "inline-flex", alignItems: "flex-end" },
      children: bars.map((level, i) => {
        const pct = active ? Math.max(MIN_BAR_PCT, level * 100) : MIN_BAR_PCT;
        return /* @__PURE__ */ jsx16(
          "span",
          {
            "data-fi-audio-bar": "",
            className: barClassName,
            style: { height: `${pct}%`, backgroundColor: color }
          },
          i
        );
      })
    }
  );
}

// src/voice/ComposerMicSlot.tsx
import { Mic as Mic2, MicOff, Square as Square4, Loader2 as Loader27 } from "lucide-react";
import { jsx as jsx17 } from "react/jsx-runtime";
var ICON3 = "w-4 h-4";
var BTN3 = "p-2 disabled:opacity-40";
function ComposerMicSlot({
  available = false,
  recording = false,
  busy = false,
  onStart,
  onStop,
  unavailableLabel = "Dictado por voz no disponible todav\xEDa",
  startLabel = "Iniciar dictado por voz",
  stopLabel = "Detener dictado por voz",
  busyLabel = "Transcribiendo\u2026",
  className,
  buttonClassName,
  iconClassName
}) {
  const btnClass = buttonClassName ?? BTN3;
  const iconClass = iconClassName ?? ICON3;
  const disabled = !available || busy;
  const label = !available ? unavailableLabel : busy ? busyLabel : recording ? stopLabel : startLabel;
  const handleClick = () => {
    if (disabled) return;
    if (recording) onStop?.();
    else onStart?.();
  };
  const Icon = !available ? MicOff : busy ? Loader27 : recording ? Square4 : Mic2;
  return /* @__PURE__ */ jsx17("div", { className, "data-fi-mic-slot": "", "data-available": available ? "" : void 0, children: /* @__PURE__ */ jsx17(
    "button",
    {
      type: "button",
      onClick: handleClick,
      disabled,
      "aria-disabled": disabled,
      "aria-pressed": available ? recording : void 0,
      "aria-label": label,
      title: !available ? unavailableLabel : void 0,
      className: btnClass,
      children: /* @__PURE__ */ jsx17(
        Icon,
        {
          className: busy ? `${iconClass} animate-spin` : iconClass,
          "aria-hidden": true
        }
      )
    }
  ) });
}

// src/voice/useVoice.ts
import { useCallback as useCallback2, useRef as useRef4, useState as useState4 } from "react";
function toUrl(src) {
  return src instanceof Blob ? URL.createObjectURL(src) : src.url;
}
var TTS_CACHE_MAX_CLIPS = 8;
var clipKey = (text, voice) => `${voice}\0${text}`;
function useVoice(adapter, opts = {}) {
  const { onError } = opts;
  const [isOpen, setIsOpen] = useState4(false);
  const [isLoading, setIsLoading] = useState4(false);
  const [audioUrl, setAudioUrl] = useState4(null);
  const [voiceName, setVoiceName] = useState4("nova");
  const [isUserMessage, setIsUserMessage] = useState4(false);
  const [currentVoice, setCurrentVoice] = useState4("nova");
  const [currentText, setCurrentText] = useState4("");
  const inFlight = useRef4(false);
  const clipCache = useRef4(/* @__PURE__ */ new Map());
  const synthesizeCached = useCallback2(
    async (text, voice) => {
      const cache = clipCache.current;
      const key = clipKey(text, voice);
      const hit = cache.get(key);
      if (hit) {
        cache.delete(key);
        cache.set(key, hit);
        return hit;
      }
      const src = await adapter.synthesize(text, voice);
      if (src instanceof Blob && src.size > 0) {
        cache.set(key, src);
        while (cache.size > TTS_CACHE_MAX_CLIPS) {
          const oldest = cache.keys().next().value;
          if (oldest === void 0) break;
          cache.delete(oldest);
        }
      }
      return src;
    },
    [adapter]
  );
  const getVoiceDisplayName = useCallback2(
    (voiceId) => {
      const found = adapter?.availableVoices?.find((v) => v.id === voiceId);
      if (found) return found.label.split(" ")[0];
      const match = voiceId.match(/([A-Z][a-z]+)Neural$/);
      return match ? match[1] : voiceId;
    },
    [adapter]
  );
  const generateAudio = useCallback2(
    async (text, voice = "nova", isUser = false) => {
      if (!adapter?.synthesize) return;
      if (inFlight.current) return;
      inFlight.current = true;
      setCurrentText(text);
      setCurrentVoice(voice);
      setIsUserMessage(isUser);
      setVoiceName(getVoiceDisplayName(voice));
      setIsOpen(true);
      setAudioUrl((prev) => {
        if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
        return null;
      });
      const isHit = clipCache.current.has(clipKey(text, voice));
      if (!isHit) setIsLoading(true);
      try {
        const src = await synthesizeCached(text, voice);
        setAudioUrl(toUrl(src));
      } catch (error) {
        onError?.(error, "useVoice:TTS");
        setIsOpen(false);
      } finally {
        inFlight.current = false;
        setIsLoading(false);
      }
    },
    [adapter, getVoiceDisplayName, onError, synthesizeCached]
  );
  const changeVoice = useCallback2(
    async (newVoice) => {
      if (!currentText || !adapter?.synthesize) return;
      if (inFlight.current) return;
      inFlight.current = true;
      setCurrentVoice(newVoice);
      setVoiceName(getVoiceDisplayName(newVoice));
      setIsLoading(true);
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
      try {
        const src = await synthesizeCached(currentText, newVoice);
        setAudioUrl(toUrl(src));
      } catch (error) {
        onError?.(error, "useVoice:VoiceChange");
      } finally {
        inFlight.current = false;
        setIsLoading(false);
      }
    },
    [adapter, audioUrl, currentText, getVoiceDisplayName, onError, synthesizeCached]
  );
  const close = useCallback2(() => {
    setIsOpen(false);
    setAudioUrl(null);
    setIsLoading(false);
    setCurrentText("");
    setIsUserMessage(false);
  }, []);
  const hasCachedAudio = useCallback2(
    (text, voice = "nova") => clipCache.current.has(clipKey(text, voice)),
    []
  );
  return {
    isOpen,
    isLoading,
    audioUrl,
    voiceName,
    isUserMessage,
    currentVoice,
    currentText,
    generateAudio,
    changeVoice,
    close,
    hasCachedAudio
  };
}

// src/voice/useDictation.ts
import { useCallback as useCallback4, useState as useState7 } from "react";

// src/voice/useRecorder.ts
import { useState as useState5, useRef as useRef5, useCallback as useCallback3 } from "react";

// src/voice/makeRecorder.ts
async function makeRecorder(stream, onChunk, opts) {
  const timeSlice = opts?.timeSlice;
  const channels = opts?.channels ?? 1;
  const mod = await import("recordrtc");
  const RecordRTC = mod.default ?? mod;
  if (!RecordRTC) {
    throw new Error("[makeRecorder] RecordRTC library not available");
  }
  const mimeType = "audio/wav";
  let currentRecorder = null;
  let loopTimer = null;
  let isActive = false;
  const createRecorder = () => {
    return new RecordRTC(stream, {
      type: "audio",
      recorderType: RecordRTC.StereoAudioRecorder,
      mimeType,
      numberOfAudioChannels: channels,
      desiredSampRate: opts?.sampleRate ?? 16e3,
      disableLogs: true
    });
  };
  const startLoop = async () => {
    if (!isActive) return;
    currentRecorder = createRecorder();
    currentRecorder.startRecording();
    if (timeSlice && timeSlice > 0) {
      loopTimer = setTimeout(async () => {
        if (!currentRecorder || !isActive) return;
        currentRecorder.stopRecording(() => {
          if (!isActive) return;
          const blob = currentRecorder.getBlob();
          if (blob && blob.size > 0) {
            onChunk(blob);
          }
          if (isActive) {
            startLoop();
          }
        });
      }, timeSlice);
    }
  };
  return {
    start: () => {
      isActive = true;
      startLoop();
    },
    stop: () => new Promise((resolve) => {
      isActive = false;
      if (loopTimer) {
        clearTimeout(loopTimer);
        loopTimer = null;
      }
      if (currentRecorder) {
        currentRecorder.stopRecording(() => {
          const finalBlob = currentRecorder.getBlob();
          resolve(finalBlob);
        });
      } else {
        resolve(new Blob([], { type: mimeType }));
      }
    }),
    kind: "recordrtc"
  };
}

// src/voice/useRecorder.ts
var log = {
  error: (_m, _meta) => {
    void _m;
    void _meta;
  },
  warn: (_m, _meta) => {
    void _m;
    void _meta;
  }
};
function useRecorder(config) {
  const {
    onChunk,
    onError,
    timeSlice = 3e3,
    sampleRate = 16e3,
    channels = 1,
    externalStream = null,
    deviceId = null
  } = config;
  const [isRecording, setIsRecording] = useState5(false);
  const [recordingTime, setRecordingTime] = useState5(0);
  const [fullAudioBlob, setFullAudioBlob] = useState5(null);
  const [fullAudioUrl, setFullAudioUrl] = useState5(null);
  const [currentStream, setCurrentStream] = useState5(null);
  const recorderRef = useRef5(null);
  const continuousRecorderRef = useRef5(null);
  const currentStreamRef = useRef5(null);
  const recordingTimerRef = useRef5(null);
  const fullAudioUrlRef = useRef5(null);
  const chunkNumberRef = useRef5(0);
  const startRecording = useCallback3(async () => {
    try {
      chunkNumberRef.current = 0;
      setRecordingTime(0);
      setFullAudioBlob(null);
      if (fullAudioUrlRef.current) {
        URL.revokeObjectURL(fullAudioUrlRef.current);
        fullAudioUrlRef.current = null;
        setFullAudioUrl(null);
      }
      let stream;
      if (externalStream) {
        stream = externalStream;
      } else {
        try {
          const timeoutMs = 15e3;
          const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => {
              reject(new Error(
                "Microphone permission timeout (15s). Check: 1) macOS System Preferences \u2192 Privacy \u2192 Microphone has your browser enabled, 2) Restart browser after granting permission"
              ));
            }, timeoutMs);
          });
          const audioConstraints = deviceId ? { deviceId: { exact: deviceId } } : true;
          stream = await Promise.race([
            navigator.mediaDevices.getUserMedia({ audio: audioConstraints }),
            timeoutPromise
          ]);
        } catch (micError) {
          log.error("Microphone access failed", { error: String(micError) });
          throw micError;
        }
      }
      currentStreamRef.current = stream;
      setCurrentStream(stream);
      const chunkedRecorder = await makeRecorder(
        stream,
        async (blob) => {
          const chunkNumber = chunkNumberRef.current++;
          await onChunk(blob, chunkNumber);
        },
        {
          timeSlice,
          sampleRate,
          channels
        }
      );
      recorderRef.current = chunkedRecorder;
      chunkedRecorder.start();
      const continuousRecorder = await makeRecorder(
        stream,
        () => {
        },
        // Empty callback - blob comes from .stop() return value
        {
          // NO timeSlice = records continuously until stop()
          sampleRate,
          channels
        }
      );
      continuousRecorderRef.current = continuousRecorder;
      continuousRecorder.start();
      setIsRecording(true);
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1e3);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "No se pudo acceder al micr\xF3fono. Por favor, verifica los permisos.";
      log.error("Start failed", { error: String(err) });
      if (onError) {
        onError(errorMessage);
      }
    }
  }, [onChunk, onError, timeSlice, sampleRate, channels, externalStream, deviceId]);
  const stopRecording = useCallback3(async () => {
    try {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      setIsRecording(false);
      if (currentStreamRef.current) {
        currentStreamRef.current.getTracks().forEach((track) => {
          track.stop();
        });
        currentStreamRef.current = null;
        setCurrentStream(null);
      }
      let fullBlob = null;
      if (continuousRecorderRef.current) {
        try {
          fullBlob = await continuousRecorderRef.current.stop();
          if (fullBlob && fullBlob.size > 0) {
            if (fullAudioUrlRef.current) {
              URL.revokeObjectURL(fullAudioUrlRef.current);
            }
            const audioUrl = URL.createObjectURL(fullBlob);
            fullAudioUrlRef.current = audioUrl;
            setFullAudioUrl(audioUrl);
            setFullAudioBlob(fullBlob);
          }
        } catch (err) {
          log.warn("Continuous recorder stop error (non-critical)", { error: String(err) });
        }
        continuousRecorderRef.current = null;
      }
      if (recorderRef.current) {
        try {
          const lastChunk = await recorderRef.current.stop();
          if (lastChunk && lastChunk.size > 0) {
            const finalChunkNumber = chunkNumberRef.current++;
            try {
              const result = onChunk(lastChunk, finalChunkNumber);
              if (result instanceof Promise) {
                result.catch((err) => {
                  log.error("Final chunk processing failed", { error: String(err) });
                });
              }
            } catch (err) {
              log.error("Final chunk processing failed", { error: String(err) });
            }
          }
        } catch (err) {
          log.warn("Chunked recorder stop error (non-critical)", { error: String(err) });
        }
        recorderRef.current = null;
      }
      return fullBlob;
    } catch (err) {
      log.error("Stop failed", { error: String(err) });
      if (currentStreamRef.current) {
        currentStreamRef.current.getTracks().forEach((track) => track.stop());
        currentStreamRef.current = null;
        setCurrentStream(null);
      }
      setIsRecording(false);
      if (onError) {
        onError(err instanceof Error ? err.message : "Error al detener grabaci\xF3n");
      }
      return null;
    }
  }, [onChunk, onError]);
  return {
    isRecording,
    recordingTime,
    currentStream,
    fullAudioBlob,
    fullAudioUrl,
    startRecording,
    stopRecording
  };
}

// src/voice/useAudioAnalysis.ts
import { useState as useState6, useRef as useRef6, useEffect as useEffect6 } from "react";
var AUDIO_CONFIG = { SILENCE_THRESHOLD: 2, AUDIO_GAIN: 2.5 };
function frequencyDataToBands(data, bandCount, gain) {
  if (bandCount <= 0 || data.length === 0) return new Array(Math.max(0, bandCount)).fill(0);
  const usable = Math.floor(data.length * 0.75) || data.length;
  const sliceSize = Math.max(1, Math.floor(usable / bandCount));
  const bands = new Array(bandCount);
  for (let b = 0; b < bandCount; b++) {
    const start = b * sliceSize;
    let sum = 0;
    let n = 0;
    for (let i = start; i < start + sliceSize && i < usable; i++) {
      sum += data[i];
      n++;
    }
    const avg = n ? sum / n : 0;
    const scaled = avg / 255 * gain;
    bands[b] = scaled > 1 ? 1 : scaled < 0 ? 0 : scaled;
  }
  return bands;
}
function useAudioAnalysis(stream, config) {
  const {
    silenceThreshold = AUDIO_CONFIG.SILENCE_THRESHOLD,
    gain = AUDIO_CONFIG.AUDIO_GAIN,
    isActive,
    bandCount = 24
  } = config;
  const [audioLevel, setAudioLevel] = useState6(0);
  const [bands, setBands] = useState6([]);
  const analyserRef = useRef6(null);
  const audioContextRef = useRef6(null);
  const animationFrameRef = useRef6(null);
  const isSilent = audioLevel < silenceThreshold;
  useEffect6(() => {
    if (!stream || !isActive) {
      setAudioLevel(0);
      setBands([]);
      return;
    }
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const gainNode = audioContext.createGain();
    const source = audioContext.createMediaStreamSource(stream);
    gainNode.gain.value = gain;
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;
    source.connect(gainNode);
    gainNode.connect(analyser);
    audioContextRef.current = audioContext;
    analyserRef.current = analyser;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    const updateLevel = () => {
      if (!analyserRef.current) return;
      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      setAudioLevel(average);
      setBands(frequencyDataToBands(dataArray, bandCount, gain));
      animationFrameRef.current = requestAnimationFrame(updateLevel);
    };
    updateLevel();
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [stream, isActive, gain, silenceThreshold, bandCount]);
  return { audioLevel, isSilent, bands };
}

// src/voice/useDictation.ts
function useDictation(adapter, opts = {}) {
  const { timeSliceMs = 3e4, deviceId = null, onTranscriptUpdate, onError } = opts;
  const [liveTranscript, setLiveTranscript] = useState7("");
  const [isTranscribing, setIsTranscribing] = useState7(false);
  const handleChunk = useCallback4(
    async (blob, chunkNumber) => {
      if (!adapter?.transcribe) return;
      setIsTranscribing(true);
      try {
        const { text } = await adapter.transcribe(blob, { index: chunkNumber });
        if (text) {
          setLiveTranscript((prev) => {
            const updated = prev ? `${prev} ${text}` : text;
            onTranscriptUpdate?.(updated);
            return updated;
          });
        }
      } catch (err) {
        onError?.(err instanceof Error ? err.message : "transcription failed");
      } finally {
        setIsTranscribing(false);
      }
    },
    [adapter, onTranscriptUpdate, onError]
  );
  const { isRecording, recordingTime, currentStream, startRecording, stopRecording } = useRecorder({
    onChunk: handleChunk,
    onError,
    timeSlice: timeSliceMs,
    deviceId
  });
  const { audioLevel, isSilent, bands } = useAudioAnalysis(currentStream, {
    isActive: isRecording
  });
  const start = useCallback4(async () => {
    setLiveTranscript("");
    await startRecording();
  }, [startRecording]);
  const stop = useCallback4(async () => {
    await stopRecording();
  }, [stopRecording]);
  return {
    isRecording,
    recordingTime,
    audioLevel,
    isSilent,
    bands,
    liveTranscript,
    isTranscribing,
    startRecording: start,
    stopRecording: stop
  };
}

// src/voice/audioArtifact.ts
var AUDIO_QUEUE_DEFAULTS = {
  maxItems: 10,
  maxBytes: 50 * 1024 * 1024,
  // 50 MB total queue
  maxBytesPerItem: 10 * 1024 * 1024
  // 10 MB per artifact
};
function makeArtifactId() {
  return `audio-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
function isPending(a) {
  return a.state !== "transcribed" && a.state !== "deleted";
}
function isTerminal(a) {
  return a.state === "transcribed" || a.state === "deleted";
}
function artifactLabel(state) {
  const map = {
    recording: "Grabando",
    paused: "En pausa",
    stopping: "Guardando...",
    saved: "Guardado",
    queued: "En cola",
    uploading: "Subiendo",
    transcribing: "Transcribiendo",
    transcribed: "Transcrito",
    failed: "Fall\xF3",
    deleted: "Eliminado"
  };
  return map[state];
}
function formatArtifactSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
function formatArtifactDuration(ms) {
  if (!ms) return "--:--";
  const s = Math.floor(ms / 1e3);
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

// src/voice/AudioQueueStore.ts
var DEFAULT_DB_NAME = "free-intelligence-audio-queue";
var DEFAULT_STORE_NAME = "audio-artifacts";
var DB_VERSION = 1;
var CREATED_AT_INDEX = "by_createdAt";
function unavailable() {
  return typeof indexedDB === "undefined";
}
function unavailableError() {
  return new Error(
    "AudioQueueStore: IndexedDB is not available (SSR or storage disabled)."
  );
}
var AudioQueueStore = class {
  constructor(opts = {}) {
    this.dbPromise = null;
    this.dbName = opts.dbName ?? DEFAULT_DB_NAME;
    this.storeName = opts.storeName ?? DEFAULT_STORE_NAME;
  }
  open() {
    if (unavailable()) return Promise.reject(unavailableError());
    if (!this.dbPromise) {
      this.dbPromise = new Promise((resolve, reject) => {
        const req = indexedDB.open(this.dbName, DB_VERSION);
        req.onupgradeneeded = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains(this.storeName)) {
            const store = db.createObjectStore(this.storeName, { keyPath: "id" });
            store.createIndex(CREATED_AT_INDEX, "createdAt", { unique: false });
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error ?? new Error("AudioQueueStore: open failed"));
      });
    }
    return this.dbPromise;
  }
  async run(mode, makeRequest) {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(this.storeName, mode);
      const req = makeRequest(tx.objectStore(this.storeName));
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error ?? new Error("AudioQueueStore: request failed"));
    });
  }
  async list() {
    return this.run("readonly", (s) => s.getAll());
  }
  async get(id) {
    const r = await this.run(
      "readonly",
      (s) => s.get(id)
    );
    return r ?? null;
  }
  async put(artifact) {
    await this.run("readwrite", (s) => s.put(artifact));
  }
  async updateMeta(id, patch) {
    const existing = await this.get(id);
    if (!existing) return;
    await this.put({
      ...existing,
      ...patch,
      id,
      updatedAt: (/* @__PURE__ */ new Date()).toISOString()
    });
  }
  async delete(id) {
    await this.run("readwrite", (s) => s.delete(id));
  }
  async clear() {
    await this.run("readwrite", (s) => s.clear());
  }
};

// src/voice/useDurableRecording.ts
import { useState as useState8, useRef as useRef7, useCallback as useCallback5, useEffect as useEffect7 } from "react";
var MIC_TIMEOUT_MS = 15e3;
async function loadRecordRTC() {
  const mod = await import("recordrtc");
  const RTC = mod.default ?? mod.RecordRTC ?? mod;
  if (!RTC || typeof RTC !== "function") {
    throw new Error("[useDurableRecording] RecordRTC not available");
  }
  return RTC;
}
function useDurableRecording(opts) {
  const {
    store,
    policy = AUDIO_QUEUE_DEFAULTS,
    deviceId = null,
    onSaved,
    onError
  } = opts;
  const [artifact, setArtifact] = useState8(null);
  const [recordingTime, setRecordingTime] = useState8(0);
  const [currentStream, setCurrentStream] = useState8(null);
  const [isAtCapacity, setIsAtCapacity] = useState8(false);
  const [isStarting, setIsStarting] = useState8(false);
  const recorderRef = useRef7(null);
  const streamRef = useRef7(null);
  const timerRef = useRef7(null);
  const startTimeRef = useRef7(0);
  const pausedElapsedRef = useRef7(0);
  const artifactRef = useRef7(null);
  useEffect7(() => {
    artifactRef.current = artifact;
  }, [artifact]);
  useEffect7(() => {
    store.list().then((stored) => {
      const pending = stored.filter(
        (a) => a.state !== "transcribed" && a.state !== "deleted"
      );
      const totalBytes = pending.reduce((s, a) => s + a.size, 0);
      setIsAtCapacity(
        pending.length >= policy.maxItems || totalBytes >= policy.maxBytes
      );
    }).catch(() => {
    });
  }, [store, policy]);
  const { audioLevel, isSilent, bands } = useAudioAnalysis(currentStream, {
    isActive: artifact?.state === "recording"
  });
  const stopTimer = useCallback5(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);
  const releaseStream = useCallback5(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setCurrentStream(null);
    }
  }, []);
  const updateArtifact = useCallback5(
    (patch) => {
      setArtifact((prev) => {
        if (!prev) return prev;
        const updated = { ...prev, ...patch, updatedAt: (/* @__PURE__ */ new Date()).toISOString() };
        artifactRef.current = updated;
        return updated;
      });
    },
    []
  );
  const startRecording = useCallback5(async () => {
    if (artifact?.state === "recording" || artifact?.state === "paused") return;
    setIsStarting(true);
    try {
      const stored = await store.list();
      const pending = stored.filter(
        (a) => a.state !== "transcribed" && a.state !== "deleted"
      );
      const totalBytes = pending.reduce((s, a) => s + a.size, 0);
      if (pending.length >= policy.maxItems || totalBytes >= policy.maxBytes) {
        setIsAtCapacity(true);
        onError?.(
          `Cola llena (m\xE1ximo ${policy.maxItems} audios o ${Math.round(policy.maxBytes / 1024 / 1024)} MB). Transcribe o elimina audios antes de grabar.`
        );
        return;
      }
      const timeoutPromise = new Promise(
        (_, reject) => setTimeout(
          () => reject(new Error("Permiso de micr\xF3fono expirado (15s).")),
          MIC_TIMEOUT_MS
        )
      );
      const audioConstraints = deviceId ? { deviceId: { exact: deviceId } } : true;
      const stream = await Promise.race([
        navigator.mediaDevices.getUserMedia({ audio: audioConstraints }),
        timeoutPromise
      ]);
      streamRef.current = stream;
      setCurrentStream(stream);
      const RecordRTC = await loadRecordRTC();
      const recorder = new RecordRTC(stream, {
        type: "audio",
        recorderType: RecordRTC.StereoAudioRecorder,
        mimeType: "audio/wav",
        numberOfAudioChannels: 1,
        desiredSampRate: 16e3,
        disableLogs: true
      });
      recorderRef.current = recorder;
      recorder.startRecording();
      const now = Date.now();
      startTimeRef.current = now;
      pausedElapsedRef.current = 0;
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime(
          Math.floor((Date.now() - startTimeRef.current) / 1e3)
        );
      }, 1e3);
      const newArtifact = {
        id: makeArtifactId(),
        mime: "audio/wav",
        size: 0,
        createdAt: (/* @__PURE__ */ new Date()).toISOString(),
        updatedAt: (/* @__PURE__ */ new Date()).toISOString(),
        state: "recording"
      };
      setArtifact(newArtifact);
      artifactRef.current = newArtifact;
    } catch (err) {
      releaseStream();
      onError?.(err instanceof Error ? err.message : "No se pudo iniciar la grabaci\xF3n.");
    } finally {
      setIsStarting(false);
    }
  }, [artifact, store, policy, deviceId, onError, releaseStream]);
  const pauseRecording = useCallback5(() => {
    if (artifactRef.current?.state !== "recording") return;
    recorderRef.current?.pauseRecording();
    stopTimer();
    pausedElapsedRef.current = Date.now() - startTimeRef.current;
    updateArtifact({ state: "paused" });
  }, [stopTimer, updateArtifact]);
  const resumeRecording = useCallback5(() => {
    if (artifactRef.current?.state !== "paused") return;
    recorderRef.current?.resumeRecording();
    startTimeRef.current = Date.now() - pausedElapsedRef.current;
    timerRef.current = setInterval(() => {
      setRecordingTime(
        Math.floor((Date.now() - startTimeRef.current) / 1e3)
      );
    }, 1e3);
    updateArtifact({ state: "recording" });
  }, [updateArtifact]);
  const stopRecording = useCallback5(async () => {
    const current = artifactRef.current;
    if (current?.state !== "recording" && current?.state !== "paused") {
      return null;
    }
    stopTimer();
    const durationMs = Date.now() - startTimeRef.current + pausedElapsedRef.current;
    updateArtifact({ state: "stopping" });
    return new Promise((resolve) => {
      if (!recorderRef.current) {
        releaseStream();
        resolve(null);
        return;
      }
      recorderRef.current.stopRecording(async () => {
        releaseStream();
        const blob = recorderRef.current?.getBlob() ?? null;
        recorderRef.current = null;
        if (!blob || blob.size === 0) {
          updateArtifact({ state: "failed", errorMessage: "Grabaci\xF3n vac\xEDa." });
          resolve(null);
          return;
        }
        if (blob.size > policy.maxBytesPerItem) {
          updateArtifact({
            state: "failed",
            errorMessage: `Audio demasiado grande (${Math.round(blob.size / 1024 / 1024)} MB, m\xE1ximo ${Math.round(policy.maxBytesPerItem / 1024 / 1024)} MB).`
          });
          resolve(null);
          return;
        }
        const finalArtifact = {
          ...current,
          size: blob.size,
          durationMs,
          state: "queued",
          updatedAt: (/* @__PURE__ */ new Date()).toISOString()
        };
        updateArtifact({
          size: blob.size,
          durationMs,
          state: "queued"
        });
        try {
          await store.put({ ...finalArtifact, blob });
          onSaved?.(finalArtifact);
          setIsAtCapacity(false);
          resolve(finalArtifact);
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Error al guardar audio.";
          updateArtifact({ state: "failed", errorMessage: msg });
          onError?.(msg);
          resolve(null);
        }
      });
    });
  }, [store, policy, releaseStream, stopTimer, updateArtifact, onSaved, onError]);
  const cancelRecording = useCallback5(() => {
    stopTimer();
    releaseStream();
    if (recorderRef.current) {
      try {
        recorderRef.current.stopRecording(() => {
        });
      } catch {
      }
      recorderRef.current = null;
    }
    setArtifact(null);
    artifactRef.current = null;
    setRecordingTime(0);
  }, [stopTimer, releaseStream]);
  return {
    artifact,
    recordingTime,
    bands,
    audioLevel,
    isSilent,
    isStarting,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    cancelRecording,
    isAtCapacity
  };
}

// src/voice/useAudioQueue.ts
import { useState as useState9, useEffect as useEffect8, useCallback as useCallback6 } from "react";
function useAudioQueue(opts) {
  const { store, adapter, onTranscribed, onError } = opts;
  const [artifacts, setArtifacts] = useState9([]);
  const [isLoading, setIsLoading] = useState9(true);
  const loadFromStore = useCallback6(async () => {
    try {
      const stored = await store.list();
      const metas = stored.filter((a) => a.state !== "deleted").map(({ blob: _blob, ...meta }) => meta).sort((a, b) => a.createdAt.localeCompare(b.createdAt));
      setArtifacts(metas);
    } catch {
    }
    setIsLoading(false);
  }, [store]);
  useEffect8(() => {
    loadFromStore();
  }, [loadFromStore]);
  const patchLocal = useCallback6(
    (id, patch) => {
      setArtifacts(
        (prev) => prev.map(
          (a) => a.id === id ? { ...a, ...patch, updatedAt: (/* @__PURE__ */ new Date()).toISOString() } : a
        )
      );
    },
    []
  );
  const doTranscribe = useCallback6(
    async (id) => {
      if (!adapter?.transcribe) {
        onError?.(id, "Adaptador de voz sin capacidad de transcripci\xF3n.");
        return;
      }
      patchLocal(id, { state: "transcribing", errorMessage: void 0 });
      await store.updateMeta(id, { state: "transcribing", errorMessage: void 0 });
      const stored = await store.get(id);
      if (!stored) {
        patchLocal(id, { state: "failed", errorMessage: "Artefacto no encontrado." });
        onError?.(id, "Artefacto no encontrado.");
        return;
      }
      patchLocal(id, { state: "uploading" });
      await store.updateMeta(id, { state: "uploading" });
      try {
        const { text } = await adapter.transcribe(stored.blob);
        patchLocal(id, { state: "transcribed", transcript: text });
        await store.updateMeta(id, { state: "transcribed", transcript: text });
        onTranscribed?.(id, text);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Transcripci\xF3n fallida.";
        patchLocal(id, { state: "failed", errorMessage: msg });
        await store.updateMeta(id, { state: "failed", errorMessage: msg });
        onError?.(id, msg);
      }
    },
    [adapter, store, patchLocal, onTranscribed, onError]
  );
  const transcribeArtifact = useCallback6(
    async (id) => {
      const a = artifacts.find((x) => x.id === id);
      if (!a || a.state !== "queued" && a.state !== "saved") return;
      await doTranscribe(id);
    },
    [artifacts, doTranscribe]
  );
  const retryTranscription = useCallback6(
    async (id) => {
      const a = artifacts.find((x) => x.id === id);
      if (!a || a.state !== "failed") return;
      await doTranscribe(id);
    },
    [artifacts, doTranscribe]
  );
  const getPlaybackUrl = useCallback6(
    async (id) => {
      const stored = await store.get(id);
      if (!stored?.blob || stored.blob.size === 0) return null;
      return URL.createObjectURL(stored.blob);
    },
    [store]
  );
  const deleteArtifact = useCallback6(
    async (id) => {
      await store.delete(id);
      setArtifacts((prev) => prev.filter((a) => a.id !== id));
    },
    [store]
  );
  const clearTranscribed = useCallback6(async () => {
    const toDelete = artifacts.filter((a) => a.state === "transcribed");
    await Promise.all(toDelete.map((a) => store.delete(a.id)));
    setArtifacts((prev) => prev.filter((a) => a.state !== "transcribed"));
  }, [artifacts, store]);
  const reload = useCallback6(async () => {
    setIsLoading(true);
    await loadFromStore();
  }, [loadFromStore]);
  const totalBytes = artifacts.filter(isPending).reduce((s, a) => s + a.size, 0);
  return {
    artifacts,
    totalBytes,
    isLoading,
    transcribeArtifact,
    retryTranscription,
    getPlaybackUrl,
    deleteArtifact,
    clearTranscribed,
    reload
  };
}

// src/voice/AudioQueuePanel.tsx
import { Loader2 as Loader29, Trash2 as Trash22, ShieldAlert } from "lucide-react";

// src/voice/AudioQueueItem.tsx
import { useState as useState10, useCallback as useCallback7 } from "react";
import {
  Mic as Mic3,
  PauseCircle,
  CheckCircle2,
  AlertCircle as AlertCircle3,
  Loader2 as Loader28,
  Play as Play4,
  RotateCcw as RotateCcw2,
  Trash2,
  FileAudio
} from "lucide-react";
import { jsx as jsx18, jsxs as jsxs12 } from "react/jsx-runtime";
function StateIcon({ state }) {
  const base = "w-4 h-4 shrink-0";
  switch (state) {
    case "recording":
      return /* @__PURE__ */ jsx18(Mic3, { className: `${base} text-red-400 animate-pulse` });
    case "paused":
      return /* @__PURE__ */ jsx18(PauseCircle, { className: `${base} text-yellow-400` });
    case "stopping":
      return /* @__PURE__ */ jsx18(Loader28, { className: `${base} text-amber-400 animate-spin` });
    case "transcribed":
      return /* @__PURE__ */ jsx18(CheckCircle2, { className: `${base} text-green-400` });
    case "failed":
      return /* @__PURE__ */ jsx18(AlertCircle3, { className: `${base} text-red-400` });
    case "transcribing":
    case "uploading":
      return /* @__PURE__ */ jsx18(Loader28, { className: `${base} text-blue-400 animate-spin` });
    default:
      return /* @__PURE__ */ jsx18(FileAudio, { className: `${base} text-gray-400` });
  }
}
function AudioQueueItem({
  artifact,
  onTranscribe,
  onRetry,
  onDelete,
  onGetPlaybackUrl,
  className = ""
}) {
  const [playing, setPlaying] = useState10(false);
  const [audioEl, setAudioEl] = useState10(null);
  const handlePlay = useCallback7(async () => {
    if (!onGetPlaybackUrl) return;
    if (playing && audioEl) {
      audioEl.pause();
      setPlaying(false);
      return;
    }
    const url = await onGetPlaybackUrl(artifact.id);
    if (!url) return;
    const el = new Audio(url);
    setAudioEl(el);
    setPlaying(true);
    el.play().catch(() => setPlaying(false));
    el.addEventListener("ended", () => {
      setPlaying(false);
      URL.revokeObjectURL(url);
    });
    el.addEventListener("error", () => {
      setPlaying(false);
      URL.revokeObjectURL(url);
    });
  }, [artifact.id, onGetPlaybackUrl, playing, audioEl]);
  const canTranscribe = artifact.state === "queued" || artifact.state === "saved";
  const canRetry = artifact.state === "failed";
  const canPlay = !!onGetPlaybackUrl && artifact.size > 0 && artifact.state !== "recording" && artifact.state !== "paused";
  const isBusy = artifact.state === "transcribing" || artifact.state === "uploading";
  return /* @__PURE__ */ jsxs12(
    "div",
    {
      className: `flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/10 ${className}`,
      children: [
        /* @__PURE__ */ jsx18(StateIcon, { state: artifact.state }),
        /* @__PURE__ */ jsxs12("div", { className: "flex-1 min-w-0 space-y-0.5", children: [
          /* @__PURE__ */ jsxs12("div", { className: "flex items-center gap-2 text-xs", children: [
            /* @__PURE__ */ jsx18("span", { className: "font-medium text-white/80", children: artifactLabel(artifact.state) }),
            /* @__PURE__ */ jsx18("span", { className: "text-white/40", children: "\xB7" }),
            /* @__PURE__ */ jsx18("span", { className: "text-white/50", children: formatArtifactDuration(artifact.durationMs) }),
            /* @__PURE__ */ jsx18("span", { className: "text-white/40", children: "\xB7" }),
            /* @__PURE__ */ jsx18("span", { className: "text-white/50", children: formatArtifactSize(artifact.size) })
          ] }),
          artifact.state === "transcribed" && artifact.transcript && /* @__PURE__ */ jsx18("p", { className: "text-xs text-white/60 truncate", children: artifact.transcript }),
          artifact.state === "failed" && artifact.errorMessage && /* @__PURE__ */ jsx18("p", { className: "text-xs text-red-400/80 truncate", children: artifact.errorMessage }),
          /* @__PURE__ */ jsx18("p", { className: "text-[10px] text-white/30", children: new Date(artifact.createdAt).toLocaleString("es-MX", {
            hour: "2-digit",
            minute: "2-digit",
            day: "numeric",
            month: "short"
          }) })
        ] }),
        /* @__PURE__ */ jsxs12("div", { className: "flex items-center gap-1 shrink-0", children: [
          canPlay && /* @__PURE__ */ jsx18(
            "button",
            {
              onClick: handlePlay,
              disabled: isBusy,
              className: "p-1.5 rounded-md hover:bg-white/10 text-white/50 hover:text-white/80 transition-colors",
              "aria-label": playing ? "Pausar" : "Reproducir",
              children: /* @__PURE__ */ jsx18(Play4, { className: "w-3.5 h-3.5" })
            }
          ),
          canTranscribe && onTranscribe && /* @__PURE__ */ jsx18(
            "button",
            {
              onClick: () => onTranscribe(artifact.id),
              disabled: isBusy,
              className: "px-2 py-1 rounded-md text-xs bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 transition-colors",
              children: "Transcribir"
            }
          ),
          canRetry && onRetry && /* @__PURE__ */ jsx18(
            "button",
            {
              onClick: () => onRetry(artifact.id),
              className: "p-1.5 rounded-md hover:bg-white/10 text-yellow-400/70 hover:text-yellow-400 transition-colors",
              "aria-label": "Reintentar transcripci\xF3n",
              children: /* @__PURE__ */ jsx18(RotateCcw2, { className: "w-3.5 h-3.5" })
            }
          ),
          onDelete && artifact.state !== "recording" && artifact.state !== "paused" && /* @__PURE__ */ jsx18(
            "button",
            {
              onClick: () => onDelete(artifact.id),
              disabled: isBusy,
              className: "p-1.5 rounded-md hover:bg-white/10 text-white/30 hover:text-red-400 transition-colors",
              "aria-label": "Eliminar audio",
              children: /* @__PURE__ */ jsx18(Trash2, { className: "w-3.5 h-3.5" })
            }
          )
        ] })
      ]
    }
  );
}

// src/voice/AudioQueuePanel.tsx
import { jsx as jsx19, jsxs as jsxs13 } from "react/jsx-runtime";
var DEFAULT_PRIVACY_NOTICE = "Tu audio se guarda localmente hasta que lo transcribas o elimines. No se env\xEDa al servidor hasta que lo solicites.";
function AudioQueuePanel({
  queue,
  className = "",
  privacyNotice = DEFAULT_PRIVACY_NOTICE,
  maxVisible = 6,
  excludeIds = []
}) {
  const {
    artifacts,
    totalBytes,
    isLoading,
    transcribeArtifact,
    retryTranscription,
    deleteArtifact,
    clearTranscribed,
    getPlaybackUrl
  } = queue;
  const visible = artifacts.filter(
    (a) => a.state !== "deleted" && !excludeIds.includes(a.id)
  );
  const hasTranscribed = visible.some((a) => a.state === "transcribed");
  if (isLoading) {
    return /* @__PURE__ */ jsx19("div", { className: `flex items-center justify-center p-4 ${className}`, children: /* @__PURE__ */ jsx19(Loader29, { className: "w-4 h-4 text-white/40 animate-spin" }) });
  }
  if (visible.length === 0) return null;
  return /* @__PURE__ */ jsxs13("div", { className: `space-y-2 ${className}`, children: [
    /* @__PURE__ */ jsxs13("div", { className: "flex items-start gap-2 px-3 py-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20", children: [
      /* @__PURE__ */ jsx19(ShieldAlert, { className: "w-3.5 h-3.5 text-yellow-400 shrink-0 mt-0.5" }),
      /* @__PURE__ */ jsx19("p", { className: "text-[11px] text-yellow-200/70 leading-relaxed", children: privacyNotice })
    ] }),
    /* @__PURE__ */ jsxs13("div", { className: "flex items-center justify-between px-1", children: [
      /* @__PURE__ */ jsxs13("span", { className: "text-xs text-white/50", children: [
        visible.length,
        " audio",
        visible.length !== 1 ? "s" : "",
        " \xB7 ",
        formatArtifactSize(totalBytes)
      ] }),
      hasTranscribed && /* @__PURE__ */ jsxs13(
        "button",
        {
          onClick: clearTranscribed,
          className: "flex items-center gap-1 text-xs text-white/40 hover:text-white/70 transition-colors",
          children: [
            /* @__PURE__ */ jsx19(Trash22, { className: "w-3 h-3" }),
            "Limpiar transcritos"
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsx19(
      "div",
      {
        className: "space-y-1.5 overflow-y-auto",
        style: { maxHeight: `${maxVisible * 68}px` },
        children: visible.map((artifact) => /* @__PURE__ */ jsx19(
          AudioQueueItem,
          {
            artifact,
            onTranscribe: transcribeArtifact,
            onRetry: retryTranscription,
            onDelete: deleteArtifact,
            onGetPlaybackUrl: getPlaybackUrl
          },
          artifact.id
        ))
      }
    )
  ] });
}

// src/voice/AudioDraftPlayer.tsx
import { useState as useState11, useCallback as useCallback8, useEffect as useEffect9 } from "react";
import { Play as Play5, Pause as Pause3, Trash2 as Trash23, Loader2 as Loader210, RotateCcw as RotateCcw3, ArrowUp, CirclePause } from "lucide-react";
import { Fragment as Fragment2, jsx as jsx20, jsxs as jsxs14 } from "react/jsx-runtime";
var BAR_HEIGHTS = [
  0.4,
  0.7,
  0.5,
  0.9,
  0.6,
  0.8,
  0.45,
  1,
  0.55,
  0.75,
  0.5,
  0.85,
  0.4,
  0.65,
  0.7,
  0.5,
  0.9,
  0.6,
  0.45,
  0.8
];
function AudioDraftPlayer({
  artifact,
  onGetPlaybackUrl,
  onPrimary,
  onDiscard,
  onRetry,
  onResume,
  primaryActionLabel = "Transcribir",
  className = ""
}) {
  const [playing, setPlaying] = useState11(false);
  const [audioEl, setAudioEl] = useState11(null);
  useEffect9(() => {
    return () => {
      audioEl?.pause();
    };
  }, [audioEl]);
  const handlePlay = useCallback8(async () => {
    if (!onGetPlaybackUrl) return;
    if (playing && audioEl) {
      audioEl.pause();
      setPlaying(false);
      return;
    }
    const el = new Audio();
    const url = await onGetPlaybackUrl(artifact.id);
    if (!url) return;
    el.src = url;
    setAudioEl(el);
    setPlaying(true);
    const cleanup = () => {
      setPlaying(false);
      URL.revokeObjectURL(url);
    };
    el.addEventListener("ended", cleanup, { once: true });
    el.addEventListener("error", cleanup, { once: true });
    el.play().catch(() => {
      setPlaying(false);
      URL.revokeObjectURL(url);
    });
  }, [artifact.id, onGetPlaybackUrl, playing, audioEl]);
  const isPaused = artifact.state === "paused";
  const isSaving = artifact.state === "stopping";
  const isBusy = artifact.state === "transcribing" || artifact.state === "uploading";
  const isFailed = artifact.state === "failed";
  const canPlay = !!onGetPlaybackUrl && artifact.size > 0 && !isSaving && !isBusy && !isPaused;
  return /* @__PURE__ */ jsxs14(
    "div",
    {
      className: `fi-audio-draft flex items-center gap-3 px-3 py-3 rounded-2xl bg-white/[0.06] border border-white/[0.12] backdrop-blur-sm ${className}`,
      role: "group",
      "aria-label": "Audio grabado",
      children: [
        /* @__PURE__ */ jsx20(
          "button",
          {
            type: "button",
            onClick: handlePlay,
            disabled: !canPlay,
            "aria-label": isPaused ? "Grabaci\xF3n en pausa" : playing ? "Pausar reproducci\xF3n" : "Reproducir grabaci\xF3n",
            className: "fi-audio-draft-play shrink-0 w-11 h-11 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95",
            children: isSaving || isBusy ? /* @__PURE__ */ jsx20(Loader210, { className: "w-5 h-5 animate-spin text-amber-400" }) : isPaused ? /* @__PURE__ */ jsx20(CirclePause, { className: "w-5 h-5 text-yellow-400" }) : playing ? /* @__PURE__ */ jsx20(Pause3, { className: "w-5 h-5 text-white/90" }) : /* @__PURE__ */ jsx20(Play5, { className: "w-5 h-5 text-white/90 ml-0.5" })
          }
        ),
        /* @__PURE__ */ jsxs14("div", { className: "flex-1 min-w-0", children: [
          /* @__PURE__ */ jsx20("div", { className: "flex items-end gap-[3px] h-8", "aria-hidden": "true", children: BAR_HEIGHTS.map((h, i) => /* @__PURE__ */ jsx20(
            "span",
            {
              className: `flex-1 rounded-full transition-colors duration-150 ${playing ? "bg-emerald-400/80" : isPaused ? "bg-yellow-400/50" : "bg-white/40"}`,
              style: { height: `${Math.round(h * 100)}%` }
            },
            i
          )) }),
          /* @__PURE__ */ jsxs14("div", { className: "flex items-center gap-1.5 mt-1.5 text-xs text-white/50", children: [
            /* @__PURE__ */ jsx20("span", { className: "tabular-nums", children: formatArtifactDuration(artifact.durationMs) }),
            artifact.size > 0 && /* @__PURE__ */ jsxs14(Fragment2, { children: [
              /* @__PURE__ */ jsx20("span", { className: "text-white/20", children: "\xB7" }),
              /* @__PURE__ */ jsx20("span", { children: formatArtifactSize(artifact.size) })
            ] }),
            isPaused && /* @__PURE__ */ jsx20("span", { className: "text-yellow-400/70 font-medium", children: "En pausa" }),
            isSaving && /* @__PURE__ */ jsx20("span", { className: "text-amber-400/70", children: "Guardando\u2026" }),
            isBusy && /* @__PURE__ */ jsx20("span", { className: "text-blue-400/70", children: "Transcribiendo\u2026" }),
            isFailed && artifact.errorMessage && /* @__PURE__ */ jsx20("span", { className: "text-red-400/70 truncate", children: artifact.errorMessage })
          ] })
        ] }),
        /* @__PURE__ */ jsxs14("div", { className: "flex items-center gap-1 shrink-0", children: [
          onDiscard && !isBusy && /* @__PURE__ */ jsx20(
            "button",
            {
              type: "button",
              onClick: () => onDiscard(artifact.id),
              "aria-label": "Descartar grabaci\xF3n",
              className: "fi-audio-draft-discard p-2 rounded-xl text-white/35 hover:text-red-400 hover:bg-white/10 transition-colors",
              children: /* @__PURE__ */ jsx20(Trash23, { className: "w-4 h-4" })
            }
          ),
          onResume ? /* @__PURE__ */ jsxs14(
            "button",
            {
              type: "button",
              onClick: onResume,
              "aria-label": "Reanudar grabaci\xF3n",
              className: "fi-audio-draft-resume flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-300 transition-all active:scale-95",
              children: [
                /* @__PURE__ */ jsx20(Play5, { className: "w-3.5 h-3.5 ml-0.5" }),
                "Reanudar"
              ]
            }
          ) : isFailed && onRetry ? /* @__PURE__ */ jsx20(
            "button",
            {
              type: "button",
              onClick: () => onRetry(artifact.id),
              "aria-label": "Reintentar",
              className: "fi-audio-draft-retry p-2 rounded-xl text-amber-400/80 hover:text-amber-400 hover:bg-white/10 transition-colors",
              children: /* @__PURE__ */ jsx20(RotateCcw3, { className: "w-4 h-4" })
            }
          ) : onPrimary && /* @__PURE__ */ jsxs14(
            "button",
            {
              type: "button",
              onClick: () => onPrimary(artifact.id),
              disabled: isSaving || isBusy,
              className: "fi-audio-draft-primary flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95",
              children: [
                /* @__PURE__ */ jsx20(ArrowUp, { className: "w-3.5 h-3.5" }),
                primaryActionLabel
              ]
            }
          )
        ] })
      ]
    }
  );
}

// src/shell/ChatWidget.tsx
import { useCallback as useCallback10 } from "react";

// src/shell/useChatWidgetState.ts
import { useState as useState12, useCallback as useCallback9 } from "react";
function useChatWidgetState({
  initialOpen,
  initialMode
}) {
  const [isOpen, setIsOpen] = useState12(initialOpen);
  const [viewMode, setViewMode] = useState12(initialMode);
  const [isHistoryOpen, setIsHistoryOpen] = useState12(false);
  const [conversationStarted, setConversationStarted] = useState12(false);
  const [isStartingConversation, _setIsStartingConversation] = useState12(false);
  const open = useCallback9(() => {
    setIsOpen(true);
  }, []);
  const close = useCallback9(() => {
    setIsOpen(false);
    setViewMode("normal");
  }, []);
  const minimize = useCallback9(() => {
    if (viewMode === "expanded") {
      setViewMode("normal");
    }
  }, [viewMode]);
  const maximize = useCallback9(() => {
    setViewMode(viewMode === "expanded" ? "normal" : "expanded");
  }, [viewMode]);
  const toggleDenseMode = useCallback9(() => {
    setViewMode(viewMode === "dense" ? "fullscreen" : "dense");
  }, [viewMode]);
  const openHistory = useCallback9(() => {
    setIsHistoryOpen(true);
  }, []);
  const closeHistory = useCallback9(() => {
    setIsHistoryOpen(false);
  }, []);
  const startConversation = useCallback9(() => {
    setConversationStarted(true);
  }, []);
  const onMessagesLoaded = useCallback9((hasMessages) => {
    if (hasMessages) {
      setConversationStarted(true);
    }
  }, []);
  return {
    isOpen,
    viewMode,
    isHistoryOpen,
    conversationStarted,
    isStartingConversation,
    open,
    close,
    setViewMode,
    minimize,
    maximize,
    toggleDenseMode,
    openHistory,
    closeHistory,
    startConversation,
    onMessagesLoaded
  };
}

// src/shell/useMediaQuery.ts
import { useSyncExternalStore as useSyncExternalStore2 } from "react";
var mqlCache = /* @__PURE__ */ new Map();
function getMql(query, useCache = true) {
  if (typeof window === "undefined" || !("matchMedia" in window)) {
    return null;
  }
  if (useCache) {
    const cached = mqlCache.get(query);
    if (cached) return cached;
  }
  const mql = window.matchMedia(query);
  if (useCache) {
    mqlCache.set(query, mql);
  }
  return mql;
}
function useMediaQuery(query, options) {
  const ssrMatch = options?.ssrMatch ?? false;
  const useRaf = options?.useRaf ?? true;
  const cache = options?.cache ?? true;
  const mql = getMql(query, cache);
  const getSnapshot = () => mql ? mql.matches : ssrMatch;
  const getServerSnapshot = () => ssrMatch;
  const subscribe = (onStoreChange) => {
    if (!mql) return () => {
    };
    let rafId = 0;
    const handler = () => {
      if (!useRaf) {
        onStoreChange();
        return;
      }
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => onStoreChange());
    };
    const mqlAny = mql;
    if (typeof mqlAny.addEventListener === "function") {
      mqlAny.addEventListener("change", handler);
    } else if (typeof mqlAny.addListener === "function") {
      mqlAny.addListener(handler);
    }
    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      if (typeof mqlAny.removeEventListener === "function") {
        mqlAny.removeEventListener("change", handler);
      } else if (typeof mqlAny.removeListener === "function") {
        mqlAny.removeListener(handler);
      }
    };
  };
  return useSyncExternalStore2(subscribe, getSnapshot, getServerSnapshot);
}
function useBreakpoints(breakpoints, options) {
  const isMobile = useMediaQuery(breakpoints.mobile, { ssrMatch: options?.ssrMatch });
  const isTablet = useMediaQuery(breakpoints.tablet, { ssrMatch: options?.ssrMatch });
  const isDesktop = useMediaQuery(breakpoints.desktop, { ssrMatch: options?.ssrMatch });
  return { isMobile, isTablet, isDesktop };
}
function clearMediaQueryCache() {
  mqlCache.clear();
}

// src/shell/config.ts
var defaultTheme = {
  background: {
    header: "bg-gradient-to-r from-emerald-600 to-cyan-600",
    body: "bg-slate-950",
    input: "bg-slate-800"
  },
  border: {
    main: "border-slate-700",
    input: "border-slate-700",
    bubble: "border-slate-600/60"
  },
  text: {
    primary: "text-white",
    secondary: "text-slate-200",
    muted: "text-slate-400",
    accent: "text-emerald-300"
  },
  accent: { from: "from-emerald-600", to: "to-cyan-600" },
  shadow: "shadow-2xl",
  timestamp: {
    text: "text-slate-400/70",
    tooltip: "bg-slate-800/95 text-slate-200"
  }
};
var defaultBehavior = {
  autoScroll: true,
  showTyping: true,
  groupMessages: true,
  groupThresholdMinutes: 2,
  showDayDividers: true,
  animateEntrance: true,
  maxMessages: 100,
  inputPlaceholder: "Escribe tu mensaje...",
  enableReactions: false,
  enableReadReceipts: false,
  enableThinking: true,
  showThinking: true
};
var defaultTimestampConfig = {
  show: true,
  format: "smart",
  showTooltip: true,
  relativeThreshold: 60,
  showSeconds: false,
  position: "inline",
  updateInterval: 6e4
};
var defaultAnimationConfig = {
  entrance: { enabled: true, duration: "0.4s", easing: "ease-out" },
  typing: { dotDuration: "1.4s", dotDelay: "0.2s" },
  scroll: { behavior: "smooth", duration: 300 }
};
var defaultChatConfig = {
  title: "Free Intelligence",
  subtitle: void 0,
  theme: defaultTheme,
  behavior: defaultBehavior,
  timestamp: defaultTimestampConfig,
  animation: defaultAnimationConfig,
  footer: void 0,
  dimensions: { width: "24rem", height: "600px", minHeight: "400px", maxHeight: "80vh" }
};
function mergeChatConfig(custom) {
  if (!custom) return defaultChatConfig;
  return {
    ...defaultChatConfig,
    ...custom,
    theme: { ...defaultChatConfig.theme, ...custom.theme },
    behavior: { ...defaultChatConfig.behavior, ...custom.behavior },
    timestamp: { ...defaultChatConfig.timestamp, ...custom.timestamp },
    animation: { ...defaultChatConfig.animation, ...custom.animation }
  };
}
var CHAT_BREAKPOINTS = {
  mobile: "(max-width: 639.98px)",
  tablet: "(min-width: 640px) and (max-width: 1023.98px)",
  desktop: "(min-width: 1024px)"
};

// src/shell/FloatingButton.tsx
import { MessageCircle } from "lucide-react";
import { jsx as jsx21, jsxs as jsxs15 } from "react/jsx-runtime";
function FloatingButton({ onClick, isMobile }) {
  const buttonSize = isMobile ? "w-16 h-16" : "w-14 h-14";
  const iconSize = isMobile ? "h-7 w-7" : "h-6 w-6";
  const buttonPosition = isMobile ? "bottom-4 right-4" : "bottom-6 right-6";
  return /* @__PURE__ */ jsxs15(
    "button",
    {
      onClick,
      className: `
        fixed ${buttonPosition} ${buttonSize}
        fi-fab-emerald z-50 group
      `,
      "aria-label": "Chat with Free Intelligence",
      children: [
        /* @__PURE__ */ jsx21(MessageCircle, { className: `${iconSize} text-white` }),
        /* @__PURE__ */ jsx21("span", { className: "fi-dot-pulse-red" }),
        !isMobile && /* @__PURE__ */ jsx21("div", { className: "fi-tooltip-right", children: "Habla con Free Intelligence" })
      ]
    }
  );
}

// src/shell/ChatContent.tsx
import { Loader2 as Loader213 } from "lucide-react";

// src/shell/ChatWidgetContainer.tsx
import { MessageCircle as MessageCircle2 } from "lucide-react";
import { Fragment as Fragment3, jsx as jsx22, jsxs as jsxs16 } from "react/jsx-runtime";
function ChatWidgetContainer(props) {
  const { mode, title, children, embedded = false, onModeChange } = props;
  const { isMobile, isTablet } = useBreakpoints(CHAT_BREAKPOINTS, {
    ssrMatch: false
  });
  const effectiveMode = mode === "minimized" ? "minimized" : isMobile ? mode === "dense" ? "dense" : "fullscreen" : isTablet && (mode === "normal" || mode === "expanded") ? "expanded" : mode;
  if (effectiveMode === "minimized") {
    return /* @__PURE__ */ jsxs16("div", { className: "chat-container-minimized", onClick: () => onModeChange("normal"), children: [
      /* @__PURE__ */ jsx22(MessageCircle2, { className: "chat-container-minimized-icon" }),
      /* @__PURE__ */ jsx22("span", { className: "chat-container-minimized-title", children: title }),
      /* @__PURE__ */ jsx22(
        "button",
        {
          onClick: (e) => {
            e.stopPropagation();
            onModeChange("normal");
          },
          className: "ml-2 fi-hover-ghost",
          "aria-label": "Expand chat",
          children: /* @__PURE__ */ jsx22("div", { className: "chat-container-minimized-pulse" })
        }
      )
    ] });
  }
  if (effectiveMode === "expanded" && isTablet) {
    return /* @__PURE__ */ jsxs16(Fragment3, { children: [
      /* @__PURE__ */ jsx22("div", { className: "chat-backdrop", onClick: () => onModeChange("normal") }),
      /* @__PURE__ */ jsx22(
        "div",
        {
          className: "chat-container-expanded-tablet",
          style: { width: "min(90vw, 900px)", height: "min(90vh, 800px)" },
          children
        }
      )
    ] });
  }
  if (effectiveMode === "expanded") {
    return /* @__PURE__ */ jsx22(
      "div",
      {
        className: "chat-container-expanded",
        style: {
          width: "min(80vw, 1200px)",
          height: "700px",
          maxWidth: "calc(100vw - 3rem)",
          maxHeight: "calc(100vh - 3rem)"
        },
        children
      }
    );
  }
  if (embedded && (effectiveMode === "fullscreen" || effectiveMode === "dense")) {
    return /* @__PURE__ */ jsx22("div", { className: "chat-container-embedded", children });
  }
  if (effectiveMode === "dense") {
    return /* @__PURE__ */ jsx22("div", { className: "chat-container-dense", children });
  }
  if (effectiveMode === "fullscreen") {
    return /* @__PURE__ */ jsx22("div", { className: "chat-container-fullscreen", children });
  }
  return /* @__PURE__ */ jsx22("div", { className: "chat-container-normal", children });
}

// src/shell/ChatWidgetHeader.tsx
import { X, Minimize2, Maximize2, MessageCircle as MessageCircle3, Search } from "lucide-react";
import { Fragment as Fragment4, jsx as jsx23, jsxs as jsxs17 } from "react/jsx-runtime";
var HEADER_BTN_CLASS = "fi-btn-ghost fi-btn-sm chat-header-btn";
var DEFAULT_HEADER_GRADIENT = "bg-gradient-to-r from-emerald-600 to-cyan-600";
function ChatWidgetHeader({
  title,
  subtitle,
  backgroundClass = DEFAULT_HEADER_GRADIENT,
  mode,
  showControls = true,
  showHistorySearch = true,
  onNavigate,
  onMinimize,
  onMaximize,
  onToggleDenseMode,
  onClose,
  onHistorySearch
}) {
  return /* @__PURE__ */ jsxs17("div", { className: `${backgroundClass} chat-header`, children: [
    /* @__PURE__ */ jsxs17("div", { className: "flex items-center gap-3 min-w-0", children: [
      /* @__PURE__ */ jsx23(
        "button",
        {
          type: "button",
          onClick: () => onNavigate?.("chat"),
          className: "chat-header-icon",
          title: "Abrir chat completo",
          "aria-label": "Abrir chat completo",
          children: /* @__PURE__ */ jsx23(MessageCircle3, { className: "h-5 w-5 text-white" })
        }
      ),
      /* @__PURE__ */ jsxs17("div", { className: "min-w-0", children: [
        /* @__PURE__ */ jsx23("h3", { className: "chat-header-title", children: title }),
        subtitle && /* @__PURE__ */ jsx23("p", { className: "chat-header-subtitle", children: subtitle })
      ] })
    ] }),
    /* @__PURE__ */ jsx23("div", { className: "chat-header-controls", children: showControls && /* @__PURE__ */ jsxs17(Fragment4, { children: [
      showHistorySearch && onHistorySearch && mode !== "minimized" && /* @__PURE__ */ jsx23("button", { onClick: onHistorySearch, className: HEADER_BTN_CLASS, "aria-label": "Search history", title: "Buscar en historial", type: "button", children: /* @__PURE__ */ jsx23(Search, { className: "h-4 w-4" }) }),
      mode === "fullscreen" && onToggleDenseMode && /* @__PURE__ */ jsx23("button", { onClick: onToggleDenseMode, className: HEADER_BTN_CLASS, "aria-label": "Cambiar a modo denso", title: "Modo denso (sin controles)", type: "button", children: /* @__PURE__ */ jsxs17("svg", { xmlns: "http://www.w3.org/2000/svg", width: "16", height: "16", fill: "currentColor", viewBox: "0 0 16 16", children: [
        /* @__PURE__ */ jsx23("path", { d: "M0 3.5A1.5 1.5 0 0 1 1.5 2h13A1.5 1.5 0 0 1 16 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 0 12.5v-9zM1.5 3a.5.5 0 0 0-.5.5v9a.5.5 0 0 0 .5.5h13a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-13z" }),
        /* @__PURE__ */ jsx23("path", { d: "M3 4.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5z" })
      ] }) }),
      mode === "dense" && onToggleDenseMode && /* @__PURE__ */ jsx23("button", { onClick: onToggleDenseMode, className: HEADER_BTN_CLASS, "aria-label": "Cambiar a modo expandido", title: "Modo expandido (con controles)", type: "button", children: /* @__PURE__ */ jsxs17("svg", { xmlns: "http://www.w3.org/2000/svg", width: "16", height: "16", fill: "currentColor", viewBox: "0 0 16 16", children: [
        /* @__PURE__ */ jsx23("path", { d: "M14 1a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h12zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z" }),
        /* @__PURE__ */ jsx23("path", { d: "M6.5 4.5a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2V5a.5.5 0 0 1 .5-.5zM8 8.5a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2v-2a.5.5 0 0 1 .5-.5zm3-4a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2V5a.5.5 0 0 1 .5-.5zm0 6a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2v-2a.5.5 0 0 1 .5-.5z" })
      ] }) }),
      mode === "expanded" && /* @__PURE__ */ jsx23("button", { onClick: onMinimize, className: HEADER_BTN_CLASS, "aria-label": "Restaurar tama\xF1o", title: "Restaurar a tama\xF1o normal", type: "button", children: /* @__PURE__ */ jsx23(Minimize2, { className: "h-4 w-4" }) }),
      mode === "normal" && /* @__PURE__ */ jsx23("button", { onClick: onMaximize, className: HEADER_BTN_CLASS, "aria-label": "Expandir", title: "Expandir (60% m\xE1s grande)", type: "button", children: /* @__PURE__ */ jsx23(Maximize2, { className: "h-4 w-4" }) }),
      /* @__PURE__ */ jsx23("button", { onClick: onClose, className: HEADER_BTN_CLASS, "aria-label": "Close", title: "Cerrar", type: "button", children: /* @__PURE__ */ jsx23(X, { className: "h-5 w-5" }) })
    ] }) })
  ] });
}

// src/shell/ChatToolbar.tsx
import { useState as useState13, useRef as useRef8, useEffect as useEffect10 } from "react";
import { createPortal } from "react-dom";
import { Paperclip, Globe, Type, Zap, Trash, Sparkles, BookOpen, Terminal, MoreVertical, Send, Loader2 as Loader211 } from "lucide-react";
import { Fragment as Fragment5, jsx as jsx24, jsxs as jsxs18 } from "react/jsx-runtime";
function ChatToolbar({
  showAttach = true,
  showLanguage = true,
  showFormatting = true,
  showResponseMode = true,
  showVoice = true,
  showPersonaSelector = true,
  showThinkingToggle = true,
  responseMode = "explanatory",
  selectedPersona: _selectedPersona = "general_assistant",
  showThinking = true,
  voiceRecording,
  personaSelector,
  onAttach,
  onLanguage,
  onFormatting,
  onResponseModeToggle,
  onVoiceStart,
  onVoiceStop,
  onShowThinkingToggle,
  showClear = true,
  onClearConversation,
  showCopyCurl = true,
  onCopyCurl,
  onSend,
  canSend = false,
  sendLoading = false
}) {
  const [overflowOpen, setOverflowOpen] = useState13(false);
  const overflowButtonRef = useRef8(null);
  const [dropdownPosition, setDropdownPosition] = useState13({ top: 0, left: 0 });
  useEffect10(() => {
    if (overflowOpen && overflowButtonRef.current) {
      const rect = overflowButtonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.top - 8,
        // 8px margin above button
        left: rect.left
      });
    }
  }, [overflowOpen]);
  const buttonBaseClass = "chat-toolbar-btn";
  const iconClass = "chat-toolbar-icon";
  return /* @__PURE__ */ jsxs18("div", { className: "chat-toolbar", children: [
    /* @__PURE__ */ jsxs18("div", { className: "fi-flex-gap-sm", children: [
      showPersonaSelector && personaSelector,
      (showAttach || showLanguage || showFormatting) && /* @__PURE__ */ jsxs18("div", { className: "relative", children: [
        /* @__PURE__ */ jsx24(
          "button",
          {
            ref: overflowButtonRef,
            onClick: () => setOverflowOpen(!overflowOpen),
            className: buttonBaseClass,
            title: "M\xE1s opciones",
            "aria-label": "M\xE1s opciones",
            children: /* @__PURE__ */ jsx24(MoreVertical, { className: iconClass })
          }
        ),
        overflowOpen && createPortal(
          /* @__PURE__ */ jsxs18(Fragment5, { children: [
            /* @__PURE__ */ jsx24(
              "div",
              {
                className: "fixed inset-0 z-[9998]",
                onClick: () => setOverflowOpen(false),
                "aria-hidden": "true"
              }
            ),
            /* @__PURE__ */ jsxs18(
              "div",
              {
                className: "chat-dropdown",
                style: {
                  top: dropdownPosition.top,
                  left: dropdownPosition.left,
                  transform: "translateY(-100%)"
                },
                children: [
                  showAttach && /* @__PURE__ */ jsxs18(
                    "button",
                    {
                      onClick: () => {
                        onAttach?.();
                        setOverflowOpen(false);
                      },
                      className: "chat-dropdown-item",
                      children: [
                        /* @__PURE__ */ jsx24(Paperclip, { className: "fi-icon-sm" }),
                        /* @__PURE__ */ jsx24("span", { children: "Adjuntar archivo" })
                      ]
                    }
                  ),
                  showLanguage && /* @__PURE__ */ jsxs18(
                    "button",
                    {
                      onClick: () => {
                        onLanguage?.();
                        setOverflowOpen(false);
                      },
                      className: "chat-dropdown-item",
                      children: [
                        /* @__PURE__ */ jsx24(Globe, { className: "fi-icon-sm" }),
                        /* @__PURE__ */ jsx24("span", { children: "Cambiar idioma" })
                      ]
                    }
                  ),
                  showFormatting && /* @__PURE__ */ jsxs18(
                    "button",
                    {
                      onClick: () => {
                        onFormatting?.();
                        setOverflowOpen(false);
                      },
                      className: "chat-dropdown-item",
                      children: [
                        /* @__PURE__ */ jsx24(Type, { className: "fi-icon-sm" }),
                        /* @__PURE__ */ jsx24("span", { children: "Formato de texto" })
                      ]
                    }
                  ),
                  showCopyCurl && /* @__PURE__ */ jsxs18(Fragment5, { children: [
                    /* @__PURE__ */ jsx24("div", { className: "chat-dropdown-divider" }),
                    /* @__PURE__ */ jsxs18(
                      "button",
                      {
                        onClick: () => {
                          onCopyCurl?.();
                          setOverflowOpen(false);
                        },
                        className: "chat-dropdown-item fi-text-warning hover:bg-amber-900/20 hover:text-amber-300",
                        children: [
                          /* @__PURE__ */ jsx24(Terminal, { className: "fi-icon-sm" }),
                          /* @__PURE__ */ jsx24("span", { children: "Copiar plantilla curl" })
                        ]
                      }
                    )
                  ] }),
                  showThinkingToggle && /* @__PURE__ */ jsxs18("div", { className: "@md:hidden", children: [
                    /* @__PURE__ */ jsx24("div", { className: "chat-dropdown-divider" }),
                    /* @__PURE__ */ jsxs18(
                      "button",
                      {
                        onClick: () => {
                          onShowThinkingToggle?.();
                          setOverflowOpen(false);
                        },
                        className: `chat-dropdown-item ${showThinking ? "fi-text-purple hover:bg-purple-900/20" : ""}`,
                        children: [
                          /* @__PURE__ */ jsx24(Sparkles, { className: "fi-icon-sm" }),
                          /* @__PURE__ */ jsx24("span", { children: showThinking ? "Ocultar razonamiento" : "Mostrar razonamiento" })
                        ]
                      }
                    )
                  ] }),
                  showClear && /* @__PURE__ */ jsxs18("div", { className: "@md:hidden", children: [
                    /* @__PURE__ */ jsx24("div", { className: "chat-dropdown-divider" }),
                    /* @__PURE__ */ jsxs18(
                      "button",
                      {
                        onClick: () => {
                          onClearConversation?.();
                          setOverflowOpen(false);
                        },
                        className: "chat-dropdown-item-danger",
                        children: [
                          /* @__PURE__ */ jsx24(Trash, { className: "fi-icon-sm" }),
                          /* @__PURE__ */ jsx24("span", { children: "Limpiar conversaci\xF3n" })
                        ]
                      }
                    )
                  ] })
                ]
              }
            )
          ] }),
          document.body
        )
      ] })
    ] }),
    /* @__PURE__ */ jsxs18("div", { className: "fi-flex-gap-sm", children: [
      showClear && /* @__PURE__ */ jsx24(
        "button",
        {
          onClick: () => onClearConversation?.(),
          className: `${buttonBaseClass} chat-toolbar-btn-danger hidden @md:flex`,
          title: "Limpiar conversaci\xF3n",
          "aria-label": "Limpiar conversaci\xF3n",
          children: /* @__PURE__ */ jsx24(Trash, { className: iconClass })
        }
      ),
      showThinkingToggle && /* @__PURE__ */ jsx24(
        "button",
        {
          onClick: onShowThinkingToggle,
          className: `${buttonBaseClass} hidden @md:flex ${showThinking ? "chat-toolbar-btn-active" : ""}`,
          title: showThinking ? "Razonamiento visible (click para ocultar)" : "Razonamiento oculto (click para mostrar)",
          "aria-label": showThinking ? "Ocultar razonamiento del modelo" : "Mostrar razonamiento del modelo",
          children: /* @__PURE__ */ jsx24(Sparkles, { className: iconClass })
        }
      ),
      showResponseMode && /* @__PURE__ */ jsx24(
        "button",
        {
          onClick: onResponseModeToggle,
          className: `${buttonBaseClass} ${responseMode === "concise" ? "fi-text-info hover:text-cyan-300" : "chat-toolbar-btn-success"}`,
          title: responseMode === "explanatory" ? "Modo: Explicativo (detallado)" : "Modo: Conciso (breve)",
          "aria-label": responseMode === "explanatory" ? "Cambiar a modo conciso" : "Cambiar a modo explicativo",
          children: responseMode === "explanatory" ? /* @__PURE__ */ jsx24(BookOpen, { className: iconClass }) : /* @__PURE__ */ jsx24(Zap, { className: iconClass })
        }
      ),
      showVoice && /* @__PURE__ */ jsx24(
        VoiceMicButton,
        {
          isRecording: voiceRecording?.isRecording || false,
          isTranscribing: voiceRecording?.isTranscribing || false,
          audioLevel: voiceRecording?.audioLevel || 0,
          isSilent: voiceRecording?.isSilent ?? true,
          recordingTime: voiceRecording?.recordingTime || 0,
          onStart: onVoiceStart || (() => {
          }),
          onStop: onVoiceStop || (() => {
          })
        }
      ),
      /* @__PURE__ */ jsx24(
        "button",
        {
          onClick: onSend,
          disabled: !canSend,
          className: `p-2.5 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-200 ${canSend ? "bg-gradient-to-r from-amber-500 to-orange-500 text-slate-900 shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40" : "bg-slate-800 text-slate-500 cursor-not-allowed"}`,
          "aria-label": "Enviar mensaje",
          children: sendLoading ? /* @__PURE__ */ jsx24(Loader211, { className: "h-4 w-4 animate-spin" }) : /* @__PURE__ */ jsx24(Send, { className: "h-4 w-4" })
        }
      )
    ] })
  ] });
}

// src/shell/ChatFilePreview.tsx
import {
  FileText,
  FileCode,
  Image as ImageIcon,
  File,
  X as X2,
  Loader2 as Loader212,
  CheckCircle,
  AlertCircle as AlertCircle4
} from "lucide-react";
import { Fragment as Fragment6, jsx as jsx25, jsxs as jsxs19 } from "react/jsx-runtime";
var FILE_ICONS = {
  "application/pdf": FileText,
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileText,
  "application/msword": FileText,
  "text/plain": File,
  "text/markdown": FileCode,
  "image/png": ImageIcon,
  "image/jpeg": ImageIcon,
  "image/jpg": ImageIcon
};
function formatFileSize(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
function getFileIcon(file) {
  return FILE_ICONS[file.type] || File;
}
function ChatFilePreview({
  file,
  status,
  progress = 0,
  error,
  onCancel
}) {
  const FileIcon = getFileIcon(file);
  const isCompleted = status === "indexed";
  const isError = status === "error";
  const isUploading = status === "uploading";
  const isProcessing = status === "processing" || status === "pending_instructions";
  return /* @__PURE__ */ jsxs19("div", { className: `
      flex items-center gap-3 p-3 rounded-xl border
      ${isError ? "bg-red-900/20 border-red-700/50" : isCompleted ? "bg-emerald-900/20 border-emerald-700/50" : "bg-slate-800/80 border-slate-700/50"}
      transition-colors duration-200
    `, children: [
    /* @__PURE__ */ jsx25("div", { className: `
        p-2 rounded-lg
        ${isError ? "bg-red-900/50" : isCompleted ? "bg-emerald-900/50" : "bg-slate-700"}
      `, children: isProcessing ? /* @__PURE__ */ jsx25(Loader212, { className: "w-5 h-5 fi-text-primary animate-spin" }) : isCompleted ? /* @__PURE__ */ jsx25(CheckCircle, { className: "w-5 h-5 fi-text-success" }) : isError ? /* @__PURE__ */ jsx25(AlertCircle4, { className: "w-5 h-5 fi-text-error" }) : /* @__PURE__ */ jsx25(FileIcon, { className: "w-5 h-5 fi-text" }) }),
    /* @__PURE__ */ jsxs19("div", { className: "flex-1 min-w-0", children: [
      /* @__PURE__ */ jsx25("p", { className: "fi-title-sm-medium truncate", title: file.name, children: file.name }),
      /* @__PURE__ */ jsxs19("div", { className: "flex items-center gap-2 fi-text-xs", children: [
        /* @__PURE__ */ jsx25("span", { children: formatFileSize(file.size) }),
        isUploading && /* @__PURE__ */ jsxs19(Fragment6, { children: [
          /* @__PURE__ */ jsx25("span", { children: "-" }),
          /* @__PURE__ */ jsx25("span", { className: "fi-text-primary", children: progress < 100 ? `Subiendo... ${progress}%` : "Completado" })
        ] }),
        isProcessing && /* @__PURE__ */ jsxs19(Fragment6, { children: [
          /* @__PURE__ */ jsx25("span", { children: "-" }),
          /* @__PURE__ */ jsx25("span", { className: "fi-text-primary", children: "Procesando..." })
        ] }),
        isCompleted && /* @__PURE__ */ jsxs19(Fragment6, { children: [
          /* @__PURE__ */ jsx25("span", { children: "-" }),
          /* @__PURE__ */ jsx25("span", { className: "chat-file-status-indexed", children: "Indexado" })
        ] }),
        isError && error && /* @__PURE__ */ jsxs19(Fragment6, { children: [
          /* @__PURE__ */ jsx25("span", { children: "-" }),
          /* @__PURE__ */ jsx25("span", { className: "fi-text-error truncate", title: error, children: error })
        ] })
      ] }),
      isUploading && /* @__PURE__ */ jsx25("div", { className: "mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden", children: /* @__PURE__ */ jsx25(
        "div",
        {
          className: "fi-progress-bar duration-300",
          style: { width: `${progress}%` }
        }
      ) })
    ] }),
    !isCompleted && !isProcessing && /* @__PURE__ */ jsx25(
      "button",
      {
        type: "button",
        onClick: onCancel,
        className: "fi-btn-ghost fi-btn-sm fi-hover-bg",
        "aria-label": "Cancelar",
        title: "Cancelar",
        children: /* @__PURE__ */ jsx25(X2, { className: "h-4 w-4" })
      }
    )
  ] });
}

// src/shell/ChatStartScreen.tsx
import { Download, MessageSquareText, Monitor, Shield, Sparkles as Sparkles2 } from "lucide-react";
import { Fragment as Fragment7, jsx as jsx26, jsxs as jsxs20 } from "react/jsx-runtime";
function ChatStartScreen({
  isAuthenticated,
  userName,
  onStart,
  onLogin: _onLogin,
  onNavigate,
  isLoading = false
}) {
  if (!isAuthenticated) {
    return /* @__PURE__ */ jsx26("div", { className: "chat-start-screen", children: /* @__PURE__ */ jsxs20("div", { className: "chat-start-container", children: [
      /* @__PURE__ */ jsx26("div", { className: "flex justify-center", children: /* @__PURE__ */ jsx26("div", { className: "chat-start-icon", children: /* @__PURE__ */ jsx26(Monitor, { className: "fi-icon-xl text-purple-400" }) }) }),
      /* @__PURE__ */ jsxs20("div", { className: "fi-stack-sm", children: [
        /* @__PURE__ */ jsx26("h3", { className: "chat-start-title", children: "\xA1Pru\xE9balo en tu escritorio!" }),
        /* @__PURE__ */ jsx26("p", { className: "chat-start-subtitle", children: "IA offline para tu desarrollo profesional. Licencias piloto gratuitas disponibles. \xA1Descarga la tuya!" })
      ] }),
      /* @__PURE__ */ jsxs20(
        "button",
        {
          type: "button",
          onClick: () => onNavigate?.("downloads"),
          className: "chat-start-btn-login",
          children: [
            /* @__PURE__ */ jsx26(Download, { className: "fi-icon-md" }),
            "Ir a Descargas"
          ]
        }
      ),
      /* @__PURE__ */ jsx26("p", { className: "chat-start-hint", children: "100% privado, funciona sin internet" })
    ] }) });
  }
  return /* @__PURE__ */ jsx26("div", { className: "chat-start-screen", children: /* @__PURE__ */ jsxs20("div", { className: "chat-start-container", children: [
    /* @__PURE__ */ jsx26("div", { className: "pt-4 flex justify-center", children: /* @__PURE__ */ jsx26("div", { className: "chat-start-icon-large", children: /* @__PURE__ */ jsx26(Sparkles2, { className: "w-10 h-10 fi-text-purple" }) }) }),
    /* @__PURE__ */ jsxs20("div", { className: "fi-stack-sm", children: [
      /* @__PURE__ */ jsxs20("h3", { className: "chat-start-title-large", children: [
        "Hola, ",
        userName?.split(" ")[0] || "Doctor"
      ] }),
      /* @__PURE__ */ jsx26("p", { className: "chat-start-subtitle", children: "Soy tu asistente de Free Intelligence. Estoy listo para ayudarte con consultas m\xE9dicas, notas SOAP y an\xE1lisis cl\xEDnicos." })
    ] }),
    /* @__PURE__ */ jsxs20("div", { className: "chat-start-features", children: [
      /* @__PURE__ */ jsxs20("div", { className: "chat-start-feature", children: [
        /* @__PURE__ */ jsx26(MessageSquareText, { className: "w-4 h-4 fi-text-purple flex-shrink-0" }),
        /* @__PURE__ */ jsx26("span", { children: "Conversaci\xF3n privada y segura" })
      ] }),
      /* @__PURE__ */ jsxs20("div", { className: "chat-start-feature", children: [
        /* @__PURE__ */ jsx26(Shield, { className: "w-4 h-4 fi-text-green flex-shrink-0" }),
        /* @__PURE__ */ jsx26("span", { children: "Datos encriptados localmente" })
      ] })
    ] }),
    /* @__PURE__ */ jsx26("button", { onClick: onStart, disabled: isLoading, className: "chat-start-btn-begin", children: isLoading ? /* @__PURE__ */ jsxs20(Fragment7, { children: [
      /* @__PURE__ */ jsx26("div", { className: "chat-start-spinner" }),
      "Iniciando..."
    ] }) : /* @__PURE__ */ jsxs20(Fragment7, { children: [
      /* @__PURE__ */ jsx26(MessageSquareText, { className: "w-5 h-5" }),
      "Comenzar conversaci\xF3n"
    ] }) }),
    /* @__PURE__ */ jsx26("p", { className: "chat-start-hint", children: "Presiona para iniciar una nueva conversaci\xF3n" })
  ] }) });
}

// src/shell/ChatContent.tsx
import { jsx as jsx27, jsxs as jsxs21 } from "react/jsx-runtime";
function ChatContent({
  config,
  embedded,
  isAuthenticated,
  userName,
  viewMode,
  isHistoryOpen,
  isStartingConversation,
  messageCount,
  loading,
  isTyping,
  loadingInitial,
  customEmptyState,
  customQuickReplies,
  message,
  responseMode,
  selectedPersona,
  personaName,
  showThinking = true,
  voiceState,
  uploadFile,
  uploadStatus,
  isUploadActive,
  onNavigate,
  onModeChange,
  onMinimize,
  onMaximize,
  onToggleDenseMode,
  onClose,
  onHistoryOpen,
  onHistoryClose,
  onStartConversation,
  onLogin,
  onMessageChange,
  onSend,
  onResponseModeToggle,
  onShowThinkingToggle,
  onPersonaChange: _onPersonaChange,
  onClearConversation,
  onVoiceStart,
  onVoiceStop,
  onAttach,
  onCancelUpload,
  onCopyCurl,
  personaSelector,
  renderHistory,
  renderMessages
}) {
  const dynamicPlaceholder = personaName ? `Escribe a ${personaName}...` : "Escribe tu mensaje...";
  const showVoice = typeof onVoiceStart === "function";
  const showAttach = typeof onAttach === "function";
  const showResponseMode = typeof onResponseModeToggle === "function";
  const showThinkingToggle = typeof onShowThinkingToggle === "function";
  const showClear = typeof onClearConversation === "function";
  const showPersonaSelector = personaSelector != null;
  return /* @__PURE__ */ jsxs21("div", { className: "relative flex h-full flex-1 flex-col overflow-hidden", children: [
    !isHistoryOpen && /* @__PURE__ */ jsxs21(
      ChatWidgetContainer,
      {
        mode: viewMode,
        title: config.title,
        embedded,
        onModeChange,
        children: [
          viewMode !== "dense" && !embedded && /* @__PURE__ */ jsx27(
            ChatWidgetHeader,
            {
              title: config.title,
              subtitle: config.subtitle,
              backgroundClass: config.theme.background.header,
              mode: viewMode,
              showControls: !embedded,
              onNavigate,
              onMinimize,
              onMaximize,
              onToggleDenseMode,
              onClose,
              onHistorySearch: onHistoryOpen
            }
          ),
          messageCount === 0 && loadingInitial ? /* @__PURE__ */ jsx27("div", { className: "flex h-full items-center justify-center", children: /* @__PURE__ */ jsx27(Loader213, { className: "h-8 w-8 animate-spin text-slate-400" }) }) : messageCount === 0 && !isTyping && customEmptyState ? customEmptyState : messageCount === 0 && !isTyping ? /* @__PURE__ */ jsx27(
            ChatStartScreen,
            {
              isAuthenticated,
              userName,
              onStart: onStartConversation,
              onLogin,
              onNavigate,
              isLoading: isStartingConversation
            }
          ) : renderMessages?.({ viewMode }),
          customQuickReplies,
          viewMode !== "dense" && /* @__PURE__ */ jsx27("div", { className: "chat-input-wrapper", children: /* @__PURE__ */ jsxs21("div", { className: "chat-input-floating-box", children: [
            isUploadActive && uploadFile && /* @__PURE__ */ jsx27(
              ChatFilePreview,
              {
                file: uploadFile,
                status: uploadStatus ?? "selecting",
                onCancel: onCancelUpload ?? (() => {
                })
              }
            ),
            /* @__PURE__ */ jsx27(
              Composer,
              {
                message,
                loading,
                placeholder: dynamicPlaceholder,
                onMessageChange,
                onSend,
                maxRows: 5,
                areaClassName: "chat-input-area-top",
                wrapperClassName: "flex-1",
                textareaClassName: "chat-textarea"
              }
            ),
            /* @__PURE__ */ jsx27(
              ChatToolbar,
              {
                responseMode,
                selectedPersona,
                showThinking,
                voiceRecording: voiceState,
                personaSelector,
                showAttach,
                showLanguage: false,
                showFormatting: false,
                showResponseMode,
                showVoice,
                showPersonaSelector,
                showThinkingToggle,
                showClear,
                showCopyCurl: typeof onCopyCurl === "function",
                onResponseModeToggle,
                onShowThinkingToggle,
                onClearConversation,
                onCopyCurl,
                onAttach,
                onVoiceStart,
                onVoiceStop,
                onSend,
                canSend: message.trim().length > 0 && !loading,
                sendLoading: loading
              }
            )
          ] }) })
        ]
      }
    ),
    isHistoryOpen && renderHistory?.({ onClose: onHistoryClose })
  ] });
}

// src/shell/ChatWidget.tsx
import { jsx as jsx28 } from "react/jsx-runtime";
function ChatWidget({
  chatHook,
  config: customConfig,
  user,
  isAuthenticated = false,
  onLogin,
  onNavigate,
  isMobile: isMobileProp,
  initialOpen = false,
  initialMode = "normal",
  embedded = false,
  message,
  onMessageChange,
  onSend,
  responseMode,
  selectedPersona,
  personaName,
  showThinking,
  onResponseModeToggle,
  onShowThinkingToggle,
  onPersonaChange,
  onClearConversation,
  voiceState,
  onVoiceStart,
  onVoiceStop,
  uploadFile,
  uploadStatus,
  isUploadActive,
  onAttach,
  onCancelUpload,
  isStartingConversation = false,
  onStartConversation,
  personaSelector,
  renderHistory,
  renderMessages,
  onCopyCurl
}) {
  const internalIsMobile = useMediaQuery(CHAT_BREAKPOINTS.mobile, { ssrMatch: false });
  const isMobile = isMobileProp ?? internalIsMobile;
  const config = mergeChatConfig(customConfig);
  const widgetState = useChatWidgetState({ initialOpen, initialMode });
  const messages = chatHook.messages;
  const messageCount = messages.length;
  const loading = chatHook.loading;
  const isTyping = chatHook.isTyping;
  const loadingInitial = chatHook.loadingInitial ?? false;
  const customEmptyState = chatHook.customEmptyState;
  const customQuickReplies = chatHook.customQuickReplies;
  const handleOpen = useCallback10(() => {
    widgetState.open();
    widgetState.onMessagesLoaded(messageCount > 0);
  }, [widgetState, messageCount]);
  if (!widgetState.isOpen) {
    if (embedded) return null;
    return /* @__PURE__ */ jsx28(FloatingButton, { onClick: handleOpen, isMobile });
  }
  return /* @__PURE__ */ jsx28(
    ChatContent,
    {
      config,
      embedded,
      isAuthenticated,
      userName: user?.name || void 0,
      viewMode: widgetState.viewMode,
      isHistoryOpen: widgetState.isHistoryOpen,
      isStartingConversation,
      messageCount,
      loading,
      isTyping,
      loadingInitial,
      customEmptyState,
      customQuickReplies,
      message,
      responseMode,
      selectedPersona,
      personaName,
      showThinking,
      voiceState,
      uploadFile,
      uploadStatus,
      isUploadActive,
      onNavigate,
      onModeChange: widgetState.setViewMode,
      onMinimize: widgetState.minimize,
      onMaximize: widgetState.maximize,
      onToggleDenseMode: widgetState.toggleDenseMode,
      onClose: widgetState.close,
      onHistoryOpen: widgetState.openHistory,
      onHistoryClose: widgetState.closeHistory,
      onStartConversation: onStartConversation ?? widgetState.startConversation,
      onLogin: onLogin ?? (() => {
      }),
      onMessageChange,
      onSend,
      onResponseModeToggle,
      onShowThinkingToggle,
      onPersonaChange,
      onClearConversation,
      onVoiceStart,
      onVoiceStop,
      onAttach,
      onCancelUpload,
      onCopyCurl,
      personaSelector,
      renderHistory,
      renderMessages
    }
  );
}

// src/shell/ChatSurface.tsx
import { jsx as jsx29 } from "react/jsx-runtime";
function ChatSurface(props) {
  return /* @__PURE__ */ jsx29(
    ChatWidget,
    {
      ...props,
      embedded: true,
      initialOpen: true,
      initialMode: "fullscreen"
    }
  );
}

// src/persona-selector/PersonaSelector.tsx
import {
  useCallback as useCallback11,
  useEffect as useEffect11,
  useId as useId2,
  useRef as useRef9,
  useState as useState14
} from "react";
import { createPortal as createPortal2 } from "react-dom";
import { ChevronDown, Check as Check2 } from "lucide-react";
import { Fragment as Fragment8, jsx as jsx30, jsxs as jsxs22 } from "react/jsx-runtime";
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
  const [isOpen, setIsOpen] = useState14(false);
  const [position, setPosition] = useState14({ top: 0, left: 0, width: 0 });
  const triggerRef = useRef9(null);
  const contentRef = useRef9(null);
  const reactId = useId2();
  const triggerId = `persona-trigger-${reactId}`;
  const contentId = `persona-content-${reactId}`;
  const close = useCallback11(() => setIsOpen(false), []);
  useEffect11(() => {
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
  useEffect11(() => {
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
  useEffect11(() => {
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
    return renderLoading ? /* @__PURE__ */ jsx30(Fragment8, { children: renderLoading() }) : /* @__PURE__ */ jsx30("div", { role: "status", "aria-live": "polite", children: "Cargando..." });
  }
  const selectedPersona = personas.find((p) => getPersonaId(p) === selected);
  const triggerInner = renderTriggerValue ? renderTriggerValue(selectedPersona, isOpen) : selectedPersona && getPersonaLabel ? getPersonaLabel(selectedPersona) : placeholder;
  const content = isOpen ? /* @__PURE__ */ jsxs22(
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
          return /* @__PURE__ */ jsxs22(
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
                /* @__PURE__ */ jsxs22("div", { className: "flex items-center gap-2 mb-1", children: [
                  renderPersonaIcon?.(persona, ctx),
                  /* @__PURE__ */ jsx30(
                    "span",
                    {
                      className: `font-medium text-sm ${isSelected ? "text-purple-200" : "text-slate-200"}`,
                      children: getPersonaLabel?.(persona) ?? id
                    }
                  ),
                  isSelected && /* @__PURE__ */ jsx30(Check2, { className: "w-4 h-4 fi-text-purple ml-auto" })
                ] }),
                description && /* @__PURE__ */ jsx30("p", { className: "fi-text-xs mb-2 line-clamp-2", children: description }),
                (badge || meta) && /* @__PURE__ */ jsxs22("div", { className: "flex items-center gap-2 flex-wrap", children: [
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
  return /* @__PURE__ */ jsxs22("div", { className, "data-persona-root": true, children: [
    /* @__PURE__ */ jsxs22(
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
          /* @__PURE__ */ jsx30(
            ChevronDown,
            {
              className: `h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`
            }
          )
        ]
      }
    ),
    content && createPortal2(content, document.body)
  ] });
}
export {
  AUDIO_QUEUE_DEFAULTS,
  AudioDraftPlayer,
  AudioPlayer,
  AudioQueueItem,
  AudioQueuePanel,
  AudioQueueStore,
  AudioVisualizer,
  AutoResizeTextarea,
  BUTTON_SIZES,
  CHAT_BREAKPOINTS,
  COLOR_THEMES,
  ChatContent,
  ChatFilePreview,
  ChatStartScreen,
  ChatSurface,
  ChatToolbar,
  ChatWidget,
  ChatWidgetContainer,
  ChatWidgetHeader,
  CollapsibleText,
  Composer,
  ComposerMicSlot,
  CopyButton,
  FloatingButton,
  MessageBubble,
  MessageContent,
  MessageList,
  PersonaSelector,
  PulseRings,
  RecordingButton,
  RecordingTimer,
  RichAudioPlayer,
  STATUS_TEXT_EN,
  STATUS_TEXT_ES,
  SpeakButton,
  StatusText,
  VoiceMicButton,
  artifactLabel,
  clearMediaQueryCache,
  createAudioPlayer,
  defaultAnimationConfig,
  defaultBehavior,
  defaultChatConfig,
  defaultTheme,
  defaultTimestampConfig,
  formatArtifactDuration,
  formatArtifactSize,
  formatPlaybackTime,
  formatRecordingTime,
  glassTheme,
  isPending,
  isTerminal,
  makeArtifactId,
  makeRecorder,
  markdownStyles,
  mergeChatConfig,
  messageStyles,
  normalizeLevels,
  normalizeStreamedMarkdown,
  resampleLevels,
  useAudioAnalysis,
  useAudioPlayer,
  useAudioQueue,
  useBreakpoints,
  useChatWidgetState,
  useDictation,
  useDurableRecording,
  useMediaQuery,
  useRecorder,
  useVoice
};
//# sourceMappingURL=index.js.map