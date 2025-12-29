'use client';

/**
 * Auth0Provider Component
 * HIPAA Card: G-003 - Auth0 OAuth2/OIDC Integration
 *
 * ARCHITECTURAL DECISION (2025-12-03 - REVISED):
 * Simplified approach after Qwen Code audit identified SSR/hydration risks.
 *
 * STRATEGY:
 * - Build-time decision via env vars (not runtime)
 * - No conditional rendering (prevents hydration mismatch)
 * - Single provider type per deployment environment
 *
 * DESKTOP AUTH (2025-12-28):
 * For Tauri desktop builds, we use DesktopAuth0Provider which:
 * - Uses deep links (aurity://callback) for OAuth callbacks
 * - Stores tokens in OS Keychain (not localStorage)
 * - Implements PKCE flow for security
 *
 * Components MUST import useAuth0 from this module (or @/hooks/useAuth)
 * rather than directly from @auth0/auth0-react to ensure compatibility.
 */

import { Auth0Provider as Auth0ProviderSDK, useAuth0 as useAuth0SDK } from '@auth0/auth0-react';
import { ReactNode, ReactElement, useEffect, useState } from 'react';
import { MockAuth0Provider, useAuth0 as useMockAuth0 } from './MockAuth0Provider';
import { DesktopAuth0Provider, useDesktopAuth0 } from './DesktopAuth0Provider';

interface Auth0ProviderProps {
  children: ReactNode;
}

/**
 * Detect if we're running inside Tauri (desktop app)
 * This check works at runtime after hydration
 */
function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI__' in window;
}

/**
 * Determine provider type at BUILD TIME (not runtime)
 * This prevents SSR/hydration mismatches
 *
 * Uses mock auth when:
 * 1. Explicitly enabled via NEXT_PUBLIC_USE_MOCK_AUTH=true
 * 2. Desktop offline mode enabled via NEXT_PUBLIC_DESKTOP_OFFLINE=true
 * 3. In development mode without Auth0 config
 * 4. In production build without Auth0 config (static export scenario)
 */
const USE_MOCK_AUTH =
  process.env.NEXT_PUBLIC_DESKTOP_OFFLINE === 'true' ||
  process.env.NEXT_PUBLIC_USE_MOCK_AUTH === 'true' ||
  !process.env.NEXT_PUBLIC_AUTH0_DOMAIN ||
  !process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID;

/**
 * Check if desktop auth should be used (Tauri + Auth0 configured + not offline mode)
 */
const DESKTOP_AUTH_POSSIBLE =
  !USE_MOCK_AUTH &&
  process.env.NEXT_PUBLIC_DEPLOYMENT_TARGET === 'desktop';

// Development-only logging utility
const devLog = (message: string, ...args: any[]) => {
  if (process.env.NODE_ENV === 'development') {
    console.log(message, ...args);
  }
};

