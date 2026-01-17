/**
 * SchedulerCore Component - Unified Bryntum Wrapper
 * 
 * Thin, predictable wrapper around useBryntumScheduler hook.
 * Works for both Timeline and Appointments schedulers.
 * 
 * Features:
 * - Client-only rendering (no SSR)
 * - Automatic resize handling
 * - Consistent lifecycle across both scheduler types
 * - Zero duplication of Bryntum loading logic
 * 
 * Card: FI-BRYNTUM-UNIFY-001
 * Created: 2025-12-11
 */

'use client';

import React, { useEffect, useRef } from 'react';
import { useBryntumScheduler } from '../hooks/useBryntumScheduler';

// ============================================================================
// Types
// ============================================================================

interface SchedulerCoreProps {
  /**
   * Pure function that builds Bryntum config
   * Called once on init; should be memoized or stable
   */
  getConfig: () => any;
  
  /**
   * Optional time window for calendar views
   * Triggers batched setTimeSpan updates
   */
  timeWindow?: {
    startDate: Date;
    endDate: Date;
  };
  
  /**
   * Called after scheduler is ready
   */
  onReady?: (scheduler: any) => void;
  
  /**
   * Called on errors
   */
  onError?: (error: unknown) => void;
  
  /**
   * Additional CSS classes for container
   */
  className?: string;
  
  /**
   * Inline styles for container
   */
  style?: React.CSSProperties;
  
  /**
   * Loading state (shows overlay)
   */
  isLoading?: boolean;
  
  /**
   * Empty state message
   */
  emptyMessage?: string;
  
