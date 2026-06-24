'use client';

// src/shell/ChatWidget.tsx
import { useCallback as useCallback8 } from "react";

// src/shell/useChatWidgetState.ts
import { useState, useCallback } from "react";
function useChatWidgetState({
  initialOpen,
  initialMode
}) {
  const [isOpen, setIsOpen] = useState(initialOpen);
  const [viewMode, setViewMode] = useState(initialMode);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [conversationStarted, setConversationStarted] = useState(false);
  const [isStartingConversation, _setIsStartingConversation] = useState(false);
  const open = useCallback(() => {
    setIsOpen(true);
  }, []);
  const close = useCallback(() => {
    setIsOpen(false);
    setViewMode("normal");
  }, []);
  const minimize = useCallback(() => {
    if (viewMode === "expanded") {
      setViewMode("normal");
    }
  }, [viewMode]);
  const maximize = useCallback(() => {
    setViewMode(viewMode === "expanded" ? "normal" : "expanded");
  }, [viewMode]);
  const toggleDenseMode = useCallback(() => {
    setViewMode(viewMode === "dense" ? "fullscreen" : "dense");
  }, [viewMode]);
  const openHistory = useCallback(() => {
    setIsHistoryOpen(true);
  }, []);
  const closeHistory = useCallback(() => {
    setIsHistoryOpen(false);
  }, []);
  const startConversation = useCallback(() => {
    setConversationStarted(true);
  }, []);
  const onMessagesLoaded = useCallback((hasMessages) => {
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
import { useSyncExternalStore } from "react";
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
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
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
import { jsx, jsxs } from "react/jsx-runtime";
function FloatingButton({ onClick, isMobile }) {
  const buttonSize = isMobile ? "w-16 h-16" : "w-14 h-14";
  const iconSize = isMobile ? "h-7 w-7" : "h-6 w-6";
  const buttonPosition = isMobile ? "bottom-4 right-4" : "bottom-6 right-6";
  return /* @__PURE__ */ jsxs(
    "button",
    {
      onClick,
      className: `
        fixed ${buttonPosition} ${buttonSize}
        fi-fab-emerald z-50 group
      `,
      "aria-label": "Chat with Free Intelligence",
      children: [
        /* @__PURE__ */ jsx(MessageCircle, { className: `${iconSize} text-white` }),
        /* @__PURE__ */ jsx("span", { className: "fi-dot-pulse-red" }),
        !isMobile && /* @__PURE__ */ jsx("div", { className: "fi-tooltip-right", children: "Habla con Free Intelligence" })
      ]
    }
  );
}

// src/shell/ChatContent.tsx
import { Loader2 as Loader213 } from "lucide-react";

// src/composer/AutoResizeTextarea.tsx
import {
  forwardRef,
  useEffect,
  useId,
  useImperativeHandle,
  useRef,
  useState as useState2
} from "react";
import { jsx as jsx2, jsxs as jsxs2 } from "react/jsx-runtime";
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
  const [rows, setRows] = useState2(1);
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
  return /* @__PURE__ */ jsxs2("div", { className: `relative ${wrapperClassName}`, style: wrapperStyle, children: [
    /* @__PURE__ */ jsx2(
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
    showCounter && maxLength && /* @__PURE__ */ jsxs2("div", { className: isOverLimit ? "chat-char-counter-error" : isNearLimit ? "chat-char-counter-warning" : "chat-char-counter-ok", children: [
      charCount,
      "/",
      maxLength
    ] })
  ] });
});

// src/composer/Composer.tsx
import { jsx as jsx3 } from "react/jsx-runtime";
function Composer({
  message,
  loading = false,
  disabled = false,
  placeholder = "Escribe tu mensaje...",
  onMessageChange,
  onSend,
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
  return /* @__PURE__ */ jsx3("div", { className: areaClassName, children: /* @__PURE__ */ jsx3(
    AutoResizeTextarea,
    {
      ref: textareaRef,
      id,
      name,
      value: message,
      onChange: (e) => onMessageChange(e.target.value),
      onKeyDown: handleKeyDown,
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

// src/shell/ChatWidgetContainer.tsx
import { MessageCircle as MessageCircle2 } from "lucide-react";
import { Fragment, jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
function ChatWidgetContainer(props) {
  const { mode, title, children, embedded = false, onModeChange } = props;
  const { isMobile, isTablet } = useBreakpoints(CHAT_BREAKPOINTS, {
    ssrMatch: false
  });
  const effectiveMode = mode === "minimized" ? "minimized" : isMobile ? mode === "dense" ? "dense" : "fullscreen" : isTablet && (mode === "normal" || mode === "expanded") ? "expanded" : mode;
  if (effectiveMode === "minimized") {
    return /* @__PURE__ */ jsxs3("div", { className: "chat-container-minimized", onClick: () => onModeChange("normal"), children: [
      /* @__PURE__ */ jsx4(MessageCircle2, { className: "chat-container-minimized-icon" }),
      /* @__PURE__ */ jsx4("span", { className: "chat-container-minimized-title", children: title }),
      /* @__PURE__ */ jsx4(
        "button",
        {
          onClick: (e) => {
            e.stopPropagation();
            onModeChange("normal");
          },
          className: "ml-2 fi-hover-ghost",
          "aria-label": "Expand chat",
          children: /* @__PURE__ */ jsx4("div", { className: "chat-container-minimized-pulse" })
        }
      )
    ] });
  }
  if (effectiveMode === "expanded" && isTablet) {
    return /* @__PURE__ */ jsxs3(Fragment, { children: [
      /* @__PURE__ */ jsx4("div", { className: "chat-backdrop", onClick: () => onModeChange("normal") }),
      /* @__PURE__ */ jsx4(
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
    return /* @__PURE__ */ jsx4(
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
    return /* @__PURE__ */ jsx4("div", { className: "chat-container-embedded", children });
  }
  if (effectiveMode === "dense") {
    return /* @__PURE__ */ jsx4("div", { className: "chat-container-dense", children });
  }
  if (effectiveMode === "fullscreen") {
    return /* @__PURE__ */ jsx4("div", { className: "chat-container-fullscreen", children });
  }
  return /* @__PURE__ */ jsx4("div", { className: "chat-container-normal", children });
}

// src/shell/ChatWidgetHeader.tsx
import { X, Minimize2, Maximize2, MessageCircle as MessageCircle3, Search } from "lucide-react";
import { Fragment as Fragment2, jsx as jsx5, jsxs as jsxs4 } from "react/jsx-runtime";
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
  return /* @__PURE__ */ jsxs4("div", { className: `${backgroundClass} chat-header`, children: [
    /* @__PURE__ */ jsxs4("div", { className: "flex items-center gap-3 min-w-0", children: [
      /* @__PURE__ */ jsx5(
        "button",
        {
          type: "button",
          onClick: () => onNavigate?.("chat"),
          className: "chat-header-icon",
          title: "Abrir chat completo",
          "aria-label": "Abrir chat completo",
          children: /* @__PURE__ */ jsx5(MessageCircle3, { className: "h-5 w-5 text-white" })
        }
      ),
      /* @__PURE__ */ jsxs4("div", { className: "min-w-0", children: [
        /* @__PURE__ */ jsx5("h3", { className: "chat-header-title", children: title }),
        subtitle && /* @__PURE__ */ jsx5("p", { className: "chat-header-subtitle", children: subtitle })
      ] })
    ] }),
    /* @__PURE__ */ jsx5("div", { className: "chat-header-controls", children: showControls && /* @__PURE__ */ jsxs4(Fragment2, { children: [
      showHistorySearch && onHistorySearch && mode !== "minimized" && /* @__PURE__ */ jsx5("button", { onClick: onHistorySearch, className: HEADER_BTN_CLASS, "aria-label": "Search history", title: "Buscar en historial", type: "button", children: /* @__PURE__ */ jsx5(Search, { className: "h-4 w-4" }) }),
      mode === "fullscreen" && onToggleDenseMode && /* @__PURE__ */ jsx5("button", { onClick: onToggleDenseMode, className: HEADER_BTN_CLASS, "aria-label": "Cambiar a modo denso", title: "Modo denso (sin controles)", type: "button", children: /* @__PURE__ */ jsxs4("svg", { xmlns: "http://www.w3.org/2000/svg", width: "16", height: "16", fill: "currentColor", viewBox: "0 0 16 16", children: [
        /* @__PURE__ */ jsx5("path", { d: "M0 3.5A1.5 1.5 0 0 1 1.5 2h13A1.5 1.5 0 0 1 16 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 0 12.5v-9zM1.5 3a.5.5 0 0 0-.5.5v9a.5.5 0 0 0 .5.5h13a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-13z" }),
        /* @__PURE__ */ jsx5("path", { d: "M3 4.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5z" })
      ] }) }),
      mode === "dense" && onToggleDenseMode && /* @__PURE__ */ jsx5("button", { onClick: onToggleDenseMode, className: HEADER_BTN_CLASS, "aria-label": "Cambiar a modo expandido", title: "Modo expandido (con controles)", type: "button", children: /* @__PURE__ */ jsxs4("svg", { xmlns: "http://www.w3.org/2000/svg", width: "16", height: "16", fill: "currentColor", viewBox: "0 0 16 16", children: [
        /* @__PURE__ */ jsx5("path", { d: "M14 1a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h12zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z" }),
        /* @__PURE__ */ jsx5("path", { d: "M6.5 4.5a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2V5a.5.5 0 0 1 .5-.5zM8 8.5a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2v-2a.5.5 0 0 1 .5-.5zm3-4a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2V5a.5.5 0 0 1 .5-.5zm0 6a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2v-2a.5.5 0 0 1 .5-.5z" })
      ] }) }),
      mode === "expanded" && /* @__PURE__ */ jsx5("button", { onClick: onMinimize, className: HEADER_BTN_CLASS, "aria-label": "Restaurar tama\xF1o", title: "Restaurar a tama\xF1o normal", type: "button", children: /* @__PURE__ */ jsx5(Minimize2, { className: "h-4 w-4" }) }),
      mode === "normal" && /* @__PURE__ */ jsx5("button", { onClick: onMaximize, className: HEADER_BTN_CLASS, "aria-label": "Expandir", title: "Expandir (60% m\xE1s grande)", type: "button", children: /* @__PURE__ */ jsx5(Maximize2, { className: "h-4 w-4" }) }),
      /* @__PURE__ */ jsx5("button", { onClick: onClose, className: HEADER_BTN_CLASS, "aria-label": "Close", title: "Cerrar", type: "button", children: /* @__PURE__ */ jsx5(X, { className: "h-5 w-5" }) })
    ] }) })
  ] });
}

// src/shell/ChatToolbar.tsx
import { useState as useState12, useRef as useRef7, useEffect as useEffect11 } from "react";
import { createPortal } from "react-dom";
import { Paperclip, Globe, Type, Zap, Trash, Sparkles, BookOpen, Terminal, MoreVertical, Send, Loader2 as Loader211 } from "lucide-react";

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

// src/voice/recording/RecordingButton.tsx
import { jsx as jsx6 } from "react/jsx-runtime";
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
    return /* @__PURE__ */ jsx6(
      "button",
      {
        ref,
        onClick,
        disabled,
        "aria-label": ariaLabel,
        className: `fi-recording-btn-base ${sizeConfig.button} ${bgColor} ${borderStyle} ${animate} ${disabled ? "rec-btn-disabled" : "rec-btn-enabled"} ${className}`,
        children: /* @__PURE__ */ jsx6(
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
import { Fragment as Fragment3, jsx as jsx7, jsxs as jsxs5 } from "react/jsx-runtime";
function PingRings({ color = "yellow-500" }) {
  const bgClass = `rec-pulse-bg-${color}`;
  return /* @__PURE__ */ jsxs5(Fragment3, { children: [
    /* @__PURE__ */ jsx7(
      "div",
      {
        className: `rec-pulse-ping-primary ${bgClass}`
      }
    ),
    /* @__PURE__ */ jsx7(
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
  return /* @__PURE__ */ jsx7(Fragment3, { children: rings.map((ring, i) => /* @__PURE__ */ jsx7(
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
  return /* @__PURE__ */ jsx7(Fragment3, { children: rings.map((ring, i) => /* @__PURE__ */ jsx7(
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
  return /* @__PURE__ */ jsxs5("div", { className: `rec-pulse-container ${className}`, children: [
    style === "ping" && /* @__PURE__ */ jsx7(PingRings, { color }),
    style === "rings" && /* @__PURE__ */ jsx7(ConcentricRings, { color }),
    style === "vad" && /* @__PURE__ */ jsx7(VADRings, { audioLevel, isSilent })
  ] });
}

// src/voice/recording/RecordingTimer.tsx
import { motion as motion2 } from "framer-motion";
import { jsx as jsx8, jsxs as jsxs6 } from "react/jsx-runtime";
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
  return /* @__PURE__ */ jsxs6("div", { className: `rec-timer-wrap ${SIZE_CLASSES[size]} ${className}`, children: [
    showDot && /* @__PURE__ */ jsx8(
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
    /* @__PURE__ */ jsx8("span", { className: `${textColor} rec-timer-value`, children: formatRecordingTime(time) })
  ] });
}

// src/voice/recording/StatusText.tsx
import { Loader2 as Loader22 } from "lucide-react";
import { motion as motion3 } from "framer-motion";
import { jsx as jsx9, jsxs as jsxs7 } from "react/jsx-runtime";

// src/voice/VoiceMicButton.tsx
import { Mic, Square, Loader2 as Loader23 } from "lucide-react";
import { motion as motion4 } from "framer-motion";
import { jsx as jsx10, jsxs as jsxs8 } from "react/jsx-runtime";
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
  return /* @__PURE__ */ jsxs8("div", { className: `relative inline-flex items-center gap-3 ${className}`, children: [
    /* @__PURE__ */ jsxs8("div", { className: "relative", children: [
      isRecording && /* @__PURE__ */ jsx10(
        PulseRings,
        {
          style: "vad",
          audioLevel,
          isSilent
        }
      ),
      /* @__PURE__ */ jsx10(
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
          children: /* @__PURE__ */ jsx10(
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
    isRecording && /* @__PURE__ */ jsx10(
      motion4.div,
      {
        initial: { opacity: 0, x: -10 },
        animate: { opacity: 1, x: 0 },
        exit: { opacity: 0, x: -10 },
        children: /* @__PURE__ */ jsx10(
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
    isTranscribing && !isRecording && /* @__PURE__ */ jsx10(
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
    @media (pointer: coarse), (max-width: 768px) {
      .${FI_TOUCH_TARGET_CLASS} {
        min-width: 44px;
        min-height: 44px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
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
function withTouchTarget(className) {
  return className ? `${FI_TOUCH_TARGET_CLASS} ${className}` : FI_TOUCH_TARGET_CLASS;
}

// src/voice/SpeakButton.tsx
import { jsx as jsx11 } from "react/jsx-runtime";

// src/voice/useAudioPlayer.ts
import { useEffect as useEffect3, useMemo, useRef as useRef2, useSyncExternalStore as useSyncExternalStore2 } from "react";

// src/voice/AudioPlayer.tsx
import { Play as Play2, Pause, Square as Square2, Loader2 as Loader25, AlertCircle } from "lucide-react";
import { useEffect as useEffect4 } from "react";
import { jsx as jsx12, jsxs as jsxs9 } from "react/jsx-runtime";

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
import { jsx as jsx13, jsxs as jsxs10 } from "react/jsx-runtime";

// src/voice/AudioVisualizer.tsx
import { jsx as jsx14 } from "react/jsx-runtime";

// src/voice/ComposerMicSlot.tsx
import { Mic as Mic2, MicOff, Square as Square4, Loader2 as Loader27 } from "lucide-react";
import { jsx as jsx15 } from "react/jsx-runtime";

// src/voice/useVoice.ts
import { useCallback as useCallback2, useRef as useRef3, useState as useState3 } from "react";

// src/voice/useDictation.ts
import { useCallback as useCallback4, useState as useState6 } from "react";

// src/voice/useRecorder.ts
import { useState as useState4, useRef as useRef4, useCallback as useCallback3 } from "react";

// src/voice/useAudioAnalysis.ts
import { useState as useState5, useRef as useRef5, useEffect as useEffect6 } from "react";

// src/voice/audioArtifact.ts
var AUDIO_QUEUE_DEFAULTS = {
  maxItems: 10,
  maxBytes: 50 * 1024 * 1024,
  // 50 MB total queue
  maxBytesPerItem: 10 * 1024 * 1024
  // 10 MB per artifact
};

// src/voice/useAudioQueueStore.ts
import { useMemo as useMemo2 } from "react";

// src/voice/useDurableRecording.ts
import { useState as useState7, useRef as useRef6, useCallback as useCallback5, useEffect as useEffect7 } from "react";

// src/voice/useAudioQueue.ts
import { useState as useState8, useEffect as useEffect8, useCallback as useCallback6 } from "react";

// src/voice/AudioQueuePanel.tsx
import { useEffect as useEffect9, useState as useState10 } from "react";
import { Loader2 as Loader29, Trash2 as Trash22, Info } from "lucide-react";

// src/voice/AudioQueueItem.tsx
import { useState as useState9, useCallback as useCallback7 } from "react";
import {
  Mic as Mic3,
  PauseCircle,
  CheckCircle2,
  CheckCheck,
  AlertCircle as AlertCircle3,
  Loader2 as Loader28,
  Play as Play4,
  RotateCcw as RotateCcw2,
  Trash2,
  FileAudio
} from "lucide-react";
import { jsx as jsx16, jsxs as jsxs11 } from "react/jsx-runtime";

// src/voice/AudioQueuePanel.tsx
import { jsx as jsx17, jsxs as jsxs12 } from "react/jsx-runtime";

// src/voice/AudioDraftPlayer.tsx
import { useState as useState11, useEffect as useEffect10 } from "react";
import { Play as Play5, Trash2 as Trash23, Loader2 as Loader210, RotateCcw as RotateCcw3, ArrowUp } from "lucide-react";
import { jsx as jsx18, jsxs as jsxs13 } from "react/jsx-runtime";

// src/shell/ChatToolbar.tsx
import { Fragment as Fragment4, jsx as jsx19, jsxs as jsxs14 } from "react/jsx-runtime";
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
  const [overflowOpen, setOverflowOpen] = useState12(false);
  const overflowButtonRef = useRef7(null);
  const [dropdownPosition, setDropdownPosition] = useState12({ top: 0, left: 0 });
  useEffect11(() => {
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
  return /* @__PURE__ */ jsxs14("div", { className: "chat-toolbar", children: [
    /* @__PURE__ */ jsxs14("div", { className: "fi-flex-gap-sm", children: [
      showPersonaSelector && personaSelector,
      (showAttach || showLanguage || showFormatting) && /* @__PURE__ */ jsxs14("div", { className: "relative", children: [
        /* @__PURE__ */ jsx19(
          "button",
          {
            ref: overflowButtonRef,
            onClick: () => setOverflowOpen(!overflowOpen),
            className: buttonBaseClass,
            title: "M\xE1s opciones",
            "aria-label": "M\xE1s opciones",
            children: /* @__PURE__ */ jsx19(MoreVertical, { className: iconClass })
          }
        ),
        overflowOpen && createPortal(
          /* @__PURE__ */ jsxs14(Fragment4, { children: [
            /* @__PURE__ */ jsx19(
              "div",
              {
                className: "fixed inset-0 z-[9998]",
                onClick: () => setOverflowOpen(false),
                "aria-hidden": "true"
              }
            ),
            /* @__PURE__ */ jsxs14(
              "div",
              {
                className: "chat-dropdown",
                style: {
                  top: dropdownPosition.top,
                  left: dropdownPosition.left,
                  transform: "translateY(-100%)"
                },
                children: [
                  showAttach && /* @__PURE__ */ jsxs14(
                    "button",
                    {
                      onClick: () => {
                        onAttach?.();
                        setOverflowOpen(false);
                      },
                      className: "chat-dropdown-item",
                      children: [
                        /* @__PURE__ */ jsx19(Paperclip, { className: "fi-icon-sm" }),
                        /* @__PURE__ */ jsx19("span", { children: "Adjuntar archivo" })
                      ]
                    }
                  ),
                  showLanguage && /* @__PURE__ */ jsxs14(
                    "button",
                    {
                      onClick: () => {
                        onLanguage?.();
                        setOverflowOpen(false);
                      },
                      className: "chat-dropdown-item",
                      children: [
                        /* @__PURE__ */ jsx19(Globe, { className: "fi-icon-sm" }),
                        /* @__PURE__ */ jsx19("span", { children: "Cambiar idioma" })
                      ]
                    }
                  ),
                  showFormatting && /* @__PURE__ */ jsxs14(
                    "button",
                    {
                      onClick: () => {
                        onFormatting?.();
                        setOverflowOpen(false);
                      },
                      className: "chat-dropdown-item",
                      children: [
                        /* @__PURE__ */ jsx19(Type, { className: "fi-icon-sm" }),
                        /* @__PURE__ */ jsx19("span", { children: "Formato de texto" })
                      ]
                    }
                  ),
                  showCopyCurl && /* @__PURE__ */ jsxs14(Fragment4, { children: [
                    /* @__PURE__ */ jsx19("div", { className: "chat-dropdown-divider" }),
                    /* @__PURE__ */ jsxs14(
                      "button",
                      {
                        onClick: () => {
                          onCopyCurl?.();
                          setOverflowOpen(false);
                        },
                        className: "chat-dropdown-item fi-text-warning hover:bg-amber-900/20 hover:text-amber-300",
                        children: [
                          /* @__PURE__ */ jsx19(Terminal, { className: "fi-icon-sm" }),
                          /* @__PURE__ */ jsx19("span", { children: "Copiar plantilla curl" })
                        ]
                      }
                    )
                  ] }),
                  showThinkingToggle && /* @__PURE__ */ jsxs14("div", { className: "@md:hidden", children: [
                    /* @__PURE__ */ jsx19("div", { className: "chat-dropdown-divider" }),
                    /* @__PURE__ */ jsxs14(
                      "button",
                      {
                        onClick: () => {
                          onShowThinkingToggle?.();
                          setOverflowOpen(false);
                        },
                        className: `chat-dropdown-item ${showThinking ? "fi-text-purple hover:bg-purple-900/20" : ""}`,
                        children: [
                          /* @__PURE__ */ jsx19(Sparkles, { className: "fi-icon-sm" }),
                          /* @__PURE__ */ jsx19("span", { children: showThinking ? "Ocultar razonamiento" : "Mostrar razonamiento" })
                        ]
                      }
                    )
                  ] }),
                  showClear && /* @__PURE__ */ jsxs14("div", { className: "@md:hidden", children: [
                    /* @__PURE__ */ jsx19("div", { className: "chat-dropdown-divider" }),
                    /* @__PURE__ */ jsxs14(
                      "button",
                      {
                        onClick: () => {
                          onClearConversation?.();
                          setOverflowOpen(false);
                        },
                        className: "chat-dropdown-item-danger",
                        children: [
                          /* @__PURE__ */ jsx19(Trash, { className: "fi-icon-sm" }),
                          /* @__PURE__ */ jsx19("span", { children: "Limpiar conversaci\xF3n" })
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
    /* @__PURE__ */ jsxs14("div", { className: "fi-flex-gap-sm", children: [
      showClear && /* @__PURE__ */ jsx19(
        "button",
        {
          onClick: () => onClearConversation?.(),
          className: `${buttonBaseClass} chat-toolbar-btn-danger hidden @md:flex`,
          title: "Limpiar conversaci\xF3n",
          "aria-label": "Limpiar conversaci\xF3n",
          children: /* @__PURE__ */ jsx19(Trash, { className: iconClass })
        }
      ),
      showThinkingToggle && /* @__PURE__ */ jsx19(
        "button",
        {
          onClick: onShowThinkingToggle,
          className: `${buttonBaseClass} hidden @md:flex ${showThinking ? "chat-toolbar-btn-active" : ""}`,
          title: showThinking ? "Razonamiento visible (click para ocultar)" : "Razonamiento oculto (click para mostrar)",
          "aria-label": showThinking ? "Ocultar razonamiento del modelo" : "Mostrar razonamiento del modelo",
          children: /* @__PURE__ */ jsx19(Sparkles, { className: iconClass })
        }
      ),
      showResponseMode && /* @__PURE__ */ jsx19(
        "button",
        {
          onClick: onResponseModeToggle,
          className: `${buttonBaseClass} ${responseMode === "concise" ? "fi-text-info hover:text-cyan-300" : "chat-toolbar-btn-success"}`,
          title: responseMode === "explanatory" ? "Modo: Explicativo (detallado)" : "Modo: Conciso (breve)",
          "aria-label": responseMode === "explanatory" ? "Cambiar a modo conciso" : "Cambiar a modo explicativo",
          children: responseMode === "explanatory" ? /* @__PURE__ */ jsx19(BookOpen, { className: iconClass }) : /* @__PURE__ */ jsx19(Zap, { className: iconClass })
        }
      ),
      showVoice && /* @__PURE__ */ jsx19(
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
      /* @__PURE__ */ jsx19(
        "button",
        {
          onClick: onSend,
          disabled: !canSend,
          className: `p-2.5 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-200 ${canSend ? "bg-gradient-to-r from-amber-500 to-orange-500 text-slate-900 shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40" : "bg-slate-800 text-slate-500 cursor-not-allowed"}`,
          "aria-label": "Enviar mensaje",
          children: sendLoading ? /* @__PURE__ */ jsx19(Loader211, { className: "h-4 w-4 animate-spin" }) : /* @__PURE__ */ jsx19(Send, { className: "h-4 w-4" })
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
import { Fragment as Fragment5, jsx as jsx20, jsxs as jsxs15 } from "react/jsx-runtime";
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
  return /* @__PURE__ */ jsxs15("div", { className: `
      flex items-center gap-3 p-3 rounded-xl border
      ${isError ? "bg-red-900/20 border-red-700/50" : isCompleted ? "bg-emerald-900/20 border-emerald-700/50" : "bg-slate-800/80 border-slate-700/50"}
      transition-colors duration-200
    `, children: [
    /* @__PURE__ */ jsx20("div", { className: `
        p-2 rounded-lg
        ${isError ? "bg-red-900/50" : isCompleted ? "bg-emerald-900/50" : "bg-slate-700"}
      `, children: isProcessing ? /* @__PURE__ */ jsx20(Loader212, { className: "w-5 h-5 fi-text-primary animate-spin" }) : isCompleted ? /* @__PURE__ */ jsx20(CheckCircle, { className: "w-5 h-5 fi-text-success" }) : isError ? /* @__PURE__ */ jsx20(AlertCircle4, { className: "w-5 h-5 fi-text-error" }) : /* @__PURE__ */ jsx20(FileIcon, { className: "w-5 h-5 fi-text" }) }),
    /* @__PURE__ */ jsxs15("div", { className: "flex-1 min-w-0", children: [
      /* @__PURE__ */ jsx20("p", { className: "fi-title-sm-medium truncate", title: file.name, children: file.name }),
      /* @__PURE__ */ jsxs15("div", { className: "flex items-center gap-2 fi-text-xs", children: [
        /* @__PURE__ */ jsx20("span", { children: formatFileSize(file.size) }),
        isUploading && /* @__PURE__ */ jsxs15(Fragment5, { children: [
          /* @__PURE__ */ jsx20("span", { children: "-" }),
          /* @__PURE__ */ jsx20("span", { className: "fi-text-primary", children: progress < 100 ? `Subiendo... ${progress}%` : "Completado" })
        ] }),
        isProcessing && /* @__PURE__ */ jsxs15(Fragment5, { children: [
          /* @__PURE__ */ jsx20("span", { children: "-" }),
          /* @__PURE__ */ jsx20("span", { className: "fi-text-primary", children: "Procesando..." })
        ] }),
        isCompleted && /* @__PURE__ */ jsxs15(Fragment5, { children: [
          /* @__PURE__ */ jsx20("span", { children: "-" }),
          /* @__PURE__ */ jsx20("span", { className: "chat-file-status-indexed", children: "Indexado" })
        ] }),
        isError && error && /* @__PURE__ */ jsxs15(Fragment5, { children: [
          /* @__PURE__ */ jsx20("span", { children: "-" }),
          /* @__PURE__ */ jsx20("span", { className: "fi-text-error truncate", title: error, children: error })
        ] })
      ] }),
      isUploading && /* @__PURE__ */ jsx20("div", { className: "mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden", children: /* @__PURE__ */ jsx20(
        "div",
        {
          className: "fi-progress-bar duration-300",
          style: { width: `${progress}%` }
        }
      ) })
    ] }),
    !isCompleted && !isProcessing && /* @__PURE__ */ jsx20(
      "button",
      {
        type: "button",
        onClick: onCancel,
        className: "fi-btn-ghost fi-btn-sm fi-hover-bg",
        "aria-label": "Cancelar",
        title: "Cancelar",
        children: /* @__PURE__ */ jsx20(X2, { className: "h-4 w-4" })
      }
    )
  ] });
}

// src/shell/ChatStartScreen.tsx
import { Download, MessageSquareText, Monitor, Shield, Sparkles as Sparkles2 } from "lucide-react";
import { Fragment as Fragment6, jsx as jsx21, jsxs as jsxs16 } from "react/jsx-runtime";
function ChatStartScreen({
  isAuthenticated,
  userName,
  onStart,
  onLogin: _onLogin,
  onNavigate,
  isLoading = false
}) {
  if (!isAuthenticated) {
    return /* @__PURE__ */ jsx21("div", { className: "chat-start-screen", children: /* @__PURE__ */ jsxs16("div", { className: "chat-start-container", children: [
      /* @__PURE__ */ jsx21("div", { className: "flex justify-center", children: /* @__PURE__ */ jsx21("div", { className: "chat-start-icon", children: /* @__PURE__ */ jsx21(Monitor, { className: "fi-icon-xl text-purple-400" }) }) }),
      /* @__PURE__ */ jsxs16("div", { className: "fi-stack-sm", children: [
        /* @__PURE__ */ jsx21("h3", { className: "chat-start-title", children: "\xA1Pru\xE9balo en tu escritorio!" }),
        /* @__PURE__ */ jsx21("p", { className: "chat-start-subtitle", children: "IA offline para tu desarrollo profesional. Licencias piloto gratuitas disponibles. \xA1Descarga la tuya!" })
      ] }),
      /* @__PURE__ */ jsxs16(
        "button",
        {
          type: "button",
          onClick: () => onNavigate?.("downloads"),
          className: "chat-start-btn-login",
          children: [
            /* @__PURE__ */ jsx21(Download, { className: "fi-icon-md" }),
            "Ir a Descargas"
          ]
        }
      ),
      /* @__PURE__ */ jsx21("p", { className: "chat-start-hint", children: "100% privado, funciona sin internet" })
    ] }) });
  }
  return /* @__PURE__ */ jsx21("div", { className: "chat-start-screen", children: /* @__PURE__ */ jsxs16("div", { className: "chat-start-container", children: [
    /* @__PURE__ */ jsx21("div", { className: "pt-4 flex justify-center", children: /* @__PURE__ */ jsx21("div", { className: "chat-start-icon-large", children: /* @__PURE__ */ jsx21(Sparkles2, { className: "w-10 h-10 fi-text-purple" }) }) }),
    /* @__PURE__ */ jsxs16("div", { className: "fi-stack-sm", children: [
      /* @__PURE__ */ jsxs16("h3", { className: "chat-start-title-large", children: [
        "Hola, ",
        userName?.split(" ")[0] || "Doctor"
      ] }),
      /* @__PURE__ */ jsx21("p", { className: "chat-start-subtitle", children: "Soy tu asistente de Free Intelligence. Estoy listo para ayudarte con consultas m\xE9dicas, notas SOAP y an\xE1lisis cl\xEDnicos." })
    ] }),
    /* @__PURE__ */ jsxs16("div", { className: "chat-start-features", children: [
      /* @__PURE__ */ jsxs16("div", { className: "chat-start-feature", children: [
        /* @__PURE__ */ jsx21(MessageSquareText, { className: "w-4 h-4 fi-text-purple flex-shrink-0" }),
        /* @__PURE__ */ jsx21("span", { children: "Conversaci\xF3n privada y segura" })
      ] }),
      /* @__PURE__ */ jsxs16("div", { className: "chat-start-feature", children: [
        /* @__PURE__ */ jsx21(Shield, { className: "w-4 h-4 fi-text-green flex-shrink-0" }),
        /* @__PURE__ */ jsx21("span", { children: "Datos encriptados localmente" })
      ] })
    ] }),
    /* @__PURE__ */ jsx21("button", { onClick: onStart, disabled: isLoading, className: "chat-start-btn-begin", children: isLoading ? /* @__PURE__ */ jsxs16(Fragment6, { children: [
      /* @__PURE__ */ jsx21("div", { className: "chat-start-spinner" }),
      "Iniciando..."
    ] }) : /* @__PURE__ */ jsxs16(Fragment6, { children: [
      /* @__PURE__ */ jsx21(MessageSquareText, { className: "w-5 h-5" }),
      "Comenzar conversaci\xF3n"
    ] }) }),
    /* @__PURE__ */ jsx21("p", { className: "chat-start-hint", children: "Presiona para iniciar una nueva conversaci\xF3n" })
  ] }) });
}

// src/shell/ChatContent.tsx
import { jsx as jsx22, jsxs as jsxs17 } from "react/jsx-runtime";
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
  return /* @__PURE__ */ jsxs17("div", { className: "relative flex h-full flex-1 flex-col overflow-hidden", children: [
    !isHistoryOpen && /* @__PURE__ */ jsxs17(
      ChatWidgetContainer,
      {
        mode: viewMode,
        title: config.title,
        embedded,
        onModeChange,
        children: [
          viewMode !== "dense" && !embedded && /* @__PURE__ */ jsx22(
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
          messageCount === 0 && loadingInitial ? /* @__PURE__ */ jsx22("div", { className: "flex h-full items-center justify-center", children: /* @__PURE__ */ jsx22(Loader213, { className: "h-8 w-8 animate-spin text-slate-400" }) }) : messageCount === 0 && !isTyping && customEmptyState ? customEmptyState : messageCount === 0 && !isTyping ? /* @__PURE__ */ jsx22(
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
          viewMode !== "dense" && /* @__PURE__ */ jsx22("div", { className: "chat-input-wrapper", children: /* @__PURE__ */ jsxs17("div", { className: "chat-input-floating-box", children: [
            isUploadActive && uploadFile && /* @__PURE__ */ jsx22(
              ChatFilePreview,
              {
                file: uploadFile,
                status: uploadStatus ?? "selecting",
                onCancel: onCancelUpload ?? (() => {
                })
              }
            ),
            /* @__PURE__ */ jsx22(
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
            /* @__PURE__ */ jsx22(
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
import { jsx as jsx23 } from "react/jsx-runtime";
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
  const handleOpen = useCallback8(() => {
    widgetState.open();
    widgetState.onMessagesLoaded(messageCount > 0);
  }, [widgetState, messageCount]);
  if (!widgetState.isOpen) {
    if (embedded) return null;
    return /* @__PURE__ */ jsx23(FloatingButton, { onClick: handleOpen, isMobile });
  }
  return /* @__PURE__ */ jsx23(
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
import { jsx as jsx24 } from "react/jsx-runtime";
function ChatSurface(props) {
  return /* @__PURE__ */ jsx24(
    ChatWidget,
    {
      ...props,
      embedded: true,
      initialOpen: true,
      initialMode: "fullscreen"
    }
  );
}
export {
  CHAT_BREAKPOINTS,
  ChatContent,
  ChatFilePreview,
  ChatStartScreen,
  ChatSurface,
  ChatToolbar,
  ChatWidget,
  ChatWidgetContainer,
  ChatWidgetHeader,
  FI_TOUCH_TARGET_CLASS,
  FloatingButton,
  clearMediaQueryCache,
  defaultAnimationConfig,
  defaultBehavior,
  defaultChatConfig,
  defaultTheme,
  defaultTimestampConfig,
  ensureTouchTargetStyle,
  mergeChatConfig,
  useBreakpoints,
  useChatWidgetState,
  useMediaQuery,
  useTouchTargetStyle,
  withTouchTarget
};
//# sourceMappingURL=index.js.map