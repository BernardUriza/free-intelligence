/**
 * Base API Client - P1 Architectural Fix
 *
 * Centralized fetch wrapper with error handling, type safety, and auth support.
 *
 * CRITICAL FIX: Removed all hardcoded URLs. Single source of truth for backend URL.
 *
 * File: apps/aurity/lib/api/client.ts
 * Created: 2025-11-08
 * Refactored: 2025-01-XX (P1 - Remove hardcoded URLs, add auth support)
 * Updated: 2025-12-28 (Multi-target support via deployment config)
 */

import {
  getBackendUrl as getDeploymentBackendUrl,
  getTarget,
  isCloud,
} from '@/lib/config/deployment';

// Single source of truth for backend URL - now uses deployment target config
// Cloud: same-origin (empty string) or explicit NEXT_PUBLIC_BACKEND_URL
// Desktop: http://localhost:7001 (default) or explicit override
const BACKEND_URL = getDeploymentBackendUrl();

/**
 * Get the backend URL for direct fetch operations (e.g., SSE streaming)
 */
export function getBackendUrl(): string {
  return BACKEND_URL;
}

// Log deployment configuration in development
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  console.log(`[API Client] Target: ${getTarget()}, Backend: ${BACKEND_URL || '(same-origin)'}`);
}

// Warn in production if cloud mode is using same-origin (expected behavior)
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'production' && isCloud() && !BACKEND_URL) {
  console.info('[API Client] Cloud mode: Using same-origin relative API paths.');
}

export class APIError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

interface RequestOptions extends RequestInit {
  timeout?: number;
  retries?: number; // Number of retry attempts (default: 0 for regular requests, 3 for uploads)
  retryDelay?: number; // Initial retry delay in ms (default: 1000)
}

async function fetchWithTimeout(
  url: string,
  options: RequestOptions = {}
): Promise<Response> {
  const { timeout = 30000, ...fetchOptions } = options;

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

/**
 * Get auth token from storage (if available)
 *
 * FIXED: Now reads from Auth0's cache (@@auth0spajs@@ keys) instead of
 * non-existent legacy keys. Auth0 stores tokens in localStorage with
 * keys like: @@auth0spajs@@::<clientId>::<audience>::<scope>
 */
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;

  try {
    // 1. Try legacy keys first (backward compatibility)
    const legacyToken = sessionStorage.getItem('auth_token') ||
      sessionStorage.getItem('access_token') ||
      localStorage.getItem('auth_token') ||
      localStorage.getItem('access_token');

    if (legacyToken) return legacyToken;

    // 2. Read from Auth0 SDK cache (@@auth0spajs@@::...)
    // Auth0 stores cache in localStorage with format:
    // @@auth0spajs@@::<clientId>::<audience>::<scope>
    const auth0Keys = Object.keys(localStorage).filter(k =>
      k.startsWith('@@auth0spajs@@') && !k.includes('@@user@@')
    );

    if (auth0Keys.length === 0) {
      // User not authenticated or Auth0 cache cleared
      return null;
    }

    // Parse Auth0 cache (JSON structure)
    const cacheKey = auth0Keys[0]; // Use first match
    const cacheData = JSON.parse(localStorage.getItem(cacheKey) || '{}');

    // Extract access token from cache body
    // Structure: { body: { access_token: "...", ... }, expiresAt: ... }
    const accessToken = cacheData.body?.access_token;

    if (!accessToken) {
      console.warn('[getAuthToken] Auth0 cache exists but no access_token found');
      return null;
    }

    // Optional: Check token expiration (expiresAt is Unix timestamp)
    const expiresAt = cacheData.expiresAt;
    if (expiresAt && Date.now() / 1000 > expiresAt) {
      console.warn('[getAuthToken] Auth0 token expired, needs refresh');
      // Token expired, but return it anyway - Auth0 SDK will refresh if needed
    }

    return accessToken;
  } catch (error) {
    console.error('[getAuthToken] Failed to read token:', error);
    return null;
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const url = `${BACKEND_URL}${endpoint}`;

  // Build headers with auth token if available
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const authToken = getAuthToken();
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  try {
    const response = await fetchWithTimeout(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new APIError(
        response.status,
        response.statusText,
        errorText || `HTTP ${response.status}: ${response.statusText}`
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    // Include the attempted URL in the error to aid debugging (CORS / mixed-content / network)
    const errMsg = error instanceof Error ? error.message : 'Unknown';
    console.error(`[apiRequest] Network error fetching ${url}: ${errMsg}`);
    throw new Error(`Network error fetching ${url}: ${errMsg}`);
  }
}

/**
 * Sleep utility for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Upload multipart form data (files, audio chunks, etc.) with retry logic
 */
export async function apiUpload<T>(
  endpoint: string,
  formData: FormData,
  options: RequestOptions = {}
): Promise<T> {
  const url = `${BACKEND_URL}${endpoint}`;
  const { retries = 3, retryDelay = 1000, ...fetchOptions } = options;

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      if (attempt > 0) {
        // Exponential backoff: 1s, 2s, 4s
        const delay = retryDelay * Math.pow(2, attempt - 1);
        console.log(`[Upload Retry] Attempt ${attempt}/${retries} after ${delay}ms delay`);
        await sleep(delay);
      }

      const response = await fetchWithTimeout(url, {
        ...fetchOptions,
        method: 'POST',
        body: formData,
        // Don't set Content-Type - browser sets it with boundary
        headers: {
          ...fetchOptions.headers,
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new APIError(
          response.status,
          response.statusText,
          errorText || `Upload failed: ${response.statusText}`
        );
      }

      // Success - return result
      if (attempt > 0) {
        console.log(`[Upload Retry] Success on attempt ${attempt + 1}`);
      }
      return await response.json();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error('Unknown error');

      // Don't retry on HTTP errors (4xx, 5xx) - only retry network errors
      if (error instanceof APIError) {
        console.error(`[Upload] HTTP ${error.status} - not retrying`);
        throw error;
      }

      // Log retry attempt
      if (attempt < retries) {
        console.warn(
          `[Upload] Attempt ${attempt + 1}/${retries + 1} failed: ${lastError.message}`
        );
      } else {
        console.error(
          `[Upload] All ${retries + 1} attempts failed: ${lastError.message}`
        );
      }
    }
  }

  // All retries exhausted
  throw new Error(
    `Upload failed after ${retries + 1} attempts: ${lastError?.message || 'Unknown error'}`
  );
}

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'DELETE' }),

  upload: <T>(endpoint: string, formData: FormData, options?: RequestOptions) =>
    apiUpload<T>(endpoint, formData, options),
};
