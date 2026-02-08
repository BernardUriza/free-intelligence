/**
 * Admin API Service
 *
 * Centralized API for admin operations (user management, etc.)
 *
 * NOTE: Auth token is now automatically obtained from auth storage
 * by the api client. No need for manual token management.
 *
 * Created: 2025-01-XX
 * Updated: 2026-02 - Migrated to centralized api client
 */

import { api } from './client';
import { ROUTES } from './routes';

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
  role?: string;
  blocked?: boolean;
}

export interface UsersListResponse {
  users: User[];
  total: number;
  page: number;
  per_page: number;
}

export interface UserRoleResponse {
  user_id: string;
  role: string;
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
    return api.get<UsersListResponse>(`${ROUTES.internalAdmin}/users${query ? `?${query}` : ''}`);
  },

  /**
   * Update user role (singular — backend expects { role: string })
   */
  updateUserRole: async (userId: string, role: string): Promise<UserRoleResponse> => {
    return api.put<UserRoleResponse>(
      `${ROUTES.internalAdmin}/users/${encodeURIComponent(userId)}/roles`,
      { role }
    );
  },

  /**
   * Block/unblock user
   */
  blockUser: async (userId: string, blocked: boolean): Promise<{ success: boolean }> => {
    return api.put<{ success: boolean }>(
      `${ROUTES.internalAdmin}/users/${encodeURIComponent(userId)}/block`,
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
    return api.post<User>(`${ROUTES.internalAdmin}/users`, userData);
  },
};