export function Auth0Provider({ children }: Auth0ProviderProps): ReactElement {
  // For desktop builds, we need to detect Tauri at runtime
  // We use a state to handle this after hydration
  const [isTauri, setIsTauri] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsTauri(isTauriRuntime());
    setIsHydrated(true);
  }, []);

  // Decision made at build time, consistent across SSR and CSR
  if (USE_MOCK_AUTH) {
    devLog('[Auth0Provider] Using MockAuth0Provider (development/offline mode)');
    return <MockAuth0Provider>{children}</MockAuth0Provider>;
  }

  // For desktop builds with Auth0 configured, use DesktopAuth0Provider
  // We wait for hydration to avoid SSR mismatch
  if (DESKTOP_AUTH_POSSIBLE) {
    // During SSR or before hydration, show loading state
    if (!isHydrated) {
      return <>{children}</>; // Render children without auth during SSR
    }

    // After hydration, if we're in Tauri, use desktop auth
    if (isTauri) {
      devLog('[Auth0Provider] Using DesktopAuth0Provider (Tauri detected)');
      return <DesktopAuth0Provider>{children}</DesktopAuth0Provider>;
    }

    // SECURITY: Block desktop builds running outside Tauri
    // This prevents the desktop build from being accessed in a regular browser
    devLog('[Auth0Provider] ERROR: Desktop build accessed outside Tauri');
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-gray-900 text-white p-8">
        <div className="max-w-md text-center space-y-4">
          <div className="text-6xl">🔒</div>
          <h1 className="text-2xl font-bold">Aurity Desktop Required</h1>
          <p className="text-gray-400">
            This application is designed to run inside Aurity Desktop.
            Please open the app using the installed Aurity Desktop application.
          </p>
          <p className="text-sm text-gray-500">
            If you&apos;re a developer, run: <code className="bg-gray-800 px-2 py-1 rounded">cargo tauri dev</code>
          </p>
        </div>
      </div>
    );
  }

  // Validate required env vars (type-safe)
  const domain = process.env.NEXT_PUBLIC_AUTH0_DOMAIN;
  const clientId = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID;

  if (!domain || !clientId) {
    throw new Error(
      'Auth0 configuration missing. Required: NEXT_PUBLIC_AUTH0_DOMAIN, NEXT_PUBLIC_AUTH0_CLIENT_ID'
    );
  }

  // IMPORTANT: audience must come from env vars - NO hardcoded fallback
  // Dev and prod should use different Auth0 APIs or same API with different clients
  const audience = process.env.NEXT_PUBLIC_AUTH0_AUDIENCE;

  if (!audience) {
    console.error(
      '[Auth0Provider] NEXT_PUBLIC_AUTH0_AUDIENCE is not set. ' +
        'This is required for proper token audience validation.'
    );
  }

  // Build-time redirect URI (no runtime window check)
  const redirectUri = process.env.NEXT_PUBLIC_BASE_URL
    ? `${process.env.NEXT_PUBLIC_BASE_URL}/callback`
    : 'http://localhost:9000/callback';

  const onRedirectCallback = (appState?: { returnTo?: string }) => {
    devLog('[Auth0Provider] onRedirectCallback called with appState:', appState);
    const targetUrl = appState?.returnTo || '/chat';
    devLog('[Auth0Provider] Redirecting to:', targetUrl);

    if (typeof window !== 'undefined') {
      window.location.href = targetUrl;
    }
  };

  devLog('[Auth0Provider] Using real Auth0 SDK');
  return (
    <Auth0ProviderSDK
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: redirectUri,
        audience: audience,
        scope: 'openid profile email offline_access',
      }}
      onRedirectCallback={onRedirectCallback}
      useRefreshTokens={true}
      cacheLocation="localstorage"
    >
      {children}
    </Auth0ProviderSDK>
  );
}

/**
 * Unified useAuth0 hook
 *
 * UPDATED (2025-12-28):
 * - Supports mock, desktop (Tauri), and web Auth0 SDK
 * - Decision made at build time for mock vs real auth
 * - Runtime detection for desktop vs web
 *
 * USAGE:
 * ✅ import { useAuth0 } from '@/components/auth/Auth0Provider';
 * ✅ import { useAuth } from '@aurity-standalone/hooks/useAuth';
 * ❌ import { useAuth0 } from '@auth0/auth0-react';  // WRONG!
 */
export function useAuth0() {
  // For mock auth, always use mock hook
  if (USE_MOCK_AUTH) {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    return useMockAuth0();
  }

  // For desktop builds, check if we're in Tauri
  if (DESKTOP_AUTH_POSSIBLE) {
    if (isTauriRuntime()) {
      // eslint-disable-next-line react-hooks/rules-of-hooks
      return useDesktopAuth0();
    }
    // Desktop build outside Tauri - return blocked state
    return {
      isAuthenticated: false,
      isLoading: false,
      user: undefined,
      error: new Error('Desktop build requires Tauri runtime'),
      loginWithRedirect: async () => {
        console.error('[Auth0] Cannot login: Desktop build requires Tauri');
      },
      logout: async () => {},
      getAccessTokenSilently: async () => {
        throw new Error('Desktop build requires Tauri runtime');
      },
    };
  }

  // Default to Auth0 SDK for web
  // eslint-disable-next-line react-hooks/rules-of-hooks
  return useAuth0SDK();
}
