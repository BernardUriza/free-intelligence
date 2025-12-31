/**
 * Admin API Service
 *
 * Centralized API for admin operations (user management, etc.)
 * Replaces hardcoded fetch calls in UserManagement component.
 *
 * NOTE: These endpoints require Bearer token authentication.
 * Pass the token from getAccessTokenSilently() when calling.
 *
 * Created: 2025-01-XX
 * Author: Claude Code (P1 Architectural Fix)
 */

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

// ============================================================================
// Types
// ============================================================================

export interface User {
  user_id: string;
  email: string;
  name?: string;
  picture?: string;
  created_at?: string;
  last_login?: string;
  logins_count?: number;
  roles?: string[];
  blocked?: boolean;
}

export interface UsersListResponse {
  users: User[];
  total: number;
  page: number;
  per_page: number;
}

export interface UserRolesResponse {
  user_id: string;
  roles: string[];
}

// ============================================================================
// Token storage for admin API calls
// ============================================================================

let _adminToken: string | null = null;

/**
 * Set the admin token for API calls.
 * Call this with the token from getAccessTokenSilently() before using adminApi.
 */
export function setAdminToken(token: string | null): void {
  _adminToken = token;
}

/**
 * Get headers with auth token
 */
function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (_adminToken) {
    headers['Authorization'] = `Bearer ${_adminToken}`;
  }
  return headers;
}

/**
 * Authenticated fetch wrapper
 */
async function authFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorDetail = errorText;
    try {
      const errorJson = JSON.parse(errorText);
      errorDetail = errorJson.detail || errorText;
    } catch {
      // Keep errorText as is
    }
    throw new Error(`API Error ${response.status}: ${errorDetail}`);
  }

  return response.json();
}

// ============================================================================
// Admin API
// ============================================================================

export const adminApi = {
  /**
   * Get all users (paginated)
   */
  getUsers: async (options?: { per_page?: number; page?: number }): Promise<UsersListResponse> => {
    const params = new URLSearchParams();
    if (options?.per_page) params.append('per_page', options.per_page.toString());
    if (options?.page) params.append('page', options.page.toString());

    const query = params.toString();
    return authFetch<UsersListResponse>(`/internal/admin/users${query ? `?${query}` : ''}`);
  },

  /**
   * Get user roles
   */
  getUserRoles: async (userId: string): Promise<UserRolesResponse> => {
    return authFetch<UserRolesResponse>(`/internal/admin/users/${encodeURIComponent(userId)}/roles`);
  },

  /**
   * Update user roles
   */
  updateUserRoles: async (userId: string, roles: string[]): Promise<UserRolesResponse> => {
    return authFetch<UserRolesResponse>(
      `/internal/admin/users/${encodeURIComponent(userId)}/roles`,
      {
        method: 'PUT',
        body: JSON.stringify({ roles }),
      }
    );
  },

  /**
   * Block/unblock user
   */
  blockUser: async (userId: string, blocked: boolean): Promise<{ success: boolean }> => {
    return authFetch<{ success: boolean }>(
      `/internal/admin/users/${encodeURIComponent(userId)}/block`,
      {
        method: 'PUT',
        body: JSON.stringify({ blocked }),
      }
    );
  },

  /**
   * Create new user
   */
  createUser: async (userData: {
    email: string;
    name?: string;
    password?: string;
  }): Promise<User> => {
    return authFetch<User>('/internal/admin/users', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },
};

