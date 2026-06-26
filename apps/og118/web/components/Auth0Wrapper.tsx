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
import { Og118IdentityProvider } from '@/lib/og118Identity';

const DOMAIN = process.env.NEXT_PUBLIC_AUTH0_DOMAIN ?? '';
const CLIENT_ID = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID ?? '';
const AUDIENCE = process.env.NEXT_PUBLIC_AUTH0_AUDIENCE ?? '';

function TokenSync({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, getAccessTokenSilently, user } = useAuth0();
  useEffect(() => {
    if (!isAuthenticated) {
      clearToken();
      return;
    }
    let cancelled = false;
    const sync = async () => {
      try {
        const token = await getAccessTokenSilently({
          authorizationParams: { audience: AUDIENCE },
        });
        if (!cancelled) setToken(token);
      } catch (err) {
        // The login gate (isAuthenticated/id_token) stays true even when the
        // API access-token fetch fails (consent/audience/scope), so a silent
        // catch leaves the app loaded but every API call 401s with no signal.
        // Surface it: clear the stale token AND log the real cause.
        if (!cancelled) clearToken();
        console.error('[og118] Auth0 access-token sync failed:', err);
      }
    };
    void sync();
    const id = setInterval(() => void sync(), 5 * 60 * 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [isAuthenticated, getAccessTokenSilently]);
  // The account id (sub) scopes every local-first store (conversations, audio
  // queue, projects), so accounts that share a browser never see each other's
  // data. Null until authenticated.
  const userId = isAuthenticated ? user?.sub ?? null : null;
  return <Og118IdentityProvider value={{ userId }}>{children}</Og118IdentityProvider>;
}

export function Auth0Wrapper({ children }: { children: React.ReactNode }) {
  if (!isAuth0Mode) {
    return <Og118IdentityProvider value={{ userId: null }}>{children}</Og118IdentityProvider>;
  }
  const redirectUri = typeof window !== 'undefined' ? window.location.origin : undefined;
  return (
    <Auth0Provider
      domain={DOMAIN}
      clientId={CLIENT_ID}
      authorizationParams={{
        redirect_uri: redirectUri,
        audience: AUDIENCE,
        scope: 'openid profile email offline_access',
      }}
      cacheLocation="localstorage"
      useRefreshTokens
    >
      <TokenSync>{children}</TokenSync>
    </Auth0Provider>
  );
}
