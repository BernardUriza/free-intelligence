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
  const { containerRef, instance, status } = useBryntumScheduler({
    buildConfig: getConfig,
    timeSpan: timeWindow,
    onInit: onReady,
    onFailure: onError,
  });

  const isReady = status === 'ready';

  // Resize observer (responsive grids)
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  useEffect(() => {
    if (!containerRef.current || !instance || !isReady) {
      return;
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
      const span = {
        startDate: (cfg as any)?.startDate ?? timeWindow?.startDate,
        endDate: (cfg as any)?.endDate ?? timeWindow?.endDate
      };
      // Update time window first, then data
      if (span.startDate && span.endDate && typeof (instance as any)?.setTimeSpan === 'function') {
        (instance as any).setTimeSpan(span.startDate, span.endDate);
      }
      if ((instance as any)?.eventStore && (events || resources)) {
        // Use hook's applyData if available on instance
        const s: any = instance;
        if (s.resourceStore && resources) {
          (s.resourceStore.replaceData ?? s.resourceStore.loadData)?.call(s.resourceStore, resources);
        }
        if (s.eventStore && events) {
          (s.eventStore.replaceData ?? s.eventStore.loadData)?.call(s.eventStore, events);
        }
        (s.refresh ?? s.updateSize)?.call(s);
      }
    } catch (e) {
      // Non-fatal: keep previous data
      console.warn('[SchedulerCore] Failed to apply updated data/config:', e);
    }
  }, [getConfig, timeWindow, isReady, instance]);

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
    </div>
  );
}

export default SchedulerCore;
