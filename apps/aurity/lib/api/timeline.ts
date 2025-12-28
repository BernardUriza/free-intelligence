/**
 * Timeline API Client
 *
 * Client for Free Intelligence Timeline API (backend/timeline_api.py)
 * Port: 9002
 *
 * Cards: FI-UI-FEAT-100, FI-API-FEAT-010
 * Updated: 2025-10-30 - Added timeout, retry, cache
 */

// Timeline router mounted at /api/workflows/aurity/timeline (updated 2025-11-15)
const API_BASE_URL =
  process.env.NEXT_PUBLIC_TIMELINE_API_URL || 'http://localhost:7001/api/workflows/aurity';

const TIMEOUT_MS = 1000; // 1 second timeout
const CACHE_KEY_SUMMARIES = 'fi_timeline_summaries';
const CACHE_TTL_MS = 30000; // 30 seconds cache TTL

/**
 * Fetch with timeout using AbortController
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = TIMEOUT_MS
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
 * Retry logic for 5xx errors and network errors
 */
async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  maxRetries: number = 1
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetchWithTimeout(url, options);

      // Retry on 5xx errors
      if (response.status >= 500 && attempt < maxRetries) {
        lastError = new Error(`Server error: ${response.status}`);
        continue;
      }

      return response;
    } catch (error) {
      // Retry on network errors (timeout, abort, network failure)
      if (attempt < maxRetries) {
        lastError = error as Error;
        continue;
      }
      throw error;
    }
  }

  throw lastError || new Error('Request failed');
}

/**
 * Cache helper for localStorage
 */
function getCachedData<T>(key: string): T | null {
  if (typeof window === 'undefined') return null; // SSR guard

  try {
    const cached = localStorage.getItem(key);
    if (!cached) return null;

    const { data, timestamp } = JSON.parse(cached);
    const now = Date.now();

    // Check if cache is still valid
    if (now - timestamp < CACHE_TTL_MS) {
      return data as T;
    }

    // Expired, remove it
    localStorage.removeItem(key);
    return null;
  } catch {
    return null;
  }
}

function setCachedData<T>(key: string, data: T): void {
  if (typeof window === 'undefined') return; // SSR guard

  try {
    const cacheEntry = {
      data,
      timestamp: Date.now(),
    };
    localStorage.setItem(key, JSON.stringify(cacheEntry));
  } catch {
    // Ignore cache errors (e.g., quota exceeded)
  }
}

export interface SessionMetadata {
  session_id: string;
  thread_id: string | null;
  owner_hash: string;
  created_at: string;
  updated_at: string;
}

export interface SessionTimespan {
  start: string;
  end: string;
  duration_ms: number;
  duration_human: string;
}

export interface SessionSize {
  interaction_count: number;
  total_tokens: number;
  total_chars: number;
  avg_tokens_per_interaction: number;
  size_human: string;
}

export interface PolicyBadges {
  hash_verified: 'OK' | 'FAIL' | 'PENDING' | 'N/A';
  policy_compliant: 'OK' | 'FAIL' | 'PENDING' | 'N/A';
  redaction_applied: 'OK' | 'FAIL' | 'PENDING' | 'N/A';
  audit_logged: 'OK' | 'FAIL' | 'PENDING' | 'N/A';
}

export interface SessionSummary {
  metadata: SessionMetadata;
  timespan: SessionTimespan;
  size: SessionSize;
  policy_badges: PolicyBadges;
  preview: string;
}

/**
 * SessionListItem - Lightweight session list from /sessions endpoint
 * Includes patient_name and doctor_name (extracted from diarization or metadata)
 */
export interface SessionListItem {
  session_id: string;
  created_at: string;
  has_transcription: boolean;
  has_diarization: boolean;
  has_soap: boolean;
  chunk_count: number;
  duration_seconds: number;
  preview: string;
  patient_name: string;
  doctor_name: string;
}

export interface SessionsListResponse {
  sessions: SessionListItem[];
  total: number;
}

export interface EventResponse {
  event_id: string;
  event_type: string;
  timestamp: string;
  who: string;
  what: string;
  summary: string | null;
  content_hash: string;
  redaction_policy: string;
  causality: any[];
  tags: string[];
  auto_generated: boolean;
  generation_mode: string;
  confidence_score: number;
}

export interface SessionDetail {
  metadata: SessionMetadata;
  timespan: SessionTimespan;
  size: SessionSize;
  policy_badges: PolicyBadges;
  events: EventResponse[];
  generation_mode: string;
  auto_events_count: number;
  manual_events_count: number;
  redaction_stats: Record<string, number>;
}

export interface TimelineStats {
  total_sessions: number;
  total_events: number;
  total_tokens: number;
  avg_events_per_session: number;
  event_types_breakdown: Record<string, number>;
  redaction_stats: Record<string, number>;
  generation_modes: Record<string, number>;
  date_range: Record<string, string>;
}

