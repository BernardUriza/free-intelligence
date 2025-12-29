'use client';

/**
 * DesktopAuth0Provider - Native OAuth for Tauri Desktop
 *
 * This provider handles Auth0 authentication for the desktop app using:
 * - Deep links (aurity://callback) for OAuth callbacks
 * - OS Keychain for secure token storage
 * - PKCE flow (no client secret required)
 *
 * Provides the same interface as @auth0/auth0-react for compatibility
 * with existing components that use useAuth().
 *
 * Flow:
 * 1. User clicks login → invoke('start_auth_flow') → opens browser
 * 2. User authenticates in browser → Auth0 redirects to aurity://callback
 * 3. Tauri captures deep link → emits 'deep-link-received' event
 * 4. Frontend handles callback → invoke('handle_auth_callback')
 * 5. Tokens stored in Keychain → user authenticated
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
  ReactNode,
} from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen, UnlistenFn } from '@tauri-apps/api/event';

// Auth0 token structure from Rust backend
interface AuthTokens {
  access_token: string;
  refresh_token: string | null;
  id_token: string | null;
  expires_at: number; // Unix timestamp (seconds)
  token_type: string;
}

// User profile extracted from JWT
interface User {
  sub: string;
  email?: string;
  email_verified?: boolean;
  name?: string;
  nickname?: string;
  picture?: string;
  updated_at?: string;
  'https://aurity.app/roles'?: string[];
  'https://aurity.app/permissions'?: string[];
}

// Context type matching Auth0 SDK interface
interface DesktopAuth0ContextType {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: User | null;
  error?: Error;
  loginWithRedirect: (options?: { appState?: { returnTo?: string } }) => Promise<void>;
  logout: (options?: { logoutParams?: { returnTo?: string } }) => Promise<void>;
  getAccessTokenSilently: (options?: {
    authorizationParams?: { audience?: string; scope?: string };
  }) => Promise<string>;
  getIdTokenClaims: () => Promise<Record<string, unknown> | undefined>;
}

const DesktopAuth0Context = createContext<DesktopAuth0ContextType | undefined>(undefined);

/**
 * Decode JWT payload without verification (verification done server-side)
 * Safe to use for extracting user info from id_token
 */
function decodeJwtPayload<T = Record<string, unknown>>(token: string): T | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const paddedBase64 = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');

    const jsonPayload = decodeURIComponent(
      atob(paddedBase64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );

    return JSON.parse(jsonPayload);
  } catch {
    console.error('[DesktopAuth] Failed to decode JWT');
    return null;
  }
}

/**
 * Extract User from id_token or access_token
 */
function extractUserFromToken(tokens: AuthTokens): User | null {
  const tokenToDecode = tokens.id_token || tokens.access_token;
  const payload = decodeJwtPayload<User>(tokenToDecode);

  if (!payload || !payload.sub) {
    return null;
  }

  return {
    sub: payload.sub,
    email: payload.email,
    email_verified: payload.email_verified,
    name: payload.name,
    nickname: payload.nickname,
    picture: payload.picture,
    updated_at: payload.updated_at,
    'https://aurity.app/roles': payload['https://aurity.app/roles'],
    'https://aurity.app/permissions': payload['https://aurity.app/permissions'],
  };
}

interface DesktopAuth0ProviderProps {
  children: ReactNode;
}

