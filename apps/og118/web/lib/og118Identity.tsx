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
}

const Og118IdentityContext = createContext<Og118Identity>({ userId: null });

export const Og118IdentityProvider = Og118IdentityContext.Provider;

export function useOg118Identity(): Og118Identity {
  return useContext(Og118IdentityContext);
}
