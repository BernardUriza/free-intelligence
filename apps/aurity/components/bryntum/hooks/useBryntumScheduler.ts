/**
 * useBryntumScheduler v2 - Core Scheduler Lifecycle (StrictMode/SSR-safe)
 *
 * Upgrades: stronger typing, clear naming, batching helpers, listener diffing,
 * microtask timeSpan updates, resize/visibility awareness, and a stable API
 * with backward-compatible aliases.
 *
 * Card: FI-BRYNTUM-UNIFY-001
 * Version: v2 (2025-12-12)
 */

import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { loadBryntumOnce, getBryntumModule } from '../utils/bryntum-loader';

// ------------------------------------
// Minimal runtime shape (SchedulerLike)
// ------------------------------------
interface SchedulerLike {
  startDate?: Date;
  endDate?: Date;
  destroy?: () => void;
  refresh?: () => void;
  updateSize?: () => void;
  setTimeSpan: (start: Date, end: Date) => void;
  suspendRefresh: () => void;
  resumeRefresh: (trigger?: boolean) => void;
  beginBatch?: () => void;
  endBatch?: () => void;
  timeAxis?: { setTimeSpan: (s: Date, e: Date) => void };
  resourceStore?: {
    data: unknown[];
    replaceData?: (rows: unknown[]) => void;
    loadData?: (rows: unknown[]) => void;
  };
  eventStore?: {
    data: unknown[];
    replaceData?: (rows: unknown[]) => void;
    loadData?: (rows: unknown[]) => void;
  };
  on?: (name: string, handler: (...a: any[]) => void) => void;
  off?: (name: string, handler: (...a: any[]) => void) => void;
}

// ------------------------------------
// Types
// ------------------------------------
export interface TimeSpan { startDate: Date; endDate: Date }

interface UseSchedulerArgs {
  buildConfig: () => any;
  timeSpan?: TimeSpan;
  listeners?: Record<string, (...args: any[]) => void>;
  loader?: { cssHref: string; umdPath: string; theme?: string; nonce?: string };
  onInit?: (scheduler: SchedulerLike) => void;
  onFailure?: (error: unknown) => void;
  pauseWhenHidden?: boolean;
}

interface UseSchedulerReturnV2 {
  containerRef: React.RefObject<HTMLDivElement>;
  instance: SchedulerLike | null;
  status: 'idle' | 'loading' | 'ready' | 'error';
  error: unknown | null;
  applyData: (
    data: { resources?: unknown[]; events?: unknown[] },
    opts?: { silent?: boolean; replace?: boolean }
  ) => Promise<void>;
  updateTimeSpan: (span: TimeSpan) => void;
  dispose: () => void;
  awaitReady: () => Promise<SchedulerLike>;
  // Backward-compatible aliases
  reloadData: (
    opts?: { silent?: boolean; replace?: boolean; resources?: unknown[]; events?: unknown[] }
  ) => Promise<void>;
  setTimeWindow: (w: TimeSpan) => void;
  destroy: () => void;
}

// ------------------------------------
// Batching helper
// ------------------------------------
const batch = (s: SchedulerLike, fn: () => void) => {
  if (s.beginBatch && s.endBatch) {
    s.beginBatch();
    try { fn(); } finally { s.endBatch(); }
  } else {
    s.suspendRefresh();
    try { fn(); } finally { s.resumeRefresh(true); }
  }
};

