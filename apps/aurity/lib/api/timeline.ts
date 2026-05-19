/**
 * Timeline API Client
 *
 * Client for Free Intelligence Timeline API (backend/timeline_api.py)
 *
 * Cards: FI-UI-FEAT-100, FI-API-FEAT-010
 * Updated: 2026-02 - Migrated to centralized api client
 */

import { api } from './client';
import { ROUTES } from './routes';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('Timeline');

const CACHE_KEY_SUMMARIES = 'fi_timeline_summaries';
const CACHE_TTL_MS = 30000; // 30 seconds cache TTL

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
  causality: unknown[];
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

  try {
    const data = await api.get<SessionSummary[]>(
      `${ROUTES.timeline}/sessions?limit=${limit}&offset=${offset}&sort=${sort}`
    );

    // Cache successful response
    setCachedData(CACHE_KEY_SUMMARIES, data);

    return data;
  } catch (error) {
    // Fallback to cache on error
    const cached = getCachedData<SessionSummary[]>(CACHE_KEY_SUMMARIES);
    if (cached) {
      log.warn('Using cached session summaries due to error', { error: String(error) });
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

  return api.get<SessionsListResponse>(
    `${ROUTES.auritySessions}?limit=${limit}&offset=${offset}`
  );
}

/**
 * Fetch session detail by ID
 */
export async function getSessionDetail(
  sessionId: string
): Promise<SessionDetail> {
  return api.get<SessionDetail>(`${ROUTES.timeline}/sessions/${sessionId}`);
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

  const queryParams = new URLSearchParams();
  if (session_id) queryParams.set('session_id', session_id);
  if (event_type) queryParams.set('event_type', event_type);
  if (who) queryParams.set('who', who);
  queryParams.set('limit', limit.toString());
  queryParams.set('offset', offset.toString());

  return api.get<EventResponse[]>(`${ROUTES.timeline}/events?${queryParams}`);
}

/**
 * Fetch timeline statistics
 */
export async function getTimelineStats(): Promise<TimelineStats> {
  return api.get<TimelineStats>(`${ROUTES.timeline}/stats`);
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
  return api.get<{
    status: string;
    storage_path: string;
    storage_exists: boolean;
    timestamp: string;
  }>(ROUTES.health);
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
  const data = await api.get<{ chunks: AudioChunk[] }>(
    `${ROUTES.auritySessions}/${sessionId}/chunks`
  );
  return data.chunks || [];
}
