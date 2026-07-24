'use client';

// src/shell/ChatFilePreview.tsx
import {
  FileText,
  FileCode,
  Image as ImageIcon,
  File,
  X,
  Loader2,
  CheckCircle,
  AlertCircle
} from "lucide-react";
import { Fragment, jsx, jsxs } from "react/jsx-runtime";
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
  const isProcessing = status === "processing";
  const isAwaitingUser = status === "pending_instructions";
  return /* @__PURE__ */ jsxs("div", { className: `
      flex items-center gap-3 p-3 rounded-xl border
      ${isError ? "bg-red-900/20 border-red-700/50" : isCompleted ? "bg-emerald-900/20 border-emerald-700/50" : "bg-slate-800/80 border-slate-700/50"}
      transition-colors duration-200
    `, children: [
    /* @__PURE__ */ jsx("div", { className: `
        p-2 rounded-lg
        ${isError ? "bg-red-900/50" : isCompleted ? "bg-emerald-900/50" : "bg-slate-700"}
      `, children: isProcessing ? /* @__PURE__ */ jsx(Loader2, { className: "w-5 h-5 fi-text-primary animate-spin" }) : isCompleted ? /* @__PURE__ */ jsx(CheckCircle, { className: "w-5 h-5 fi-text-success" }) : isError ? /* @__PURE__ */ jsx(AlertCircle, { className: "w-5 h-5 fi-text-error" }) : /* @__PURE__ */ jsx(FileIcon, { className: "w-5 h-5 fi-text" }) }),
    /* @__PURE__ */ jsxs("div", { className: "flex-1 min-w-0", children: [
      /* @__PURE__ */ jsx("p", { className: "fi-title-sm-medium truncate", title: file.name, children: file.name }),
      /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-2 fi-text-xs", children: [
        /* @__PURE__ */ jsx("span", { children: formatFileSize(file.size) }),
        isUploading && /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("span", { children: "-" }),
          /* @__PURE__ */ jsx("span", { className: "fi-text-primary", children: progress < 100 ? `Subiendo... ${progress}%` : "Completado" })
        ] }),
        isAwaitingUser && /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("span", { children: "-" }),
          /* @__PURE__ */ jsx("span", { className: "fi-text-primary", children: "Elige c\xF3mo usarlo" })
        ] }),
        isProcessing && /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("span", { children: "-" }),
          /* @__PURE__ */ jsx("span", { className: "fi-text-primary", children: "Procesando..." })
        ] }),
        isCompleted && /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("span", { children: "-" }),
          /* @__PURE__ */ jsx("span", { className: "chat-file-status-indexed", children: "Indexado" })
        ] }),
        isError && error && /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("span", { children: "-" }),
          /* @__PURE__ */ jsx("span", { className: "fi-text-error truncate", title: error, children: error })
        ] })
      ] }),
      isUploading && /* @__PURE__ */ jsx("div", { className: "mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden", children: /* @__PURE__ */ jsx(
        "div",
        {
          className: "fi-progress-bar duration-300",
          style: { width: `${progress}%` }
        }
      ) })
    ] }),
    !isCompleted && !isProcessing && /* @__PURE__ */ jsx(
      "button",
      {
        type: "button",
        onClick: onCancel,
        className: "fi-btn-ghost fi-btn-sm fi-hover-bg",
        "aria-label": "Cancelar",
        title: "Cancelar",
        children: /* @__PURE__ */ jsx(X, { className: "h-4 w-4" })
      }
    )
  ] });
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

// src/shell/useEdgeSwipe.ts
import { useEffect, useRef, useState } from "react";
var clamp01 = (n) => n < 0 ? 0 : n > 1 ? 1 : n;
function useEdgeSwipe({
  enabled,
  isOpen,
  containerRef,
  panelRef,
  onOpen,
  onClose,
  edgeSize = 24,
  fallbackWidth = 280,
  distanceRatio = 0.4,
  velocity = 0.35,
  axisSlop = 8
}) {
  const [progress, setProgress] = useState(null);
  const gestureRef = useRef(null);
  useEffect(() => {
    if (!enabled) {
      gestureRef.current = null;
      setProgress(null);
      return;
    }
    const node = containerRef.current;
    if (!node) return;
    const measure = () => {
      const measured = panelRef.current?.getBoundingClientRect().width ?? 0;
      return measured > 0 ? measured : fallbackWidth;
    };
    const release = () => {
      gestureRef.current = null;
      setProgress(null);
    };
    const handleStart = (event) => {
      if (gestureRef.current || event.touches.length !== 1) return;
      const touch = event.touches[0];
      if (!isOpen && touch.clientX > edgeSize) return;
      gestureRef.current = {
        id: touch.identifier,
        startX: touch.clientX,
        startY: touch.clientY,
        startTime: Date.now(),
        width: measure(),
        opening: !isOpen,
        axis: "undecided"
      };
    };
    const handleMove = (event) => {
      const gesture = gestureRef.current;
      if (!gesture) return;
      const touch = Array.from(event.touches).find((t) => t.identifier === gesture.id);
      if (!touch) return;
      const dx = touch.clientX - gesture.startX;
      const dy = touch.clientY - gesture.startY;
      if (gesture.axis === "undecided") {
        if (Math.abs(dx) < axisSlop && Math.abs(dy) < axisSlop) return;
        if (Math.abs(dx) <= Math.abs(dy)) {
          release();
          return;
        }
        gesture.axis = "horizontal";
      }
      if (event.cancelable) event.preventDefault();
      setProgress(clamp01(gesture.opening ? dx / gesture.width : 1 + dx / gesture.width));
    };
    const handleEnd = (event) => {
      const gesture = gestureRef.current;
      if (!gesture) return;
      const touch = Array.from(event.changedTouches).find((t) => t.identifier === gesture.id);
      release();
      if (!touch || gesture.axis !== "horizontal") return;
      const dx = touch.clientX - gesture.startX;
      const elapsed = Math.max(1, Date.now() - gesture.startTime);
      const speed = dx / elapsed;
      const travelled = gesture.opening ? dx : -dx;
      const flicked = gesture.opening ? speed > velocity : -speed > velocity;
      if (travelled > gesture.width * distanceRatio || flicked) {
        if (gesture.opening) onOpen();
        else onClose();
      }
    };
    node.addEventListener("touchstart", handleStart, { passive: true });
    node.addEventListener("touchmove", handleMove, { passive: false });
    node.addEventListener("touchend", handleEnd, { passive: true });
    node.addEventListener("touchcancel", release, { passive: true });
    return () => {
      node.removeEventListener("touchstart", handleStart);
      node.removeEventListener("touchmove", handleMove);
      node.removeEventListener("touchend", handleEnd);
      node.removeEventListener("touchcancel", release);
      gestureRef.current = null;
    };
  }, [
    enabled,
    isOpen,
    containerRef,
    panelRef,
    onOpen,
    onClose,
    edgeSize,
    fallbackWidth,
    distanceRatio,
    velocity,
    axisSlop
  ]);
  return progress;
}

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
export {
  ChatFilePreview,
  FI_TOUCH_TARGET_CLASS,
  clearMediaQueryCache,
  ensureTouchTargetStyle,
  useBreakpoints,
  useEdgeSwipe,
  useMediaQuery,
  useTouchTargetStyle,
  withTouchTarget
};
//# sourceMappingURL=index.js.map