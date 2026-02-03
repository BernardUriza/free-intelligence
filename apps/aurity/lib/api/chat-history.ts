/**
 * Chat History API Client
 *
 * Client for conversation history endpoints (assistant_history.py)
 * Enables longitudinal memory view with chat messages + audio chunks.
 *
 * Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
 * Created: 2025-11-22
 */

import { getBackendUrl } from '@/lib/config/deployment';

const API_BASE_URL = getBackendUrl();

const TIMEOUT_MS = 5000; // 5 second timeout (chat history can be large)

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

// ============================================================================
// Types
// ============================================================================

export interface ChatInteraction {
  session_id: string;
  timestamp: number; // Unix timestamp (seconds)
  role: 'user' | 'assistant';
  content: string;
  persona: string | null;
  similarity?: number; // Only present in search results
}

export interface PaginatedHistoryResponse {
  interactions: ChatInteraction[];
  total: number;
  has_more: boolean;
  offset: number;
  limit: number;
}

export interface HistorySearchResponse {
  results: ChatInteraction[];
  total_interactions: number;
  query: string;
}

export interface HistoryStatsResponse {
  total_interactions: number;
  unique_sessions: number;
  memory_index_exists: boolean;
  doctor_id: string;
  oldest_timestamp?: number;
  newest_timestamp?: number;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get paginated chat history for a doctor (newest first)
 * Perfect for infinite scroll and Timeline integration
 */
export async function getChatHistory(params: {
  doctorId: string;
  offset?: number;
  limit?: number;
  sessionId?: string;
}): Promise<PaginatedHistoryResponse> {
  const { doctorId, offset = 0, limit = 50, sessionId } = params;

  const url = new URL(`${API_BASE_URL}/api/aurity/assistant/history/paginated`);
  url.searchParams.set('doctor_id', doctorId);
  url.searchParams.set('offset', offset.toString());
  url.searchParams.set('limit', limit.toString());
  if (sessionId) {
    url.searchParams.set('session_id', sessionId);
  }

  try {
    const response = await fetchWithTimeout(url.toString());

    if (!response.ok) {
      if (response.status === 404) {
        // No history yet - return empty
        return {
          interactions: [],
          total: 0,
          has_more: false,
          offset,
          limit,
        };
      }
      throw new Error(`Failed to fetch chat history: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    console.error('[ChatHistory API] Failed to fetch history:', error);
    // Return empty on error (graceful degradation)
    return {
      interactions: [],
      total: 0,
      has_more: false,
      offset,
      limit,
    };
  }
}

/**
 * Search chat history using semantic search
 */
export async function searchChatHistory(params: {
  doctorId: string;
  query: string;
  limit?: number;
  sessionId?: string;
}): Promise<HistorySearchResponse> {
  const { doctorId, query, limit = 10, sessionId } = params;

  const url = `${API_BASE_URL}/api/aurity/assistant/history/search`;

  try {
    const response = await fetchWithTimeout(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        doctor_id: doctorId,
        query,
        limit,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      if (response.status === 404) {
        return { results: [], total_interactions: 0, query };
      }
      throw new Error(`Search failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    console.error('[ChatHistory API] Search failed:', error);
    return { results: [], total_interactions: 0, query };
  }
}

/**
 * Get chat history statistics
 */
export async function getChatHistoryStats(doctorId: string): Promise<HistoryStatsResponse> {
  const url = new URL(`${API_BASE_URL}/api/aurity/assistant/history/stats`);
  url.searchParams.set('doctor_id', doctorId);

  try {
    const response = await fetchWithTimeout(url.toString());

    if (!response.ok) {
      throw new Error(`Failed to fetch stats: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    console.error('[ChatHistory API] Failed to fetch stats:', error);
    return {
      total_interactions: 0,
      unique_sessions: 0,
      memory_index_exists: false,
      doctor_id: doctorId,
    };
  }
}
