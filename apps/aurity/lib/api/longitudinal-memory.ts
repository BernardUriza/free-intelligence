/**
 * Longitudinal Memory API Client
 *
 * Client for the longitudinal memory endpoint that combines
 * chat messages and audio transcriptions chronologically.
 *
 * Card: FI-PHIL-DOC-014 (Memoria Longitudinal)
 * Created: 2025-11-22
 * Updated: 2026-02 - Migrated to centralized api client
 */

import {
  MEMORY_PAGINATION,
  type EventTypeFilter,
} from '@/config/timeline.config';
import { api } from './client';
import { ROUTES } from './routes';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('LongitudinalMemory');

// API endpoint base — uses ROUTES.timeline as single source of truth
// Backend mounts memory router at /timeline/memory
const MEMORY_BASE = `${ROUTES.timeline}/memory`;
const MEMORY_ENDPOINT = MEMORY_BASE;
const MEMORY_STATS_ENDPOINT = `${MEMORY_BASE}/stats`;

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

  const queryParams = new URLSearchParams();
  queryParams.set('doctor_id', doctorId);
  queryParams.set('offset', offset.toString());
  queryParams.set('limit', Math.min(limit, MEMORY_PAGINATION.MAX_LIMIT).toString());
  queryParams.set('event_type', eventType);

  if (startTime) {
    queryParams.set('start_time', startTime);
  }
  if (endTime) {
    queryParams.set('end_time', endTime);
  }

  try {
    const data = await api.get<LongitudinalMemoryResponse>(`${MEMORY_ENDPOINT}?${queryParams}`);
    return data;
  } catch (error) {
    log.error('Fetch failed', { error: String(error) });
    return createEmptyResponse(offset, limit);
  }
}

/**
 * Get memory statistics
 */
export async function getMemoryStats(
  doctorId: string
): Promise<MemoryStatsResponse> {
  try {
    return await api.get<MemoryStatsResponse>(`${MEMORY_STATS_ENDPOINT}?doctor_id=${doctorId}`);
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

  const queryParams = new URLSearchParams();
  queryParams.set('doctor_id', doctorId);
  queryParams.set('query', query.trim());
  queryParams.set('offset', offset.toString());
  queryParams.set('limit', limit.toString());

  try {
    return await api.get<LongitudinalMemoryResponse>(`${MEMORY_BASE}/search?${queryParams}`);
  } catch (error) {
    log.error('Search failed', { error: String(error) });
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
