'use client';

/**
 * Auth0Wrapper — wraps the app in Auth0's SPA provider (PKCE) ONLY in auth0 mode;
 * a pure passthrough in bearer mode so staging is untouched until the cutover.
 *
 * The key design move: it keeps `og118Token.authHeaders()` SYNCHRONOUS. Instead
 * of rewriting every fetch call site to await an async token, a small TokenSync
 * child mirrors the Auth0 access token into localStorage (the same key the bearer
 * path already reads), refreshing it on auth changes + on an interval. So
 * useOg118Agent / useOg118Projects / the voice adapter need zero changes.
 */

import { Auth0Provider, useAuth0 } from '@auth0/auth0-react';
import { useEffect } from 'react';

import { isAuth0Mode } from '@/lib/authMode';
import { clearToken, setToken } from '@/lib/og118Token';

const DOMAIN = process.env.NEXT_PUBLIC_AUTH0_DOMAIN ?? '';
const CLIENT_ID = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID ?? '';
const AUDIENCE = process.env.NEXT_PUBLIC_AUTH0_AUDIENCE ?? '';

function TokenSync({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, getAccessTokenSilently } = useAuth0();
  useEffect(() => {
    if (!isAuthenticated) {
      clearToken();
      return;
    }
    let cancelled = false;
    const sync = async () => {
      try {
        const token = await getAccessTokenSilently();
        if (!cancelled) setToken(token);
      } catch {
        // Silent refresh failed (session gone) — AuthGate re-prompts login.
      }
    };
    void sync();
    const id = setInterval(() => void sync(), 5 * 60 * 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [isAuthenticated, getAccessTokenSilently]);
  return <>{children}</>;
}

export function Auth0Wrapper({ children }: { children: React.ReactNode }) {
  if (!isAuth0Mode) return <>{children}</>;
  const redirectUri = typeof window !== 'undefined' ? window.location.origin : undefined;
  return (
    <Auth0Provider
      domain={DOMAIN}
      clientId={CLIENT_ID}
      authorizationParams={{ redirect_uri: redirectUri, audience: AUDIENCE }}
      cacheLocation="localstorage"
      useRefreshTokens
    >
      <TokenSync>{children}</TokenSync>
    </Auth0Provider>
  );
}
