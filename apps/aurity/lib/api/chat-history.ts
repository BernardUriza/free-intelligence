/**
 * Chat History API Client
 *
 * Client for conversation history endpoints (assistant_history.py)
 * Enables longitudinal memory view with chat messages + audio chunks.
 *
 * Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
 * Created: 2025-11-22
 * Updated: 2026-02 - Migrated to centralized api client
 */

import { api } from './client';

const API_BASE = '/api/aurity/assistant/history';

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

export interface ChatHistorySearchResponse {
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

  const queryParams = new URLSearchParams();
  queryParams.set('doctor_id', doctorId);
  queryParams.set('offset', offset.toString());
  queryParams.set('limit', limit.toString());
  if (sessionId) {
    queryParams.set('session_id', sessionId);
  }

  try {
    return await api.get<PaginatedHistoryResponse>(`${API_BASE}/paginated?${queryParams}`);
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
}): Promise<ChatHistorySearchResponse> {
  const { doctorId, query, limit = 10, sessionId } = params;

  try {
    return await api.post<ChatHistorySearchResponse>(`${API_BASE}/search`, {
      doctor_id: doctorId,
      query,
      limit,
      session_id: sessionId,
    });
  } catch (error) {
    console.error('[ChatHistory API] Search failed:', error);
    return { results: [], total_interactions: 0, query };
  }
}

/**
 * Get chat history statistics
 */
export async function getChatHistoryStats(doctorId: string): Promise<HistoryStatsResponse> {
  try {
    return await api.get<HistoryStatsResponse>(`${API_BASE}/stats?doctor_id=${doctorId}`);
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
