'use client';

/**
 * og118 identity context — the signed-in account id (Auth0 `sub`), available to
 * the whole app in BOTH auth modes so local-first stores can partition by it.
 *
 * In auth0 mode Auth0Wrapper fills it from the Auth0 user; in bearer / legacy
 * single-tenant mode it stays null (one shared partition, the original behavior).
 * Components read `useOg118Identity().userId` and pass it to the identity-scoped
 * store hooks (conversations, audio queue, projects) — that is what stops two
 * accounts on the same browser from seeing each other's data.
 */

import { createContext, useContext } from 'react';

export interface Og118Identity {
  /** The signed-in account id (Auth0 principal `sub`), or null when unauthenticated. */
  userId: string | null;
  /**
   * True once an Authorization token is available for API calls. In auth0 mode it
   * flips true only after TokenSync has mirrored the Auth0 access token into
   * storage — so an auth-gated mount fetch (GET /projects) waits for it instead of
   * racing the async token sync and 401-ing. Always true in bearer mode (the
   * legacy token, if any, is read synchronously).
   */
  tokenReady: boolean;
  /**
   * True when the token sync FAILED (refresh token expired/revoked): the user
   * still looks signed in (the id session is valid) but every API call 401s.
   * Distinguishes "syncing" (tokenReady false, transient) from "needs
   * re-login", so the UI says so instead of silently falling back to local
   * data — the session-zombie fake-green.
   */
  tokenFailed: boolean;
}

const Og118IdentityContext = createContext<Og118Identity>({
  userId: null,
  tokenReady: true,
  tokenFailed: false,
});

export const Og118IdentityProvider = Og118IdentityContext.Provider;

export function useOg118Identity(): Og118Identity {
  return useContext(Og118IdentityContext);
}
