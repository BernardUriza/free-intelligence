/**
 * Longitudinal Memory API Client
 *
 * Client for the longitudinal memory endpoint that combines
 * chat messages and audio transcriptions chronologically.
 *
 * Card: FI-PHIL-DOC-014 (Memoria Longitudinal)
 * Created: 2025-11-22
 */

import {
  MEMORY_API,
  MEMORY_PAGINATION,
  type EventTypeFilter,
} from '@/config/timeline.config';

// ============================================================================
// Types (matching backend schemas)
// ============================================================================

export interface MemoryEvent {
  id: string;
  timestamp: number; // Unix timestamp (seconds)
  event_type: 'chat_user' | 'chat_assistant' | 'transcription';
  content: string;
  source: 'chat' | 'audio';

  // Optional metadata
  session_id?: string | null;
  persona?: string | null;
  chunk_number?: number | null;
  duration?: number | null;
  confidence?: number | null;
  language?: string | null;
  stt_provider?: string | null;
}

export interface LongitudinalMemoryResponse {
  events: MemoryEvent[];
  total: number;
  has_more: boolean;
  offset: number;
  limit: number;
  chat_count: number;
  audio_count: number;
  time_range: {
    start: string | null;
    end: string | null;
    start_ts: number | null;
    end_ts: number | null;
  };
}

export interface MemoryStatsResponse {
  total_events: number;
  chat_messages: number;
  audio_transcriptions: number;
  oldest_timestamp: number | null;
  newest_timestamp: number | null;
  unique_sessions: number;
}

export interface MemoryQueryParams {
  doctorId: string;
  offset?: number;
  limit?: number;
  eventType?: EventTypeFilter;
  startTime?: string | null;
  endTime?: string | null;
}

export interface MemorySearchParams {
  doctorId: string;
  query: string;
  offset?: number;
  limit?: number;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch with timeout using AbortController
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = MEMORY_API.TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Get longitudinal memory with pagination and filters
 *
 * @param params - Query parameters
 * @returns LongitudinalMemoryResponse
 */
export async function getLongitudinalMemory(
  params: MemoryQueryParams
): Promise<LongitudinalMemoryResponse> {
  const {
    doctorId,
    offset = 0,
    limit = MEMORY_PAGINATION.DEFAULT_LIMIT,
    eventType = 'all',
    startTime,
    endTime,
  } = params;

  const url = new URL(`${MEMORY_API.BASE_URL}${MEMORY_API.ENDPOINT}`);
  url.searchParams.set('doctor_id', doctorId);
  url.searchParams.set('offset', offset.toString());
  url.searchParams.set('limit', Math.min(limit, MEMORY_PAGINATION.MAX_LIMIT).toString());
  url.searchParams.set('event_type', eventType);

  if (startTime) {
    url.searchParams.set('start_time', startTime);
  }
  if (endTime) {
    url.searchParams.set('end_time', endTime);
  }

  try {
    console.log('[LongitudinalMemory] Fetching:', url.toString());
    const response = await fetchWithTimeout(url.toString());

    if (!response.ok) {
      console.error('[LongitudinalMemory] Error:', response.status, response.statusText);
      // Return empty response on error (graceful degradation)
      return createEmptyResponse(offset, limit);
    }

    const data: LongitudinalMemoryResponse = await response.json();
    console.log('[LongitudinalMemory] Received:', data.events.length, 'events');
    return data;

  } catch (error) {
    console.error('[LongitudinalMemory] Fetch failed:', error);
    return createEmptyResponse(offset, limit);
  }
}

/**
 * Get memory statistics
 */
export async function getMemoryStats(
  doctorId: string
): Promise<MemoryStatsResponse> {
  const url = new URL(`${MEMORY_API.BASE_URL}${MEMORY_API.STATS_ENDPOINT}`);
  url.searchParams.set('doctor_id', doctorId);

  try {
    const response = await fetchWithTimeout(url.toString());

    if (!response.ok) {
      return createEmptyStats();
    }

    return response.json();
  } catch {
    return createEmptyStats();
  }
}

/**
 * Load more events (for infinite scroll)
 */
export async function loadMoreMemoryEvents(
  params: MemoryQueryParams,
  currentOffset: number
): Promise<LongitudinalMemoryResponse> {
  return getLongitudinalMemory({
    ...params,
    offset: currentOffset,
  });
}

/**
 * Search longitudinal memory by text query
 */
export async function searchMemory(
  params: MemorySearchParams
): Promise<LongitudinalMemoryResponse> {
  const { doctorId, query, offset = 0, limit = MEMORY_PAGINATION.DEFAULT_LIMIT } = params;

  if (!query || query.trim().length === 0) {
    return createEmptyResponse(offset, limit);
  }

  const url = new URL(`${MEMORY_API.BASE_URL}/search`);
  url.searchParams.set('doctor_id', doctorId);
  url.searchParams.set('query', query.trim());
  url.searchParams.set('offset', offset.toString());
  url.searchParams.set('limit', limit.toString());

  try {
    const response = await fetchWithTimeout(url.toString());

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[searchMemory] Error:', error);
    return createEmptyResponse(offset, limit);
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

function createEmptyResponse(offset: number, limit: number): LongitudinalMemoryResponse {
  return {
    events: [],
    total: 0,
    has_more: false,
    offset,
    limit,
    chat_count: 0,
    audio_count: 0,
    time_range: {
      start: null,
      end: null,
      start_ts: null,
      end_ts: null,
    },
  };
}

function createEmptyStats(): MemoryStatsResponse {
  return {
    total_events: 0,
    chat_messages: 0,
    audio_transcriptions: 0,
    oldest_timestamp: null,
    newest_timestamp: null,
    unique_sessions: 0,
  };
}

// ============================================================================
// React Query Keys (for cache management)
// ============================================================================

export const memoryQueryKeys = {
  all: ['longitudinal-memory'] as const,
  list: (params: MemoryQueryParams) =>
    [...memoryQueryKeys.all, 'list', params] as const,
  search: (params: MemorySearchParams) =>
    [...memoryQueryKeys.all, 'search', params] as const,
  stats: (doctorId: string) =>
    [...memoryQueryKeys.all, 'stats', doctorId] as const,
};