// ------------------------------------
// Hook v2 (keeps name for drop-in compatibility)
// ------------------------------------
export function useBryntumScheduler({
  buildConfig,
  timeSpan,
  listeners,
  loader,
  onInit,
  onFailure,
  pauseWhenHidden,
}: UseSchedulerArgs): UseSchedulerReturnV2 {
  const containerRef = useRef<HTMLDivElement>(null);
  const schedulerRef = useRef<SchedulerLike | null>(null);
  const didInitRef = useRef(false);
  const pendingSpanRef = useRef<TimeSpan | null>(null);
  const readyResolversRef = useRef<((s: SchedulerLike) => void)[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const prevListenersRef = useRef<Record<string, (...a:any[])=>void> | undefined>(undefined);

  const [status, setStatus] = useState<'idle'|'loading'|'ready'|'error'>('idle');
  const [error, setError] = useState<unknown | null>(null);

  const awaitReady = useCallback(() => new Promise<SchedulerLike>((resolve) => {
    if (schedulerRef.current) return resolve(schedulerRef.current);
    readyResolversRef.current.push(resolve);
  }), []);

  const defaultLoader = useMemo(() => ({
    cssHref: '/css/bryntum/schedulerpro.classic-dark.css',
    umdPath: '/js/bryntum/schedulerpro.wc.module.js',
    // Align CSS href to match JS bundle version to avoid mismatch warnings
    strictVersionMatch: true,
    // Load overrides to neutralize Font Awesome references (avoid 404s)
    extraCss: ['/css/bryntum/overrides.css'],
  }), []);

  // Init (StrictMode/SSR-safe)
  useEffect(() => {
    // CRITICAL: Prevent double-init even in StrictMode
    if (didInitRef.current || schedulerRef.current) return;
    if (typeof window === 'undefined') return; // SSR guard
    if (!containerRef.current) return;

    // CRITICAL: Mark as initialized IMMEDIATELY to prevent double-init in StrictMode
    didInitRef.current = true;

    // CRITICAL: Clear any existing Bryntum instances in container
    const container = containerRef.current;
    if (container.firstChild) {
      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
    }

    setStatus('loading');
    abortRef.current = new AbortController();

    (async () => {
      try {
        const cfg = { ...(loader ?? defaultLoader) };
        await loadBryntumOnce(cfg);
        if (abortRef.current?.signal.aborted) return;

        const SchedulerProCtor: any = getBryntumModule();
        if (!SchedulerProCtor) throw new Error('SchedulerPro module not available');

        const config = buildConfig();
        const instance: SchedulerLike = new SchedulerProCtor({
          ...config,
          appendTo: container,
        });

        // Initial listeners
        if (listeners && instance.on) {
          Object.entries(listeners).forEach(([name, handler]) => instance.on!(name, handler));
          prevListenersRef.current = listeners;
        }

        schedulerRef.current = instance;
        setStatus('ready');
        readyResolversRef.current.splice(0).forEach(r => r(instance));
        onInit?.(instance);
      } catch (e) {
        setStatus('error');
        setError(e);
        onFailure?.(e);
      }
    })();

    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
      if (schedulerRef.current) {
        try {
          schedulerRef.current.destroy?.();
        } catch { /* noop */ }
        schedulerRef.current = null;
      }
      // Clear DOM to prevent orphaned elements
      if (containerRef.current) {
        while (containerRef.current.firstChild) {
          containerRef.current.removeChild(containerRef.current.firstChild);
        }
      }
      setStatus('idle');
      setError(null);
      // DO NOT reset didInitRef - keep it true to prevent StrictMode double-init
      // didInitRef.current = false;
    };
  // buildConfig/listeners should be stable via useMemo/useCallback
  }, [buildConfig, listeners, loader, onInit, onFailure]);

  // Dynamic listeners diffing
  useEffect(() => {
    const s = schedulerRef.current;
    if (!s || !s.on || !s.off) return;
    const prev = prevListenersRef.current || {};
    const next = listeners || {};

    Object.entries(prev).forEach(([name, handler]) => {
      if (!next[name] || next[name] !== handler) s.off!(name, handler);
    });
    Object.entries(next).forEach(([name, handler]) => {
      if (!prev[name] || prev[name] !== handler) s.on!(name, handler);
    });
    prevListenersRef.current = next;
  }, [listeners]);

  // TimeSpan updates via microtask queue
  useEffect(() => {
    const s = schedulerRef.current;
    if (!s || status !== 'ready' || !timeSpan) return;

    const currStart = s.startDate?.getTime();
    const currEnd = s.endDate?.getTime();
    if (currStart === timeSpan.startDate.getTime() && currEnd === timeSpan.endDate.getTime()) return;

    pendingSpanRef.current = timeSpan;
    queueMicrotask(() => {
      const span = pendingSpanRef.current; if (!span || !schedulerRef.current) return;
      pendingSpanRef.current = null;
      const apply = () => s.timeAxis?.setTimeSpan ? s.timeAxis!.setTimeSpan(span.startDate, span.endDate)
                                                  : s.setTimeSpan(span.startDate, span.endDate);
      batch(s, apply);
    });
  }, [timeSpan, status]);

  // Resize-aware refresh/updateSize
  useEffect(() => {
    const el = containerRef.current; const s = schedulerRef.current;
    if (!el || !s) return;
    const ro = new ResizeObserver(() => { (s.updateSize ?? s.refresh)?.call(s); });
    ro.observe(el);
    return () => ro.disconnect();
  }, [status]);

  // Visibility-aware (optional perf)
  useEffect(() => {
    if (!pauseWhenHidden) return;
    const el = containerRef.current; const s = schedulerRef.current; if (!el || !s) return;
    const io = new IntersectionObserver((entries) => {
      const visible = entries.some(e => e.isIntersecting);
      if (visible) (s.updateSize ?? s.refresh)?.call(s);
    }, { threshold: 0 });
    io.observe(el);
    return () => io.disconnect();
  }, [pauseWhenHidden, status]);

  // Public API
  const applyData = useCallback(async (
    data: { resources?: unknown[]; events?: unknown[] },
    opts?: { silent?: boolean; replace?: boolean }
  ) => {
    const s = schedulerRef.current; if (!s) return;
    const silent = opts?.silent ?? true;
    const replace = opts?.replace ?? true;
    const run = () => {
      if (data.resources && s.resourceStore) {
        if (replace && (s.resourceStore.replaceData || s.resourceStore.loadData)) {
          (s.resourceStore.replaceData ?? s.resourceStore.loadData)!(data.resources);
        } else {
          s.resourceStore.data = data.resources;
        }
      }
      if (data.events && s.eventStore) {
        if (replace && (s.eventStore.replaceData || s.eventStore.loadData)) {
          (s.eventStore.replaceData ?? s.eventStore.loadData)!(data.events);
        } else {
          s.eventStore.data = data.events;
        }
      }
    };
    silent ? batch(s, run) : run();
  }, []);

  const updateTimeSpan = useCallback((span: TimeSpan) => {
    const s = schedulerRef.current; if (!s) return;
    const apply = () => s.timeAxis?.setTimeSpan ? s.timeAxis!.setTimeSpan(span.startDate, span.endDate)
                                                : s.setTimeSpan(span.startDate, span.endDate);
    batch(s, apply);
  }, []);

  const dispose = useCallback(() => {
    if (!schedulerRef.current) return;
    try { schedulerRef.current.destroy?.(); } finally { schedulerRef.current = null; }
  }, []);

  // Aliases for backward compatibility
  const reloadData = useCallback(async (opts?: { silent?: boolean; replace?: boolean; resources?: unknown[]; events?: unknown[] }) => {
    const { resources, events, ...rest } = opts || {};
    await applyData({ resources, events }, rest);
  }, [applyData]);
  const setTimeWindow = useCallback((w: TimeSpan) => updateTimeSpan(w), [updateTimeSpan]);
  const destroy = useCallback(() => dispose(), [dispose]);

  return {
    containerRef,
    instance: schedulerRef.current,
    status,
    error,
    applyData,
    updateTimeSpan,
    dispose,
    awaitReady,
    // Compat
    reloadData,
    setTimeWindow,
    destroy,
  };
}
