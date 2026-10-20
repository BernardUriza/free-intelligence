'use client';

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

export {
  useMediaQuery,
  useBreakpoints,
  clearMediaQueryCache,
  useEdgeSwipe
};
//# sourceMappingURL=chunk-TZYRBKX6.js.map