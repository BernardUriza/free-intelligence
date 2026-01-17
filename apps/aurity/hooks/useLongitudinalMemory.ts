/**
 * useLongitudinalMemory Hook
 *
 * Custom hook for managing longitudinal memory state with:
 * - Pagination (infinite scroll)
 * - Time range filtering
 * - Event type filtering
 * - Automatic data windowing
 *
 * Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
 * Created: 2025-11-22
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import {
  getLongitudinalMemory,
  getMemoryStats,
  searchMemory,
  type MemoryEvent,
  type MemoryStatsResponse,
} from '@/lib/api/longitudinal-memory';
import {
  MEMORY_PAGINATION,
  MEMORY_TIME_RANGES,
  EVENT_TYPES,
  getTimeRangeFromPreset,
  type EventTypeFilter,
  type TimelinePreset,
} from '@/config/timeline.config';

// ============================================================================
// Types
// ============================================================================

export interface MemoryState {
  events: MemoryEvent[];
  total: number;
  hasMore: boolean;
  chatCount: number;
  audioCount: number;
}

export interface MemoryFilters {
  eventType: EventTypeFilter;
  timeRange: {
    start: string | null;
    end: string | null;
  };
  preset: TimelinePreset | null;
}

export interface UseLongitudinalMemoryReturn {
  // State
  events: MemoryEvent[];
  stats: MemoryStatsResponse | null;
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  total: number;

  // Counts
  chatCount: number;
  audioCount: number;

  // Filters
  filters: MemoryFilters;
  setEventType: (type: EventTypeFilter) => void;
  setTimeRangePreset: (preset: TimelinePreset) => void;
  setCustomTimeRange: (start: string | null, end: string | null) => void;

  // Search
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  isSearching: boolean;

  // Actions
  loadMore: () => Promise<void>;
  refresh: () => Promise<void>;

  // Auth state
  isAuthenticated: boolean;
  doctorId: string | null;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useLongitudinalMemory(): UseLongitudinalMemoryReturn {
  // Auth
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const doctorId = user?.sub ?? null;

  // State
  const [events, setEvents] = useState<MemoryEvent[]>([]);
  const [stats, setStats] = useState<MemoryStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [chatCount, setChatCount] = useState(0);
  const [audioCount, setAudioCount] = useState(0);

  // Filters
  const [filters, setFilters] = useState<MemoryFilters>({
    eventType: EVENT_TYPES.ALL,
    timeRange: { start: null, end: null },
    preset: MEMORY_TIME_RANGES.PRESETS.find(p => p.hours === null) ?? null,
  });

  // Search
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isSearching, setIsSearching] = useState(false);

  // Refs for pagination
  const offsetRef = useRef(0);
  const isFetchingRef = useRef(false);

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const fetchTimeline = useCallback(
    async (reset: boolean = true) => {
      if (!doctorId || isFetchingRef.current) return;

      isFetchingRef.current = true;
      const newOffset = reset ? 0 : offsetRef.current;

      if (reset) {
        setIsLoading(true);
        setError(null);
      } else {
        setIsLoadingMore(true);
      }

      try {
        // If searching, use search endpoint
        if (searchQuery.trim()) {
          setIsSearching(true);
          const response = await searchMemory({
            doctorId,
            query: searchQuery,
            offset: newOffset,
            limit: MEMORY_PAGINATION.DEFAULT_LIMIT,
          });

          if (reset) {
            setEvents(response.events);
            offsetRef.current = response.events.length;
          } else {
            setEvents(prev => [...prev, ...response.events]);
            offsetRef.current += response.events.length;
          }

          setTotal(response.total);
          // Fix: If we received 0 events, there's nothing more to load
          setHasMore(response.events.length > 0 && response.has_more);
          // Only update counts on first fetch (reset=true) to avoid overwriting
          // with 0 when subsequent pages have no matching events
          if (reset) {
            setChatCount(response.chat_count);
            setAudioCount(response.audio_count);
          }
          setIsSearching(false);
        } else {
          // Normal timeline fetch
          const response = await getLongitudinalMemory({
            doctorId,
            offset: newOffset,
            limit: MEMORY_PAGINATION.DEFAULT_LIMIT,
            eventType: filters.eventType,
            startTime: filters.timeRange.start,
            endTime: filters.timeRange.end,
          });

          if (reset) {
            setEvents(response.events);
            offsetRef.current = response.events.length;
          } else {
            setEvents(prev => [...prev, ...response.events]);
            offsetRef.current += response.events.length;
          }

          setTotal(response.total);
          // Fix: If we received 0 events, there's nothing more to load
          // (prevents infinite loop when backend returns has_more:true with 0 events)
          setHasMore(response.events.length > 0 && response.has_more);
          // Only update counts on first fetch (reset=true) to avoid overwriting
          // with 0 when subsequent pages have no matching events
          if (reset) {
            setChatCount(response.chat_count);
            setAudioCount(response.audio_count);
          }
        }
      } catch (err) {
        console.error('[useLongitudinalMemory] Fetch error:', err);
        setError('Error al cargar la memoria longitudinal');
      } finally {
        setIsLoading(false);
        setIsLoadingMore(false);
        isFetchingRef.current = false;
      }
    },
    [doctorId, filters, searchQuery]
  );

  const fetchStats = useCallback(async () => {
    if (!doctorId) return;

    try {
      const statsData = await getMemoryStats(doctorId);
      setStats(statsData);
    } catch {
      // Stats are optional, don't show error
    }
  }, [doctorId]);

  // ============================================================================
  // Effects
  // ============================================================================

  // Initial load when authenticated
  // NOTE: We intentionally exclude fetchTimeline/fetchStats from deps.
  // This effect should ONLY run when auth state changes, not when the
  // callbacks change (which would cause infinite loops).
  useEffect(() => {
    if (isAuthenticated && doctorId && !authLoading) {
      fetchTimeline(true);
      fetchStats();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, doctorId, authLoading]);

  // Refetch when filters change OR search query changes
  // NOTE: fetchTimeline is included to ensure we use the latest version
  // (fixes stale closure bug when clearing search)
  useEffect(() => {
    if (isAuthenticated && doctorId) {
      fetchTimeline(true);
    }
  }, [filters, searchQuery, isAuthenticated, doctorId, fetchTimeline]);

  // ============================================================================
  // Actions
  // ============================================================================

  const loadMore = useCallback(async () => {
    if (!hasMore || isLoadingMore || isFetchingRef.current) return;
    await fetchTimeline(false);
  }, [hasMore, isLoadingMore, fetchTimeline]);

  const refresh = useCallback(async () => {
    offsetRef.current = 0;
    await fetchTimeline(true);
    await fetchStats();
  }, [fetchTimeline, fetchStats]);

  const setEventType = useCallback((type: EventTypeFilter) => {
    setFilters(prev => ({ ...prev, eventType: type }));
  }, []);

  const setTimeRangePreset = useCallback((preset: TimelinePreset) => {
    const range = getTimeRangeFromPreset(preset);
    setFilters(prev => ({
      ...prev,
      preset,
      timeRange: range,
    }));
  }, []);

  const setCustomTimeRange = useCallback((start: string | null, end: string | null) => {
    setFilters(prev => ({
      ...prev,
      preset: null,
      timeRange: { start, end },
    }));
  }, []);

  // ============================================================================
  // Return
  // ============================================================================

  return {
    // State
    events,
    stats,
    isLoading: isLoading || authLoading,
    isLoadingMore,
    error,
    hasMore,
    total,

    // Counts
    chatCount,
    audioCount,

    // Filters
    filters,
    setEventType,
    setTimeRangePreset,
    setCustomTimeRange,

    // Search
    searchQuery,
    setSearchQuery,
    isSearching,

    // Actions
    loadMore,
    refresh,

    // Auth
    isAuthenticated,
    doctorId,
  };
}
