'use client';

/**
 * og118 access token — read at RUNTIME from localStorage, never baked into the
 * static bundle. Gate decision (Gate 1): NO NEXT_PUBLIC_OG118_TOKEN; the user
 * pastes the token into the running app and it lives only in their browser.
 *
 * SECURITY NOTE: this is a single-user speed-bump, not real auth. A token in the
 * browser is visible to that browser's owner and to anyone with XSS on the page.
 * Stable production still needs a network/identity gate (Azure auth, IP allow).
 */

const KEY = 'og118_access_token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(KEY, token.trim());
  } catch {
    /* private mode / storage disabled — token just won't persist */
  }
}

export function clearToken(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

/** Authorization header, present only when a token is configured. */
export function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

/** Sentinel an SSE hook emits as its error message on HTTP 401. */
export const AUTH401 = 'AUTH401';