/**
 * Fetch session summaries with pagination, cache fallback
 */
export async function getSessionSummaries(params?: {
  limit?: number;
  offset?: number;
  sort?: 'recent' | 'oldest' | 'events_desc' | 'events_asc';
}): Promise<SessionSummary[]> {
  const { limit = 50, offset = 0, sort = 'recent' } = params || {};

  const url = new URL(`${API_BASE_URL}/timeline/sessions`);
  url.searchParams.set('limit', limit.toString());
  url.searchParams.set('offset', offset.toString());
  url.searchParams.set('sort', sort);

  try {
    // Try to fetch with timeout and retry
    const response = await fetchWithRetry(url.toString());

    if (!response.ok) {
      throw new Error(`Failed to fetch sessions: ${response.statusText}`);
    }

    const data = await response.json();

    // Cache successful response
    setCachedData(CACHE_KEY_SUMMARIES, data);

    return data;
  } catch (error) {
    // Fallback to cache on error
    const cached = getCachedData<SessionSummary[]>(CACHE_KEY_SUMMARIES);
    if (cached) {
      console.warn('Using cached session summaries due to error:', error);
      return cached;
    }

    // No cache available, rethrow error
    throw error;
  }
}

/**
 * Get lightweight sessions list with patient/doctor names
 * Uses /sessions endpoint (sessions_list.py) NOT /timeline/sessions
 *
 * This endpoint is MUCH faster and includes patient_name + doctor_name
 * extracted from session metadata or diarization results.
 */
export async function getSessionsList(params?: {
  limit?: number;
  offset?: number;
}): Promise<SessionsListResponse> {
  const { limit = 20, offset = 0 } = params || {};

  const url = new URL(`${API_BASE_URL}/sessions`);
  url.searchParams.set('limit', limit.toString());
  url.searchParams.set('offset', offset.toString());

  try {
    const response = await fetchWithRetry(url.toString());

    if (!response.ok) {
      throw new Error(`Failed to fetch sessions list: ${response.statusText}`);
    }

    const data: SessionsListResponse = await response.json();
    return data;
  } catch (error) {
    console.error('[Timeline API] Failed to fetch sessions list:', error);
    throw error;
  }
}

/**
 * Fetch session detail by ID with retry
 */
export async function getSessionDetail(
  sessionId: string
): Promise<SessionDetail> {
  const url = `${API_BASE_URL}/timeline/sessions/${sessionId}`;

  // Use retry for session detail (no cache for individual sessions)
  const response = await fetchWithRetry(url);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Session ${sessionId} not found`);
    }
    throw new Error(`Failed to fetch session: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch events with filters
 */
export async function getEvents(params?: {
  session_id?: string;
  event_type?: string;
  who?: string;
  limit?: number;
  offset?: number;
}): Promise<EventResponse[]> {
  const { session_id, event_type, who, limit = 100, offset = 0 } = params || {};

  const url = new URL(`${API_BASE_URL}/timeline/events`);

  if (session_id) url.searchParams.set('session_id', session_id);
  if (event_type) url.searchParams.set('event_type', event_type);
  if (who) url.searchParams.set('who', who);

  url.searchParams.set('limit', limit.toString());
  url.searchParams.set('offset', offset.toString());

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch events: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch timeline statistics
 */
export async function getTimelineStats(): Promise<TimelineStats> {
  const url = `${API_BASE_URL}/timeline/stats`;

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch stats: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{
  status: string;
  storage_path: string;
  storage_exists: boolean;
  timestamp: string;
}> {
  const url = `${API_BASE_URL}/health`;

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Audio Chunk Interface
 * Represents a transcription chunk with audio metadata
 */
export interface AudioChunk {
  chunk_number: number;
  transcript: string;
  language: string;
  duration: number;
  audio_hash: string;
  timestamp_start: number;
  timestamp_end: number;
  created_at: string;
  stt_provider?: string;
  confidence_score?: number;
  latency_ms?: number;
  audio_quality?: string;
}

/**
 * Fetch session audio chunks with timestamp ranges
 * This endpoint provides granular transcription data with timing information
 * Perfect for gantt charts and audio playback
 */
export async function getSessionChunks(sessionId: string): Promise<AudioChunk[]> {
  const url = `${API_BASE_URL}/sessions/${sessionId}/chunks`;

  try {
    const response = await fetchWithRetry(url);

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Chunks not found for session ${sessionId}`);
      }
      throw new Error(`Failed to fetch chunks: ${response.statusText}`);
    }

    const data = await response.json();
    return data.chunks || [];
  } catch (error) {
    console.error('[Timeline API] Failed to fetch session chunks:', error);
    throw error;
  }
}
