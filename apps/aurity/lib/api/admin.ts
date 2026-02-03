/**
 * Admin API Service
 *
 * Centralized API for admin operations (user management, etc.)
 *
 * NOTE: Auth token is now automatically obtained from Auth0 cache
 * by the api client. No need for manual token management.
 *
 * Created: 2025-01-XX
 * Updated: 2026-02 - Migrated to centralized api client
 */

import { api } from './client';

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
    return api.get<UsersListResponse>(`/internal/admin/users${query ? `?${query}` : ''}`);
  },

  /**
   * Get user roles
   */
  getUserRoles: async (userId: string): Promise<UserRolesResponse> => {
    return api.get<UserRolesResponse>(`/internal/admin/users/${encodeURIComponent(userId)}/roles`);
  },

  /**
   * Update user roles
   */
  updateUserRoles: async (userId: string, roles: string[]): Promise<UserRolesResponse> => {
    return api.put<UserRolesResponse>(
      `/internal/admin/users/${encodeURIComponent(userId)}/roles`,
      { roles }
    );
  },

  /**
   * Block/unblock user
   */
  blockUser: async (userId: string, blocked: boolean): Promise<{ success: boolean }> => {
    return api.put<{ success: boolean }>(
      `/internal/admin/users/${encodeURIComponent(userId)}/block`,
      { blocked }
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
    return api.post<User>('/internal/admin/users', userData);
  },
};

// Legacy exports for backwards compatibility
// These are deprecated - use adminApi directly
/** @deprecated Use adminApi directly - token is now handled automatically */
export function setAdminToken(_token: string | null): void {
  // No-op - auth is now handled automatically by api client
  console.warn('[admin.ts] setAdminToken is deprecated - token is handled automatically');
}
