/**
 * fi-glass · useMediaQuery — pure, tearing-free media-query subscription.
 *
 * Copied verbatim from aurity's `hooks/useMediaQuery.ts` (it had zero domain
 * coupling — only React). The shell's responsive container consumes it so
 * fi-glass never reaches back into the app for breakpoint state.
 *
 * - useSyncExternalStore for concurrent-safe reads
 * - SSR-safe (configurable server snapshot)
 * - global MediaQueryList cache shared across components
 * - RAF-debounced notifications
 * - legacy addListener/removeListener fallback
 */

import { useSyncExternalStore } from 'react';

const mqlCache = new Map<string, MediaQueryList>();

function getMql(query: string, useCache = true): MediaQueryList | null {
  if (typeof window === 'undefined' || !('matchMedia' in window)) {
    return null;
  }
  if (useCache) {
    const cached = mqlCache.get(query);
    if (cached) return cached;
  }
  const mql = window.matchMedia(query);
  if (useCache) {
    mqlCache.set(query, mql);
  }
  return mql;
}

export interface UseMediaQueryOptions {
  ssrMatch?: boolean;
  useRaf?: boolean;
  cache?: boolean;
}

export function useMediaQuery(query: string, options?: UseMediaQueryOptions): boolean {
  const ssrMatch = options?.ssrMatch ?? false;
  const useRaf = options?.useRaf ?? true;
  const cache = options?.cache ?? true;

  const mql = getMql(query, cache);

  const getSnapshot = (): boolean => (mql ? mql.matches : ssrMatch);
  const getServerSnapshot = (): boolean => ssrMatch;

  const subscribe = (onStoreChange: () => void): (() => void) => {
    if (!mql) return () => {};

    let rafId = 0;
    const handler = (): void => {
      if (!useRaf) {
        onStoreChange();
        return;
      }
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => onStoreChange());
    };

    const mqlAny = mql as unknown as {
      addEventListener?: (t: string, h: () => void) => void;
      removeEventListener?: (t: string, h: () => void) => void;
      addListener?: (h: () => void) => void;
      removeListener?: (h: () => void) => void;
    };

    if (typeof mqlAny.addEventListener === 'function') {
      mqlAny.addEventListener('change', handler);
    } else if (typeof mqlAny.addListener === 'function') {
      mqlAny.addListener(handler);
    }

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      if (typeof mqlAny.removeEventListener === 'function') {
        mqlAny.removeEventListener('change', handler);
      } else if (typeof mqlAny.removeListener === 'function') {
        mqlAny.removeListener(handler);
      }
    };
  };

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

export interface Breakpoints {
  mobile: string;
  tablet: string;
  desktop: string;
}

export interface BreakpointMatches {
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
}

export function useBreakpoints(
  breakpoints: Breakpoints,
  options?: Pick<UseMediaQueryOptions, 'ssrMatch'>
): BreakpointMatches {
  const isMobile = useMediaQuery(breakpoints.mobile, { ssrMatch: options?.ssrMatch });
  const isTablet = useMediaQuery(breakpoints.tablet, { ssrMatch: options?.ssrMatch });
  const isDesktop = useMediaQuery(breakpoints.desktop, { ssrMatch: options?.ssrMatch });
  return { isMobile, isTablet, isDesktop };
}

export function clearMediaQueryCache(): void {
  mqlCache.clear();
}
