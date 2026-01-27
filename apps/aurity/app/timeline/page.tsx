'use client';

/**
 * Unified Timeline Page - Memoria Longitudinal Unificada
 *
 * FI-PHIL-DOC-014: "No existen sesiones. Solo una conversación infinita"
 *
 * Features:
 * - Bryntum SchedulerPro visualization with Navigate drawer
 * - Pagination via backend /timeline/memory endpoint
 * - Event type filtering (all/chat/audio)
 * - Time range filtering (presets)
 * - Infinite scroll with IntersectionObserver
 * - Dual view: Visual scheduler + detailed list
 *
 * Updated: 2025-11-22 - Added TimelineScheduler with Bryntum SchedulerPro
 */

import React, { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { Button } from '@/components/ui/button';
import { timelineHeader } from '@/config/page-headers';
import { useLongitudinalMemory } from '@/hooks/useLongitudinalMemory';
import { TimelineFilters } from '@/components/timeline/TimelineFilters';
import { TimelineSearch } from '@/components/timeline/TimelineSearch';
import { VirtualizedTimeline } from '@/components/timeline/VirtualizedTimeline';
import type { TimelineEvent } from '@/components/audit/EventTimeline';
import {
  MessageCircle,
  Mic,
  Loader2,
  RefreshCw,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  BarChart3,
  List,
} from 'lucide-react';

// Lazy load TimelineScheduler (Bryntum ~800KB)
// Only loads when scheduler view is activated
const TimelineScheduler = dynamic(
  () => import('@/components/timeline/TimelineScheduler'),
  {
    ssr: false, // Bryntum requires window object
    loading: () => (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
      </div>
    ),
  }
);

// ============================================================================
// Main Component
// ============================================================================

type ViewType = 'scheduler' | 'list' | 'both';

export default function TimelinePage() {
  // Use longitudinal memory hook (replaces all legacy state management)
  const {
    events,
    stats,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    total,
    chatCount,
    audioCount,
    filters,
    setEventType,
    setTimeRangePreset,
    loadMore,
    refresh,
    searchQuery,
    setSearchQuery,
    isSearching,
  } = useLongitudinalMemory();

  // View mode: scheduler (Bryntum), list (EventTimeline), or both
  const [viewType, setViewType] = useState<ViewType>('both');
  const [schedulerExpanded, setSchedulerExpanded] = useState(true);

  // Track scheduler's visible time range for filtering list view
  const [schedulerTimeRange, setSchedulerTimeRange] = useState<{
    startDate: Date;
    endDate: Date;
  } | null>(null);

  // Handler for scheduler time range changes
  const handleTimeRangeChange = useCallback((startDate: Date, endDate: Date) => {
    setSchedulerTimeRange({ startDate, endDate });
  }, []);

  // Sentinel ref for infinite scroll
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // ============================================================================
  // Infinite Scroll with IntersectionObserver
  // ============================================================================

  useEffect(() => {
    // SSR-safe: check for IntersectionObserver
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      return;
    }

    const el = sentinelRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && hasMore && !isLoading && !isLoadingMore) {
          void loadMore();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    observer.observe(el);

    return () => {
      observer.disconnect();
    };
  }, [hasMore, isLoading, isLoadingMore, loadMore]);

  // ============================================================================
  // Transform MemoryEvent to TimelineEvent for EventTimeline component
  // ============================================================================

  // Filter events by scheduler's visible time range (if available)
  const filteredEventsByTimeRange = useMemo(() => {
    if (!schedulerTimeRange) return events;

    const startTimestamp = schedulerTimeRange.startDate.getTime() / 1000;
    const endTimestamp = schedulerTimeRange.endDate.getTime() / 1000;

    return events.filter(
      (e) => e.timestamp >= startTimestamp && e.timestamp <= endTimestamp
    );
  }, [events, schedulerTimeRange]);

  const timelineEvents = useMemo<TimelineEvent[]>(() => {
    return filteredEventsByTimeRange.map((e, idx) => ({
      id: e.id,
      timestamp: e.timestamp, // Unix timestamp (seconds)
      // Normalize: event_type → type for EventTimeline compatibility
      type: (e as any).type ?? e.event_type,
      content: e.content,
      metadata: {
        event_number: idx + 1,
        session_id: e.session_id,
        persona: e.persona,
        chunk_number: e.chunk_number,
        duration: e.duration,
        confidence: e.confidence,
        language: e.language,
        stt_provider: e.stt_provider,
        source: e.source,
      },
    }));
  }, [filteredEventsByTimeRange]);

  // ============================================================================
  // Calculate metrics for header
  // ============================================================================

  const metrics = useMemo(() => {
    const audioEvents = events.filter(e => e.source === 'audio');
    const totalDuration = audioEvents.reduce((sum, e) => sum + (e.duration || 0), 0);

    // Calculate p95 latency from stats or estimate
    const p95Latency = stats?.total_events ?? 0 > 0 ? 850 : 0; // Placeholder

    return {
      totalEvents: total,
      chatCount,
      audioCount,
      totalDuration,
      p95Latency,
      successRate: 100, // Will be calculated from actual data
    };
  }, [events, stats, total, chatCount, audioCount]);

  // ============================================================================
  // Loading State
  // ============================================================================

  if (isLoading && events.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950">
        <div className="text-center">
          <Loader2 className="animate-spin h-12 w-12 text-emerald-500 mx-auto mb-4" />
          <p className="text-slate-400 text-[15px] leading-6">
            Cargando memoria longitudinal...
          </p>
        </div>
      </div>
    );
  }

  // ============================================================================
  // Header Configuration
  // ============================================================================

  const headerConfig = timelineHeader({
    totalEvents: metrics.totalEvents,
    p95Latency: metrics.p95Latency,
    sessionId: 'unified',
    successRate: metrics.successRate,
    totalDuration: metrics.totalDuration,
  });

  const headerActions = (
      <div className="flex items-center gap-2">
      {/* View Mode Toggle */}
      <div className="flex items-center bg-slate-800 rounded-lg p-0.5">
        <Button
          onClick={() => setViewType('scheduler')}
          className={viewType === 'scheduler' ? 'fi-view-toggle-active' : 'fi-view-toggle'}
          variant="ghost"
          size="sm"
          title="Vista Scheduler"
        >
          <BarChart3 className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Visual</span>
        </Button>
        <Button
          onClick={() => setViewType('list')}
          className={viewType === 'list' ? 'fi-view-toggle-active' : 'fi-view-toggle'}
          variant="ghost"
          size="sm"
          title="Vista Lista"
        >
          <List className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Lista</span>
        </Button>
        <Button
          onClick={() => setViewType('both')}
          className={viewType === 'both' ? 'fi-view-toggle-active' : 'fi-view-toggle'}
          variant="ghost"
          size="sm"
          title="Ambas vistas"
        >
          <span className="hidden sm:inline">Ambas</span>
          <span className="sm:hidden">2</span>
        </Button>
      </div>

      {/* Refresh Button */}
      <Button
        onClick={() => refresh()}
        disabled={isLoading}
        className="fi-btn-refresh"
        variant="ghost"
        size="sm"
        title="Refresh"
      >
        <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        Refresh
      </Button>
    </div>
  );

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <AppTemplate headerConfig={{ ...headerConfig, actions: headerActions }} showWatermark={true} showGeometricBg={true}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="fi-stack-xl">

          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="fi-stat-card">
              <div className="fi-stat-value">{metrics.totalEvents}</div>
              <div className="fi-stat-label">Total Eventos</div>
            </div>
            <div className="fi-stat-card-sky">
              <div className="flex items-center gap-2">
                <MessageCircle className="h-4 w-4 text-sky-400" />
                <div className="text-2xl font-bold text-sky-400">{metrics.chatCount}</div>
              </div>
              <div className="fi-text-xs">Chat Messages</div>
            </div>
            <div className="fi-stat-card-emerald">
              <div className="flex items-center gap-2">
                <Mic className="h-4 w-4 fi-text-success" />
                <div className="text-2xl font-bold fi-text-success">{metrics.audioCount}</div>
              </div>
              <div className="fi-text-xs">Transcripciones</div>
            </div>
            <div className="fi-stat-card">
              <div className="fi-stat-value">
                {metrics.totalDuration.toFixed(0)}s
              </div>
              <div className="fi-stat-label">Audio Total</div>
            </div>
          </div>

          {/* Search Bar */}
          <TimelineSearch
            onSearch={setSearchQuery}
            isSearching={isSearching}
            className="w-full"
          />

          {/* TimelineFilters Component - Event type only (time filtering via scheduler) */}
          <TimelineFilters
            eventType={filters.eventType}
            totalCount={metrics.totalEvents}
            chatCount={metrics.chatCount}
            audioCount={metrics.audioCount}
            onEventTypeChange={setEventType}
          />

          {/* Bryntum SchedulerPro Visualization */}
          {(viewType === 'scheduler' || viewType === 'both') && (
            <div className="rounded-2xl overflow-hidden ring-1 ring-white/5 shadow-sm bg-slate-900">
              {viewType === 'both' && (
                <Button
                  onClick={() => setSchedulerExpanded(!schedulerExpanded)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-slate-800/50 fi-border-bottom hover:bg-slate-800 transition-colors"
                  variant="ghost"
                  size="sm"
                  title={schedulerExpanded ? 'Contraer Scheduler' : 'Expandir Scheduler'}
                >
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-emerald-400" />
                    <span className="fi-title-sm-medium">
                      Visualización Timeline
                    </span>
                    <span className="fi-text-xs">
                      (Bryntum SchedulerPro)
                    </span>
                  </div>
                  {schedulerExpanded ? (
                    <ChevronUp className="h-4 w-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-slate-400" />
                  )}
                </Button>
              )}
              {(viewType === 'scheduler' || schedulerExpanded) && (
                <TimelineScheduler
                  events={events}
                  isLoading={isLoading}
                  onTimeRangeChange={handleTimeRangeChange}
                  className="h-[400px]"
                />
              )}
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="flex items-center gap-3 p-4 bg-red-950/30 border border-red-700/30 rounded-xl">
              <AlertCircle className="h-5 w-5 fi-text-error flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm text-red-300">{error}</p>
              </div>
              <Button
                onClick={() => refresh()}
                className="fi-btn-danger-sm"
                variant="danger"
                size="sm"
                title="Reintentar"
              >
                Reintentar
              </Button>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && timelineEvents.length === 0 && (
            <div className="fi-empty-state">
              <p className="text-slate-400 text-sm">
                Sin eventos en el período seleccionado.
              </p>
              <p className="text-slate-500 text-xs mt-2">
                &quot;No existen sesiones. Solo una conversación infinita&quot;
              </p>
            </div>
          )}

          {/* Unified Timeline - All Events (List View with Virtualization) */}
          {(viewType === 'list' || viewType === 'both') && timelineEvents.length > 0 && (
            <div className="rounded-2xl overflow-hidden ring-1 ring-white/5 shadow-sm">
              {viewType === 'both' && (
                <div className="flex items-center gap-2 px-4 py-3 bg-slate-800/50 fi-border-bottom">
                  <List className="h-4 w-4 text-sky-400" />
                  <span className="fi-title-sm-medium">
                    Lista de Eventos
                  </span>
                  <span className="fi-text-xs">
                    ({timelineEvents.length} eventos)
                  </span>
                  {searchQuery && (
                    <span className="ml-2 text-xs fi-text-success">
                      · Búsqueda: &quot;{searchQuery}&quot;
                    </span>
                  )}
                </div>
              )}
              
              {/* Use VirtualizedTimeline for performance */}
              <VirtualizedTimeline
                events={timelineEvents}
                isLoading={isLoadingMore}
                onLoadMore={loadMore}
                hasMore={hasMore}
                className=""
              />
            </div>
          )}

          {/* Infinite Scroll Sentinel */}
          <div
            ref={sentinelRef}
            aria-hidden="true"
            className="h-1"
          />

          {/* Loading More Indicator */}
          {isLoadingMore && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="animate-spin h-6 w-6 text-emerald-500 mr-2" />
              <span className="fi-subtitle">Cargando más eventos...</span>
            </div>
          )}

          {/* End of Timeline Indicator */}
          {!hasMore && timelineEvents.length > 0 && !isLoadingMore && (
            <div className="text-center py-8 border-t border-slate-800">
              <p className="fi-text-xs-muted">
                Fin de la memoria longitudinal · {total} eventos totales
              </p>
            </div>
          )}

          {/* Philosophy Note */}
          <div className="p-4 bg-slate-800/30 border border-slate-700 rounded-xl">
            <p className="fi-text-xs-muted italic text-center">
              &quot;No existen sesiones. Solo una conversación infinita&quot; — FI-PHIL-DOC-014
            </p>
          </div>

        </div>
      </div>
    </AppTemplate>
  );
}
