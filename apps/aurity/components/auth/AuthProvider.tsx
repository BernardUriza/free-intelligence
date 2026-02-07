'use client';

/**
 * AuthProvider - Self-hosted JWT authentication context
 *
 * Custom auth provider with direct email/password auth.
 * Tokens stored in localStorage (works in both web and Tauri WebView).
 *
 * Provides the same useAuth() interface so existing components
 * don't need to change their hook usage patterns.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
  useRef,
  ReactNode,
} from 'react';
import {
  getStoredAccessToken,
  getStoredRefreshToken,
  storeTokens,
  clearTokens,
  isTokenExpired,
} from '@/lib/auth-storage';
import { getBackendUrl } from '@/lib/api/client';

// ── Types ──────────────────────────────────────────────────────────────────

interface AuthUser {
  sub: string;
  email?: string;
  name?: string;
  roles?: string[];
  clinic_id?: string;
  [key: string]: any;
}

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: AuthUser | undefined;
  error: Error | undefined;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: (options?: { logoutParams?: { returnTo?: string } }) => Promise<void>;
  /** @deprecated Use login() instead. Redirects to /login page. */
  loginWithRedirect: (options?: { appState?: { returnTo?: string } }) => Promise<void>;
  /** Returns the stored access token (or throws if not authenticated). */
  getAccessTokenSilently: (options?: any) => Promise<string>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ── Helpers ────────────────────────────────────────────────────────────────

function decodeJwtPayload(token: string): AuthUser | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

async function authFetch<T>(endpoint: string, body: Record<string, string>): Promise<T> {
  const url = `${getBackendUrl()}/api/auth${endpoint}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(data.detail || `Auth error: ${res.status}`);
  }
  return res.json();
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ── Provider ───────────────────────────────────────────────────────────────

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<AuthUser | undefined>();
  const [error, setError] = useState<Error | undefined>();
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Schedule auto-refresh before access token expires
  const scheduleRefresh = useCallback((token: string) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);

    const payload = decodeJwtPayload(token);
    if (!payload?.exp) return;

    const now = Math.floor(Date.now() / 1000);
    // Refresh 60s before expiry
    const delay = Math.max((payload.exp - now - 60) * 1000, 0);

    refreshTimerRef.current = setTimeout(async () => {
      const rt = getStoredRefreshToken();
      if (!rt) return;
      try {
        const data = await authFetch<TokenResponse>('/refresh', { refresh_token: rt });
        storeTokens(data.access_token, data.refresh_token);
        const newUser = decodeJwtPayload(data.access_token);
        if (newUser) setUser(newUser);
        scheduleRefresh(data.access_token);
      } catch {
        // Refresh failed — force re-login
        clearTokens();
        setIsAuthenticated(false);
        setUser(undefined);
      }
    }, delay);
  }, []);

  // Init: check stored token on mount
  useEffect(() => {
    const at = getStoredAccessToken();
    if (at && !isTokenExpired(at)) {
      const decoded = decodeJwtPayload(at);
      if (decoded) {
        setUser(decoded);
        setIsAuthenticated(true);
        scheduleRefresh(at);
      }
    } else if (at && isTokenExpired(at)) {
      // Try refresh
      const rt = getStoredRefreshToken();
      if (rt) {
        authFetch<TokenResponse>('/refresh', { refresh_token: rt })
          .then((data) => {
            storeTokens(data.access_token, data.refresh_token);
            const decoded = decodeJwtPayload(data.access_token);
            if (decoded) {
              setUser(decoded);
              setIsAuthenticated(true);
              scheduleRefresh(data.access_token);
            }
          })
          .catch(() => {
            clearTokens();
          });
      } else {
        clearTokens();
      }
    }
    setIsLoading(false);

    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, [scheduleRefresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      setIsLoading(true);
      setError(undefined);
      try {
        const data = await authFetch<TokenResponse>('/login', { email, password });
        storeTokens(data.access_token, data.refresh_token);
        const decoded = decodeJwtPayload(data.access_token);
        setUser(decoded ?? undefined);
        setIsAuthenticated(true);
        scheduleRefresh(data.access_token);
      } catch (err) {
        const e = err instanceof Error ? err : new Error(String(err));
        setError(e);
        throw e;
      } finally {
        setIsLoading(false);
      }
    },
    [scheduleRefresh]
  );

  const registerFn = useCallback(
    async (email: string, password: string, name: string) => {
      setIsLoading(true);
      setError(undefined);
      try {
        const data = await authFetch<TokenResponse>('/register', { email, password, name });
        storeTokens(data.access_token, data.refresh_token);
        const decoded = decodeJwtPayload(data.access_token);
        setUser(decoded ?? undefined);
        setIsAuthenticated(true);
        scheduleRefresh(data.access_token);
      } catch (err) {
        const e = err instanceof Error ? err : new Error(String(err));
        setError(e);
        throw e;
      } finally {
        setIsLoading(false);
      }
    },
    [scheduleRefresh]
  );

  const logout = useCallback(
    async (options?: { logoutParams?: { returnTo?: string } }) => {
      const rt = getStoredRefreshToken();
      if (rt) {
        // Best-effort revoke on server
        authFetch('/logout', { refresh_token: rt }).catch(() => {});
      }
      clearTokens();
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
      setIsAuthenticated(false);
      setUser(undefined);
      setError(undefined);

      const returnTo = options?.logoutParams?.returnTo;
      if (returnTo && typeof window !== 'undefined') {
        window.location.href = returnTo;
      }
    },
    []
  );

  const loginWithRedirect = useCallback(
    async (_options?: { appState?: { returnTo?: string } }) => {
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    },
    []
  );

  const getAccessTokenSilently = useCallback(async (_options?: any): Promise<string> => {
    const at = getStoredAccessToken();
    if (!at) throw new Error('Not authenticated');

    if (!isTokenExpired(at)) return at;

    // Token expired — try refresh
    const rt = getStoredRefreshToken();
    if (!rt) throw new Error('Not authenticated');

    const data = await authFetch<TokenResponse>('/refresh', { refresh_token: rt });
    storeTokens(data.access_token, data.refresh_token);
    const decoded = decodeJwtPayload(data.access_token);
    if (decoded) setUser(decoded);
    scheduleRefresh(data.access_token);
    return data.access_token;
  }, [scheduleRefresh]);

  const value = useMemo<AuthContextType>(
    () => ({
      isAuthenticated,
      isLoading,
      user,
      error,
      login,
      register: registerFn,
      logout,
      loginWithRedirect,
      getAccessTokenSilently,
    }),
    [isAuthenticated, isLoading, user, error, login, registerFn, logout, loginWithRedirect, getAccessTokenSilently]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ── Hook ───────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within <AuthProvider>');
  }
  return ctx;
}
