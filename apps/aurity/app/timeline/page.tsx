'use client';

/**
 * Unified Timeline Page — Memoria Longitudinal Unificada
 *
 * FI-PHIL-DOC-014: "No existen sesiones. Solo una conversación infinita"
 *
 * Composition shell: hooks own state, components own rendering.
 */

import React, { useState, useCallback } from 'react';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { timelineHeader } from '@/config/page-headers';
import { useLongitudinalMemory } from '@/hooks/useLongitudinalMemory';
import { TimelineFilters } from '@/components/timeline/TimelineFilters';
import { TimelineSearch } from '@/components/timeline/TimelineSearch';

import type { ViewType, SchedulerTimeRange } from './types';
import { useInfiniteScroll } from './hooks/useInfiniteScroll';
import { useTimelineEvents } from './hooks/useTimelineEvents';
import { useTimelineMetrics } from './hooks/useTimelineMetrics';
import { TimelineStatsGrid } from './components/TimelineStatsGrid';
import { TimelineHeaderActions } from './components/TimelineHeaderActions';
import { TimelineSchedulerSection } from './components/TimelineSchedulerSection';
import { TimelineListSection } from './components/TimelineListSection';
import {
  TimelineError,
  TimelineEmpty,
  TimelineLoadingMore,
  TimelineEndIndicator,
  TimelinePageLoading,
  TimelinePhilosophyNote,
} from './components/TimelineFeedback';

export default function TimelinePage() {
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
    loadMore,
    refresh,
    searchQuery,
    setSearchQuery,
    isSearching,
  } = useLongitudinalMemory();

  // View mode
  const [viewType, setViewType] = useState<ViewType>('both');
  const [schedulerExpanded, setSchedulerExpanded] = useState(true);

  // Scheduler time-range filter
  const [schedulerTimeRange, setSchedulerTimeRange] =
    useState<SchedulerTimeRange | null>(null);

  const handleTimeRangeChange = useCallback(
    (startDate: Date, endDate: Date) =>
      setSchedulerTimeRange({ startDate, endDate }),
    [],
  );

  // Derived data
  const timelineEvents = useTimelineEvents(events, schedulerTimeRange);
  const metrics = useTimelineMetrics(events, stats, total, chatCount, audioCount);

  // Infinite scroll
  const sentinelRef = useInfiniteScroll({
    hasMore,
    isLoading,
    isLoadingMore,
    loadMore: () => void loadMore(),
  });

  // Full-page loading state
  if (isLoading && events.length === 0) {
    return <TimelinePageLoading />;
  }

  // Header
  const headerConfig = timelineHeader({
    totalEvents: metrics.totalEvents,
    p95Latency: metrics.p95Latency,
    sessionId: 'unified',
    successRate: metrics.successRate,
    totalDuration: metrics.totalDuration,
  });

  const headerActions = (
    <TimelineHeaderActions
      viewType={viewType}
      onViewTypeChange={setViewType}
      isLoading={isLoading}
      onRefresh={refresh}
    />
  );

  return (
    <AppTemplate
      headerConfig={{ ...headerConfig, actions: headerActions }}
      showWatermark
      showGeometricBg
    >
      <div className="tl-content">
        <div className="fi-stack-xl">
          <TimelineStatsGrid metrics={metrics} />

          <TimelineSearch
            onSearch={setSearchQuery}
            isSearching={isSearching}
            className="tl-search-full"
          />

          <TimelineFilters
            eventType={filters.eventType}
            totalCount={metrics.totalEvents}
            chatCount={metrics.chatCount}
            audioCount={metrics.audioCount}
            onEventTypeChange={setEventType}
          />

          {(viewType === 'scheduler' || viewType === 'both') && (
            <TimelineSchedulerSection
              events={events}
              isLoading={isLoading}
              viewType={viewType}
              expanded={schedulerExpanded}
              onToggleExpanded={() => setSchedulerExpanded((prev) => !prev)}
              onTimeRangeChange={handleTimeRangeChange}
            />
          )}

          {error && <TimelineError message={error} onRetry={refresh} />}

          {!isLoading && !error && timelineEvents.length === 0 && (
            <TimelineEmpty />
          )}

          {(viewType === 'list' || viewType === 'both') && (
            <TimelineListSection
              events={timelineEvents}
              viewType={viewType}
              searchQuery={searchQuery}
              isLoadingMore={isLoadingMore}
              hasMore={hasMore}
              onLoadMore={loadMore}
            />
          )}

          {/* Infinite scroll sentinel */}
          <div ref={sentinelRef} aria-hidden="true" className="tl-sentinel" />

          {isLoadingMore && <TimelineLoadingMore />}

          {!hasMore && timelineEvents.length > 0 && !isLoadingMore && (
            <TimelineEndIndicator total={total} />
          )}

          <TimelinePhilosophyNote />
        </div>
      </div>
    </AppTemplate>
  );
}
