'use client';

/**
 * Auth0Provider Component
 * HIPAA Card: G-003 - Auth0 OAuth2/OIDC Integration
 *
 * SECURITY (2025-12-28):
 * Only two authentication modes are supported:
 * 1. DESKTOP - Uses DesktopAuth0Provider with PKCE + OS Keychain
 * 2. CLOUD - Uses Auth0 SDK with standard web flow
 *
 * NO MOCK AUTH - Mock authentication has been removed for security.
 * All builds require real Auth0 authentication.
 *
 * Components MUST import useAuth0 from this module (or @/hooks/useAuth)
 * rather than directly from @auth0/auth0-react to ensure compatibility.
 */

import { Auth0Provider as Auth0ProviderSDK, useAuth0 as useAuth0SDK } from '@auth0/auth0-react';
import { ReactNode, ReactElement, useEffect, useState } from 'react';
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
 * Check if this is a desktop build (set at build time)
 */
const IS_DESKTOP_BUILD = process.env.NEXT_PUBLIC_DEPLOYMENT_TARGET === 'desktop';

// Development-only logging utility
const devLog = (message: string, ...args: unknown[]) => {
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

  // DESKTOP MODE: Use DesktopAuth0Provider with PKCE + Keychain
  if (IS_DESKTOP_BUILD) {
    // During SSR or before hydration, render children without auth
    if (!isHydrated) {
      return <>{children}</>;
    }

    // After hydration, if we're in Tauri, use desktop auth
    if (isTauri) {
      devLog('[Auth0Provider] Using DesktopAuth0Provider (Tauri detected)');
      return <DesktopAuth0Provider>{children}</DesktopAuth0Provider>;
    }

    // SECURITY: Block desktop builds running outside Tauri
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

  // CLOUD MODE: Use standard Auth0 SDK
  const domain = process.env.NEXT_PUBLIC_AUTH0_DOMAIN;
  const clientId = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID;

  if (!domain || !clientId) {
    throw new Error(
      'Auth0 configuration missing. Required: NEXT_PUBLIC_AUTH0_DOMAIN, NEXT_PUBLIC_AUTH0_CLIENT_ID'
    );
  }

  const audience = process.env.NEXT_PUBLIC_AUTH0_AUDIENCE;

  if (!audience) {
    console.error(
      '[Auth0Provider] NEXT_PUBLIC_AUTH0_AUDIENCE is not set. ' +
        'This is required for proper token audience validation.'
    );
  }

  // Build-time redirect URI
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

  devLog('[Auth0Provider] Using Auth0 SDK (cloud mode)');
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
 * Two modes only:
 * - Desktop (Tauri): Uses DesktopAuth0Provider with PKCE
 * - Cloud (Web): Uses Auth0 SDK
 *
 * USAGE:
 * ✅ import { useAuth0 } from '@/components/auth/Auth0Provider';
 * ✅ import { useAuth } from '@/hooks/useAuth';
 * ❌ import { useAuth0 } from '@auth0/auth0-react';  // WRONG!
 */
export function useAuth0() {
  // Desktop mode with Tauri runtime
  if (IS_DESKTOP_BUILD && isTauriRuntime()) {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    return useDesktopAuth0();
  }

  // Desktop build outside Tauri - return blocked state
  if (IS_DESKTOP_BUILD) {
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

  // Cloud mode - use Auth0 SDK
  // eslint-disable-next-line react-hooks/rules-of-hooks
  return useAuth0SDK();
}
