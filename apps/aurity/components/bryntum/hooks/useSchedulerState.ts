/**
 * useSchedulerState Hook
 * 
 * Centralized state management for Bryntum SchedulerPro instances.
 * Manages view mode, date navigation, zoom, filtering, and UI state.
 * 
 * Design: Single source of truth for all scheduler-related state.
 * Replaces scattered useState calls with cohesive state management.
 */

import { useState, useCallback, useMemo } from 'react';
import type { ViewMode, SchedulerState, UnifiedEvent } from '../types/scheduler.types';
import { navigateDate as navigateDateUtil } from '../config/timeline-presets.config';

interface UseSchedulerStateProps {
  events: UnifiedEvent[];
  initialViewMode?: ViewMode;
  initialDate?: Date;
}

interface UseSchedulerStateReturn extends SchedulerState {
  // State updaters
  setIsReady: (ready: boolean) => void;
  setViewMode: (mode: ViewMode) => void;
  setCurrentDate: (date: Date) => void;
  setZoomLevel: (level: number) => void;
  setSelectedSession: (sessionId: string | null) => void;
  setSearchQuery: (query: string) => void;
  
  // Derived state
  filteredEvents: UnifiedEvent[];
  sessions: string[];
  chatCount: number;
  audioCount: number;
  
  // Actions
  navigateDate: (direction: 'prev' | 'next') => void;
  goToToday: () => void;
  jumpToLatestEvent: () => void;
  handleZoom: (direction: 'in' | 'out') => void;
}

export function useSchedulerState({
  events,
  initialViewMode = 'day',
  initialDate = new Date(),
}: UseSchedulerStateProps): UseSchedulerStateReturn {
  // Core state
  const [isReady, setIsReady] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>(initialViewMode);
  const [currentDate, setCurrentDate] = useState<Date>(initialDate);
  const [zoomLevel, setZoomLevel] = useState(1); // 0.5 to 2
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Derived: Unique sessions from events
  const sessions = useMemo(() => {
    const sessionSet = new Set<string>();
    events.forEach((e) => {
      if (e.session_id) sessionSet.add(e.session_id);
    });
    return Array.from(sessionSet);
  }, [events]);

  // Derived: Filtered events by selected session
  const filteredEvents = useMemo(() => {
    if (!selectedSession) return events;
    return events.filter((e) => e.session_id === selectedSession);
  }, [events, selectedSession]);

  // Derived: Event counts
  const chatCount = useMemo(
    () => filteredEvents.filter((e) => e.source === 'chat').length,
    [filteredEvents]
  );

  const audioCount = useMemo(
    () => filteredEvents.filter((e) => e.source === 'audio').length,
    [filteredEvents]
  );

  // Actions
  const navigateDate = useCallback(
    (direction: 'prev' | 'next') => {
      const newDate = navigateDateUtil(viewMode, currentDate, direction);
      setCurrentDate(newDate);
    },
    [viewMode, currentDate]
  );

  const goToToday = useCallback(() => {
    setCurrentDate(new Date());
  }, []);

  const jumpToLatestEvent = useCallback(() => {
    if (events.length === 0) return;
    
    // Events are sorted descending, so first is latest
    const latestEvent = events[0];
    const eventDate = new Date(latestEvent.timestamp * 1000);
    setCurrentDate(eventDate);
  }, [events]);

  const handleZoom = useCallback(
    (direction: 'in' | 'out') => {
      const delta = direction === 'in' ? 0.25 : -0.25;
      const newZoom = Math.max(0.5, Math.min(2, zoomLevel + delta));
      setZoomLevel(newZoom);
    },
    [zoomLevel]
  );

  return {
    // State
    isReady,
    viewMode,
    currentDate,
    zoomLevel,
    selectedSession,
    searchQuery,
    
    // Setters
    setIsReady,
    setViewMode,
    setCurrentDate,
    setZoomLevel,
    setSelectedSession,
    setSearchQuery,
    
    // Derived
    filteredEvents,
    sessions,
    chatCount,
    audioCount,
    
    // Actions
    navigateDate,
    goToToday,
    jumpToLatestEvent,
    handleZoom,
  };
}