export function DesktopAuth0Provider({ children }: DesktopAuth0ProviderProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [error, setError] = useState<Error | undefined>();
  const [isConfigured, setIsConfigured] = useState(false);

  // Configure Auth0 on mount
  useEffect(() => {
    const configureAuth0 = async () => {
      const domain = process.env.NEXT_PUBLIC_AUTH0_DOMAIN;
      const clientId = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID;
      const audience = process.env.NEXT_PUBLIC_AUTH0_AUDIENCE || '';

      if (!domain || !clientId) {
        console.error('[DesktopAuth] Missing Auth0 configuration');
        setError(new Error('Auth0 configuration missing'));
        setIsLoading(false);
        return;
      }

      try {
        await invoke('configure_auth0', { domain, clientId, audience });
        setIsConfigured(true);
        console.log('[DesktopAuth] Auth0 configured successfully');
      } catch (err) {
        console.error('[DesktopAuth] Failed to configure Auth0:', err);
        setError(err instanceof Error ? err : new Error(String(err)));
      }
    };

    configureAuth0();
  }, []);

  // Initialize - check for stored tokens
  useEffect(() => {
    if (!isConfigured) return;

    const init = async () => {
      try {
        const storedTokens = await invoke<AuthTokens | null>('get_stored_tokens');

        if (storedTokens) {
          const isExpired = await invoke<boolean>('is_token_expired');

          if (isExpired && storedTokens.refresh_token) {
            // Try to refresh
            try {
              console.log('[DesktopAuth] Token expired, refreshing...');
              const newTokens = await invoke<AuthTokens>('refresh_tokens');
              setTokens(newTokens);
              setUser(extractUserFromToken(newTokens));
              setIsAuthenticated(true);
              console.log('[DesktopAuth] Token refreshed successfully');
            } catch (refreshError) {
              // Refresh failed - user needs to re-authenticate
              console.log('[DesktopAuth] Refresh failed, clearing tokens');
              await invoke('clear_tokens');
              setIsAuthenticated(false);
            }
          } else if (!isExpired) {
            // Token still valid
            setTokens(storedTokens);
            setUser(extractUserFromToken(storedTokens));
            setIsAuthenticated(true);
            console.log('[DesktopAuth] Valid stored token found');
          } else {
            // Expired with no refresh token
            console.log('[DesktopAuth] Token expired, no refresh token');
            await invoke('clear_tokens');
            setIsAuthenticated(false);
          }
        } else {
          console.log('[DesktopAuth] No stored tokens');
        }
      } catch (err) {
        console.error('[DesktopAuth] Init error:', err);
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setIsLoading(false);
      }
    };

    init();
  }, [isConfigured]);

  // Listen for deep link callbacks (OAuth redirect)
  useEffect(() => {
    let unlisten: UnlistenFn | null = null;

    const setupListener = async () => {
      unlisten = await listen<string>('deep-link-received', async (event) => {
        const url = event.payload;
        console.log('[DesktopAuth] Deep link received:', url);

        if (url.startsWith('aurity://callback')) {
          setIsLoading(true);
          setError(undefined);

          try {
            const newTokens = await invoke<AuthTokens>('handle_auth_callback', {
              callbackUrl: url,
            });
            setTokens(newTokens);
            setUser(extractUserFromToken(newTokens));
            setIsAuthenticated(true);
            console.log('[DesktopAuth] Authentication successful');
          } catch (err) {
            console.error('[DesktopAuth] Callback error:', err);
            setError(err instanceof Error ? err : new Error(String(err)));
          } finally {
            setIsLoading(false);
          }
        }
      });
    };

    setupListener();

    return () => {
      if (unlisten) {
        unlisten();
      }
    };
  }, []);

  // Auto-refresh tokens before expiry
  useEffect(() => {
    if (!tokens || !tokens.refresh_token || !isAuthenticated) return;

    const now = Math.floor(Date.now() / 1000);
    const timeUntilExpiry = tokens.expires_at - now - 60; // 60s buffer

    if (timeUntilExpiry <= 0) {
      // Already expired or about to expire, refresh immediately
      invoke<AuthTokens>('refresh_tokens')
        .then((newTokens) => {
          setTokens(newTokens);
          setUser(extractUserFromToken(newTokens));
          console.log('[DesktopAuth] Token auto-refreshed');
        })
        .catch((err) => {
          console.error('[DesktopAuth] Auto-refresh failed:', err);
          setIsAuthenticated(false);
          setUser(null);
          setTokens(null);
        });
      return;
    }

    // Schedule refresh before expiry
    const timer = setTimeout(async () => {
      try {
        const newTokens = await invoke<AuthTokens>('refresh_tokens');
        setTokens(newTokens);
        setUser(extractUserFromToken(newTokens));
        console.log('[DesktopAuth] Token auto-refreshed (scheduled)');
      } catch (err) {
        console.error('[DesktopAuth] Scheduled auto-refresh failed:', err);
        setIsAuthenticated(false);
        setUser(null);
        setTokens(null);
      }
    }, timeUntilExpiry * 1000);

    return () => clearTimeout(timer);
  }, [tokens, isAuthenticated]);

  const loginWithRedirect = useCallback(
    async (_options?: { appState?: { returnTo?: string } }) => {
      if (!isConfigured) {
        throw new Error('Auth0 not configured');
      }

      setIsLoading(true);
      setError(undefined);

      try {
        // This opens the browser - the callback will be handled by deep link listener
        await invoke('start_auth_flow');
        console.log('[DesktopAuth] Auth flow started, browser opened');
        // Note: isLoading stays true until callback is received
      } catch (err) {
        console.error('[DesktopAuth] Login error:', err);
        setError(err instanceof Error ? err : new Error(String(err)));
        setIsLoading(false);
      }
    },
    [isConfigured]
  );

  const logout = useCallback(
    async (options?: { logoutParams?: { returnTo?: string } }) => {
      try {
        await invoke('clear_tokens');
        setIsAuthenticated(false);
        setUser(null);
        setTokens(null);
        setError(undefined);
        console.log('[DesktopAuth] Logged out successfully');

        // Redirect if specified
        if (options?.logoutParams?.returnTo && typeof window !== 'undefined') {
          window.location.href = options.logoutParams.returnTo;
        }
      } catch (err) {
        console.error('[DesktopAuth] Logout error:', err);
        // Even on error, clear local state
        setIsAuthenticated(false);
        setUser(null);
        setTokens(null);
      }
    },
    []
  );

  const getAccessTokenSilently = useCallback(async (): Promise<string> => {
    if (!tokens) {
      throw new Error('Not authenticated');
    }

    // Check if token needs refresh
    const isExpired = await invoke<boolean>('is_token_expired');

    if (isExpired && tokens.refresh_token) {
      const newTokens = await invoke<AuthTokens>('refresh_tokens');
      setTokens(newTokens);
      setUser(extractUserFromToken(newTokens));
      return newTokens.access_token;
    }

    if (isExpired) {
      throw new Error('Token expired and no refresh token available');
    }

    return tokens.access_token;
  }, [tokens]);

  const getIdTokenClaims = useCallback(async () => {
    if (!tokens?.id_token) return undefined;
    return decodeJwtPayload(tokens.id_token) ?? undefined;
  }, [tokens]);

  const contextValue = useMemo(
    () => ({
      isLoading,
      isAuthenticated,
      user,
      error,
      loginWithRedirect,
      logout,
      getAccessTokenSilently,
      getIdTokenClaims,
    }),
    [
      isLoading,
      isAuthenticated,
      user,
      error,
      loginWithRedirect,
      logout,
      getAccessTokenSilently,
      getIdTokenClaims,
    ]
  );

  return (
    <DesktopAuth0Context.Provider value={contextValue}>
      {children}
    </DesktopAuth0Context.Provider>
  );
}

export function useDesktopAuth0(): DesktopAuth0ContextType {
  const context = useContext(DesktopAuth0Context);
  if (!context) {
    throw new Error('useDesktopAuth0 must be used within DesktopAuth0Provider');
  }
  return context;
}