  /**
   * Show empty state when no data
   */
  showEmpty?: boolean;
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * SchedulerCore - Unified Bryntum Container
 * 
 * Handles:
 * - Bryntum initialization via hook
 * - Resize observer for responsive grids
 * - Loading + empty states
 * - Client-only rendering
 * 
 * @example Timeline
 * ```tsx
 * <SchedulerCore
 *   getConfig={() => buildTimelineSchedulerConfig({
 *     viewMode: 'day',
 *     currentDate: new Date(),
 *     events: myEvents,
 *   })}
 *   className="h-full"
 * />
 * ```
 * 
 * @example Appointments
 * ```tsx
 * <SchedulerCore
 *   getConfig={() => buildAppointmentSchedulerConfig({
 *     viewMode: 'day',
 *     currentDate: new Date(),
 *     doctors: myDoctors,
 *     appointments: myAppointments,
 *     onEventDrop: handleDrop,
 *   })}
 *   timeWindow={{ startDate, endDate }}
 * />
 * ```
 */
export function SchedulerCore({
  getConfig,
  timeWindow,
  onReady,
  onError,
  className = '',
  style,
  isLoading = false,
  emptyMessage,
  showEmpty = false,
}: SchedulerCoreProps) {
  // Scheduler hook (handles all lifecycle)
  const { containerRef, instance, status, error } = useBryntumScheduler({
    buildConfig: getConfig,
    timeSpan: timeWindow,
    onInit: onReady,
    onFailure: onError,
  });

  const isReady = status === 'ready';
  const isError = status === 'error';

  // Resize observer (responsive grids)
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  useEffect(() => {
    if (!containerRef.current || !instance || !isReady) {
      return;
    }

    // Disconnect existing observer before creating new one (prevents duplicates)
    if (resizeObserverRef.current) {
      resizeObserverRef.current.disconnect();
      resizeObserverRef.current = null;
    }

    // Create resize observer
    resizeObserverRef.current = new ResizeObserver(() => {
      if (instance && typeof (instance as any).refreshColumns === 'function') {
        (instance as any).refreshColumns();
      }
    });

    // Observe container
    resizeObserverRef.current.observe(containerRef.current);

    // Cleanup
    return () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }
    };
  }, [instance, isReady]);

  // Apply data updates when getConfig/timeWindow changes and scheduler is ready
  useEffect(() => {
    if (!isReady || !instance) return;
    try {
      const cfg = getConfig();
      const resources = (cfg as any)?.resources;
      const events = (cfg as any)?.events;
      // Bryntum 5.x uses resourceTimeRangesData for initial data
      const resourceTimeRanges = (cfg as any)?.resourceTimeRangesData;
      const span = {
        startDate: (cfg as any)?.startDate ?? timeWindow?.startDate,
        endDate: (cfg as any)?.endDate ?? timeWindow?.endDate
      };
      // Update time window first, then data
      if (span.startDate && span.endDate && typeof (instance as any)?.setTimeSpan === 'function') {
        (instance as any).setTimeSpan(span.startDate, span.endDate);
      }
      if ((instance as any)?.eventStore && (events || resources || resourceTimeRanges)) {
        // Use hook's applyData if available on instance
        const s: any = instance;
        if (s.resourceStore && resources) {
          (s.resourceStore.replaceData ?? s.resourceStore.loadData)?.call(s.resourceStore, resources);
        }
        if (s.eventStore && events) {
          (s.eventStore.replaceData ?? s.eventStore.loadData)?.call(s.eventStore, events);
        }
        // Update resourceTimeRanges for non-working hours
        if (s.resourceTimeRangeStore && resourceTimeRanges) {
          (s.resourceTimeRangeStore.replaceData ?? s.resourceTimeRangeStore.loadData)?.call(
            s.resourceTimeRangeStore,
            resourceTimeRanges
          );
        }
        (s.refresh ?? s.updateSize)?.call(s);
      }
    } catch (e) {
      // Non-fatal: keep previous data
      console.warn('[SchedulerCore] Failed to apply updated data/config:', e);
    }
  }, [getConfig, timeWindow, isReady, instance]);

  // ============================================================================
  // WORKAROUND: Fix blocked time event positions (CSS/JS version mismatch)
  // Card: FI-BRYNTUM-CSS-001
  // ============================================================================
  // Bryntum CSS v6.0.0-alpha-1 + JS v5.6.6 calculates wrong Y positions for events.
  // This effect repositions blocked events to their correct resource rows.
  // Uses MutationObserver to catch Bryntum's virtual rendering DOM changes.
  useEffect(() => {
    if (!isReady || !instance) return;

    const s = instance as any;

    const fixBlockedEventPositions = () => {
      if (!s?.resourceStore?.allRecords) return;

      // Build resourceId -> row index map
      const resourceIndexMap: Record<string, number> = {};
      s.resourceStore.allRecords.forEach((resource: any, index: number) => {
        resourceIndexMap[resource.id] = index;
      });

      // Get row height from scheduler config
      const rowHeight = s.rowHeight || 200;

      // Find all blocked event wrappers and fix their positions
      const blockedWrappers = document.querySelectorAll('.b-sch-event-wrap[data-event-id^="blocked-"]');

      blockedWrappers.forEach((wrapper) => {
        const resourceId = wrapper.getAttribute('data-resource-id');
        if (!resourceId || resourceIndexMap[resourceId] === undefined) return;

        const rowIndex = resourceIndexMap[resourceId];
        const correctTop = rowIndex * rowHeight + 5; // 5px margin

        // Apply correct position via CSS custom property
        (wrapper as HTMLElement).style.setProperty('--blocked-row-top', `${correctTop}px`);
        (wrapper as HTMLElement).classList.add('blocked-position-fixed');
      });
    };

    // Run fix after initial render
    const timeoutId = setTimeout(fixBlockedEventPositions, 100);

    // MutationObserver to catch Bryntum's virtual rendering
    // Run fix on ANY DOM mutation - Bryntum recycles elements unpredictably
    const schedulerEl = containerRef.current;
    let observer: MutationObserver | null = null;
    let pendingFix = false;

    if (schedulerEl) {
      observer = new MutationObserver(() => {
        // Debounce: only schedule one fix per animation frame
        if (!pendingFix) {
          pendingFix = true;
          requestAnimationFrame(() => {
            fixBlockedEventPositions();
            pendingFix = false;
          });
        }
      });

      observer.observe(schedulerEl, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['style', 'class'], // Catch style/class changes too
      });
    }

    // Also keep Bryntum event listeners as backup
    const handleRender = () => {
      requestAnimationFrame(fixBlockedEventPositions);
    };

    s?.on?.('scroll', handleRender);
    s?.on?.('zoomChange', handleRender);
    s?.on?.('refresh', handleRender);

    return () => {
      clearTimeout(timeoutId);
      observer?.disconnect();
      s?.un?.('scroll', handleRender);
      s?.un?.('zoomChange', handleRender);
      s?.un?.('refresh', handleRender);
    };
  }, [isReady, instance, getConfig]);

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div
      className={`relative ${className}`}
      style={style}
    >
      {/* Scheduler Container */}
      <div
        ref={containerRef}
        data-bryntum-core
        className="absolute inset-0 w-full h-full"
      />

      {/* Loading Overlay */}
      {isLoading && (
        <div className="fi-overlay">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-500" />
        </div>
      )}

      {/* Empty State */}
      {showEmpty && !isLoading && isReady && (
        <div className="fi-overlay">
          <div className="text-center">
            <p className="text-slate-400 text-sm">
              {emptyMessage || 'No hay datos para mostrar'}
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {isError && (
        <div className="fi-overlay bg-red-900/20">
          <div className="text-center p-6 bg-slate-800 rounded-lg border border-red-500/30 max-w-md">
            <div className="text-red-400 text-4xl mb-3">⚠️</div>
            <h3 className="text-red-400 font-semibold mb-2">
              Error al cargar el calendario
            </h3>
            <p className="text-slate-400 text-sm mb-4">
              {error instanceof Error ? error.message : 'Error desconocido al inicializar el scheduler'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Reintentar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default SchedulerCore;
