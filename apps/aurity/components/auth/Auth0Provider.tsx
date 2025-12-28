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
 * Components MUST import useAuth0 from this module (or @/hooks/useAuth)
 * rather than directly from @auth0/auth0-react to ensure compatibility.
 */

import { Auth0Provider as Auth0ProviderSDK, useAuth0 as useAuth0SDK } from '@auth0/auth0-react';
import { ReactNode, ReactElement } from 'react';
import { MockAuth0Provider, useAuth0 as useMockAuth0 } from './MockAuth0Provider';

interface Auth0ProviderProps {
  children: ReactNode;
}

/**
 * Determine provider type at BUILD TIME (not runtime)
 * This prevents SSR/hydration mismatches
 *
 * Uses mock auth when:
 * 1. Explicitly enabled via NEXT_PUBLIC_USE_MOCK_AUTH=true
 * 2. In development mode without Auth0 config
 * 3. In production build without Auth0 config (static export scenario)
 */
const USE_MOCK_AUTH =
  process.env.NEXT_PUBLIC_USE_MOCK_AUTH === 'true' ||
  !process.env.NEXT_PUBLIC_AUTH0_DOMAIN ||
  !process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID;

// Development-only logging utility
const devLog = (message: string, ...args: any[]) => {
  if (process.env.NODE_ENV === 'development') {
    console.log(message, ...args);
  }
};

export function Auth0Provider({ children }: Auth0ProviderProps): ReactElement {
  // Decision made at build time, consistent across SSR and CSR
  if (USE_MOCK_AUTH) {
    devLog('[Auth0Provider] Using MockAuth0Provider (development mode)');
    return <MockAuth0Provider>{children}</MockAuth0Provider>;
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

  const onRedirectCallback = (appState?: any) => {
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
 * SIMPLIFIED (2025-12-03):
 * - Decision made at build time (USE_MOCK_AUTH const)
 * - No runtime conditionals = no SSR issues
 * - No global mutable state
 *
 * USAGE:
 * ✅ import { useAuth0 } from '@/components/auth/Auth0Provider';
 * ✅ import { useAuth } from '@aurity-standalone/hooks/useAuth';
 * ❌ import { useAuth0 } from '@auth0/auth0-react';  // WRONG!
 */
export function useAuth0() {
  if (USE_MOCK_AUTH) {
    return useMockAuth0();
  } else {
    return useAuth0SDK();
  }
}
