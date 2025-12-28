/**
 * Free Intelligence - API Client
 *
 * Fetch wrapper for Sessions API with timeout, retry, and cache.
 *
 * File: apps/aurity/ui/lib/apiClient.ts
 * Cards: FI-UI-FEAT-201, FI-API-FEAT-010
 * Created: 2025-10-29
 * Updated: 2025-10-30 - Added timeout, retry, cache
 */

import type { Session, SessionsListResponse } from "../../types/session";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:7001";
const TIMEOUT_MS = 1000; // 1 second timeout
const CACHE_KEY_SESSIONS = "fi_sessions_cache";
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

  throw lastError || new Error("Request failed");
}

/**
 * Cache helper for localStorage
 */
function getCachedData<T>(key: string): T | null {
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

  const url = `${API_BASE}/api/sessions?${query.toString()}`;

  try {
    // Try to fetch with timeout and retry
    const response = await fetchWithRetry(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch sessions: ${response.statusText}`);
    }

    const data = await response.json();

    // Cache successful response
    setCachedData(CACHE_KEY_SESSIONS, data);

    return data;
  } catch (error) {
    // Fallback to cache on error
    const cached = getCachedData<SessionsListResponse>(CACHE_KEY_SESSIONS);
    if (cached) {
      console.warn("Using cached sessions data due to error:", error);
      return cached;
    }

    // No cache available, rethrow error
    throw error;
  }
}

/**
 * Get single session detail with retry
 */
export async function getSession(sessionId: string): Promise<Session> {
  const url = `${API_BASE}/api/sessions/${sessionId}`;

  // Use retry for session detail (no cache for individual sessions)
  const response = await fetchWithRetry(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.statusText}`);
  }

  return response.json();
}
