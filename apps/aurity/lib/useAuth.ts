// =============================================================================
// useAuth Hook - Client-side authentication utility
// =============================================================================
// Provides authentication functions and token management
// Sprint: SPR-2025W44 - Bug fix for JWT token authentication
// Version: 0.1.0
// =============================================================================

'use client';

import { useState, useEffect } from 'react';

interface AuthUser {
  id: string;
  email: string;
  role: string;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface LoginResponse {
  success: boolean;
  token?: string;
  user?: AuthUser;
  error?: string;
  message?: string;
}

/**
 * useAuth hook - Manages authentication state
 *
 * For SPR-2025W44:
 * - Auto-login with admin credentials for development
 * - Stores token in sessionStorage
 * - Provides getToken() for API requests
 */
export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>({
    token: null,
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Initialize auth state from sessionStorage
  useEffect(() => {
    const storedToken = sessionStorage.getItem('auth_token');
    const storedUser = sessionStorage.getItem('auth_user');

    if (storedToken && storedUser) {
      try {
        const user = JSON.parse(storedUser);
        setAuthState({
          token: storedToken,
          user,
          isAuthenticated: true,
          isLoading: false,
        });
      } catch {
        // Invalid stored data, clear it
        sessionStorage.removeItem('auth_token');
        sessionStorage.removeItem('auth_user');
        setAuthState((prev) => ({ ...prev, isLoading: false }));
      }
    } else {
      // Auto-login is dangerous if accidentally enabled in staging/production.
      // Gate auto-login behind an explicit env var for development only.
      const allowAuto = (process.env.NEXT_PUBLIC_ALLOW_DEV_AUTOLOGIN || 'false').toLowerCase() === 'true';
      const isDev = process.env.NODE_ENV !== 'production';

      if (isDev && allowAuto) {
        // Only attempt auto-login in development when explicitly allowed
        autoLoginAdmin();
      } else {
        setAuthState((prev) => ({ ...prev, isLoading: false }));
      }
    }
  }, []);

  /**
   * Auto-login with default admin credentials (development mode)
   */
  const autoLoginAdmin = async () => {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: 'admin@aurity.local',
          password: 'admin', // Stub password for development
        }),
      });

      const result: LoginResponse = await response.json();

      if (result.success && result.token && result.user) {
        // Store in sessionStorage
        sessionStorage.setItem('auth_token', result.token);
        sessionStorage.setItem('auth_user', JSON.stringify(result.user));

        setAuthState({
          token: result.token,
          user: result.user,
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        console.error('Auto-login failed:', result.message || result.error);
        setAuthState((prev) => ({ ...prev, isLoading: false }));
      }
    } catch (error) {
      console.error('Auto-login error:', error);
      setAuthState((prev) => ({ ...prev, isLoading: false }));
    }
  };

  /**
   * Manual login
   */
  const login = async (email: string, password: string): Promise<LoginResponse> => {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const result: LoginResponse = await response.json();

      if (result.success && result.token && result.user) {
        // Store in sessionStorage
        sessionStorage.setItem('auth_token', result.token);
        sessionStorage.setItem('auth_user', JSON.stringify(result.user));

        setAuthState({
          token: result.token,
          user: result.user,
          isAuthenticated: true,
          isLoading: false,
        });
      }

      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Login failed',
      };
    }
  };

  /**
   * Logout
   */
  const logout = () => {
    sessionStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_user');

    setAuthState({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  };

  /**
   * Get current token (for API requests)
   */
  const getToken = (): string | null => {
    return authState.token || sessionStorage.getItem('auth_token');
  };

  return {
    ...authState,
    login,
    logout,
    getToken,
  };
}
