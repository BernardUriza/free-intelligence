'use client';

/**
 * TimelineScheduler Component - UNIFIED CORE
 *
 * Professional Bryntum SchedulerPro integration for longitudinal memory visualization.
 * 
 * Architecture:
 * - Uses unified SchedulerCore + buildTimelineSchedulerConfig
 * - Single source of truth for Bryntum lifecycle
 * - No duplicate CSS/JS loads
 * - StrictMode-safe initialization
 * 
 * Card: FI-BRYNTUM-UNIFY-001
 * Refactored: 2025-12-11
 * 
 * @see components/bryntum/core/SchedulerCore.tsx for implementation
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';

// Bryntum unified modules
import {
  useSchedulerState,
  useSchedulerEvents,
  SchedulerCore,
  buildTimelineSchedulerConfig,
  VIEW_PRESETS,
  type UnifiedEvent,
} from '@/components/bryntum';

// UI Components
import { TimelineToolbar } from './TimelineToolbar';
import { NavigateDrawer } from './NavigateDrawer';
import { EventDetailModal } from './EventDetailModal';
import { KeyboardShortcutsBar } from './KeyboardShortcutsBar';

// ============================================================================
// Types
// ============================================================================

interface TimelineSchedulerProps {
  events: UnifiedEvent[];
  isLoading?: boolean;
  onEventClick?: (event: UnifiedEvent) => void;
  className?: string;
}

// ============================================================================
// Main Component
// ============================================================================

export function TimelineScheduler({
  events,
  isLoading = false,
  onEventClick,
  className = '',
}: TimelineSchedulerProps) {
  // UI state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<UnifiedEvent | null>(null);

  // Scheduler state (centralized hook)
  const schedulerState = useSchedulerState({
    events,
    initialViewMode: 'day',
    initialDate: new Date(),
  });

  // Build configuration from current state (memoized for stability)
  const getConfig = useCallback(() => {
    return buildTimelineSchedulerConfig({
      viewMode: schedulerState.viewMode,
      currentDate: schedulerState.currentDate,
      events: schedulerState.filteredEvents,
      onEventClick: (event) => {
        setSelectedEvent(event);
        onEventClick?.(event);
      },
    });
  }, [
    schedulerState.viewMode,
    schedulerState.currentDate,
    schedulerState.filteredEvents,
    onEventClick,
  ]);

  // Calculate time window for batched updates
  const timeWindow = useMemo(() => {
    const viewConfig = VIEW_PRESETS[schedulerState.viewMode];
    const { start, end } = viewConfig.getDateRange(schedulerState.currentDate);
    return { startDate: start, endDate: end };
  }, [schedulerState.viewMode, schedulerState.currentDate]);

  // Track scheduler instance for keyboard shortcuts
  const [schedulerInstance, setSchedulerInstance] = useState<any>(null);

  const handleReady = useCallback((instance: any) => {
    setSchedulerInstance(instance);
    schedulerState.setIsReady(true);
  }, [schedulerState]);

  const handleError = useCallback((error: unknown) => {
    console.error('[TimelineScheduler] Scheduler error:', error);
  }, []);

  // Keyboard shortcuts and event handling
  useSchedulerEvents({
    instance: schedulerInstance,
    onEventClick: (event) => {
      setSelectedEvent(event);
      onEventClick?.(event);
    },
    onNavigatePrev: () => schedulerState.navigateDate('prev'),
    onNavigateNext: () => schedulerState.navigateDate('next'),
    onZoomIn: () => schedulerState.handleZoom('in'),
    onZoomOut: () => schedulerState.handleZoom('out'),
    onGoToToday: schedulerState.goToToday,
    onEscape: () => {
      if (selectedEvent) {
        setSelectedEvent(null);
      } else if (drawerOpen) {
        setDrawerOpen(false);
      }
    },
  });

  // Update zoom level
  useEffect(() => {
    if (!schedulerInstance) return;

    const viewConfig = VIEW_PRESETS[schedulerState.viewMode];
    const baseTickWidth = (viewConfig.preset as { tickWidth?: number }).tickWidth || 60;
    schedulerInstance.tickSize = Math.round(baseTickWidth * schedulerState.zoomLevel);
  }, [schedulerInstance, schedulerState.zoomLevel, schedulerState.viewMode]);

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Toolbar */}
      <TimelineToolbar
        viewMode={schedulerState.viewMode}
        currentDate={schedulerState.currentDate}
        zoomLevel={schedulerState.zoomLevel}
        drawerOpen={drawerOpen}
        onToggleDrawer={() => setDrawerOpen(!drawerOpen)}
        onViewModeChange={schedulerState.setViewMode}
        onNavigateDate={schedulerState.navigateDate}
        onGoToToday={schedulerState.goToToday}
        onZoom={schedulerState.handleZoom}
        onJumpToLatest={events.length > 0 ? schedulerState.jumpToLatestEvent : undefined}
      />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Navigate Drawer */}
        <NavigateDrawer
          isOpen={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          sessions={schedulerState.sessions}
          selectedSession={schedulerState.selectedSession}
          onSessionSelect={schedulerState.setSelectedSession}
          searchQuery={schedulerState.searchQuery}
          onSearchChange={schedulerState.setSearchQuery}
          chatCount={schedulerState.chatCount}
          audioCount={schedulerState.audioCount}
        />

        {/* Scheduler Container - Unified Core */}
        <div className="flex-1 relative bg-slate-950">
          <SchedulerCore
            getConfig={getConfig}
            timeWindow={timeWindow}
            onReady={handleReady}
            onError={handleError}
            isLoading={isLoading}
            showEmpty={events.length === 0}
            emptyMessage="Sin eventos en el período seleccionado"
            className="absolute inset-0"
            style={{ minHeight: '300px' }}
          />
        </div>
      </div>

      {/* Event Detail Modal */}
      <EventDetailModal event={selectedEvent} onClose={() => setSelectedEvent(null)} />

      {/* Keyboard Shortcuts Help */}
      <KeyboardShortcutsBar />
    </div>
  );
}

export default TimelineScheduler;
