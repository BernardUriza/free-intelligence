/**
 * Free Intelligence - API Client
 *
 * Sessions API client with cache support.
 *
 * File: apps/aurity/lib/api/apiClient.ts
 * Cards: FI-UI-FEAT-201, FI-API-FEAT-010
 * Created: 2025-10-29
 * Updated: 2026-02 - Migrated to centralized api client
 */

import type { Session, SessionsListResponse } from "../../types/session";
import { api } from "./client";
import { ROUTES } from "./routes";
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('ApiClient');

const CACHE_KEY_SESSIONS = "fi_sessions_cache";
const CACHE_TTL_MS = 30000; // 30 seconds cache TTL

/**
 * Cache helper for localStorage
 */
function getCachedData<T>(key: string): T | null {
  if (typeof window === "undefined") return null;

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
  if (typeof window === "undefined") return;

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

/**
 * Get sessions list with cache fallback
 */
export async function getSessions(params?: {
  limit?: number;
  offset?: number;
  owner_hash?: string;
}): Promise<SessionsListResponse> {
  const query = new URLSearchParams();
  if (params?.limit) query.set("limit", params.limit.toString());
  if (params?.offset) query.set("offset", params.offset.toString());
  if (params?.owner_hash) query.set("owner_hash", params.owner_hash);

  try {
    const data = await api.get<SessionsListResponse>(`${ROUTES.sessions}?${query.toString()}`);

    // Cache successful response
    setCachedData(CACHE_KEY_SESSIONS, data);

    return data;
  } catch (error) {
    // Fallback to cache on error
    const cached = getCachedData<SessionsListResponse>(CACHE_KEY_SESSIONS);
    if (cached) {
      log.warn('Using cached sessions data due to error', { error: String(error) });
      return cached;
    }

    // No cache available, rethrow error
    throw error;
  }
}

/**
 * Get single session detail
 */
export async function getSession(sessionId: string): Promise<Session> {
  return api.get<Session>(`${ROUTES.sessions}/${sessionId}`);
}
