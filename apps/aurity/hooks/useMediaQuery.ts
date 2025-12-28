/**
 * useMediaQuery — Production-grade React hook (2026)
 *
 * Features:
 * - useSyncExternalStore for tearing-free concurrent rendering
 * - SSR-safe with configurable server snapshot
 * - Global MediaQueryList cache to share instances across components
 * - RAF-debounced notifications to batch visual updates
 * - Legacy fallback for addListener/removeListener
 *
 * @example
 * ```tsx
 * const isMobile = useMediaQuery('(max-width: 639.98px)', { ssrMatch: false });
 * const { isMobile, isTablet, isDesktop } = useBreakpoints(BREAKPOINTS);
 * ```
 */

import { useSyncExternalStore } from 'react';

// Global cache: one MediaQueryList per unique query string
const mqlCache = new Map<string, MediaQueryList>();

/**
 * Get or create a cached MediaQueryList
 * @internal
 */
function getMql(query: string, useCache = true): MediaQueryList | null {
  // SSR guard: matchMedia doesn't exist on server
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
  /**
   * Value to return during SSR (server-side rendering)
   * Prevents hydration mismatches by providing consistent server snapshot
   * @default false
   */
  ssrMatch?: boolean;

  /**
   * Wrap change notifications in requestAnimationFrame
   * Batches updates with browser paint cycle for smoother UI
   * @default true
   */
  useRaf?: boolean;

  /**
   * Use global MediaQueryList cache
   * Shares MQL instances across components for same query
   * @default true
   */
  cache?: boolean;
}

/**
 * Subscribe to a CSS media query with automatic cleanup
 *
 * @param query - CSS media query string (e.g., '(min-width: 1024px)')
 * @param options - Configuration options
 * @returns Current match state (true if query matches, false otherwise)
 */
export function useMediaQuery(
  query: string,
  options?: UseMediaQueryOptions
): boolean {
  const ssrMatch = options?.ssrMatch ?? false;
  const useRaf = options?.useRaf ?? true;
  const cache = options?.cache ?? true;

  // Get MediaQueryList (null during SSR)
  const mql = getMql(query, cache);

  // Snapshot functions for useSyncExternalStore
  const getSnapshot = (): boolean => {
    return mql ? mql.matches : ssrMatch;
  };

  const getServerSnapshot = (): boolean => {
    return ssrMatch;
  };

  // Subscribe to MediaQueryList changes
  const subscribe = (onStoreChange: () => void): (() => void) => {
    if (!mql) {
      // No-op unsubscribe for SSR
      return () => {};
    }

    let rafId = 0;

    // Change handler with optional RAF batching
    const handler = (): void => {
      if (!useRaf) {
        onStoreChange();
        return;
      }

      // Cancel pending RAF before scheduling new one
      if (rafId) {
        cancelAnimationFrame(rafId);
      }

      rafId = requestAnimationFrame(() => {
        onStoreChange();
      });
    };

    // Modern API (addEventListener) vs legacy (addListener)
    // TypeScript doesn't know about addListener, so we use type assertion
    const mqlAny = mql as any;

    if (typeof mqlAny.addEventListener === 'function') {
      mqlAny.addEventListener('change', handler);
    } else if (typeof mqlAny.addListener === 'function') {
      // Safari < 14, legacy browsers
      mqlAny.addListener(handler);
    }

    // Cleanup function
    return () => {
      if (rafId) {
        cancelAnimationFrame(rafId);
      }

      if (typeof mqlAny.removeEventListener === 'function') {
        mqlAny.removeEventListener('change', handler);
      } else if (typeof mqlAny.removeListener === 'function') {
        mqlAny.removeListener(handler);
      }
    };
  };

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/**
 * Standard breakpoint definitions
 */
export interface Breakpoints {
  mobile: string;
  tablet: string;
  desktop: string;
}

/**
 * Breakpoint match results
 */
export interface BreakpointMatches {
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
}

/**
 * Hook for common mobile-first breakpoints
 *
 * @param breakpoints - Object with mobile/tablet/desktop media queries
 * @param options - UseMediaQuery options (applies to all queries)
 * @returns Object with isMobile, isTablet, isDesktop flags
 *
 * @example
 * ```tsx
 * const BREAKPOINTS = {
 *   mobile: '(max-width: 639.98px)',
 *   tablet: '(min-width: 640px) and (max-width: 1023.98px)',
 *   desktop: '(min-width: 1024px)'
 * };
 *
 * function MyComponent() {
 *   const { isMobile, isTablet, isDesktop } = useBreakpoints(BREAKPOINTS);
 *
 *   if (isMobile) return <MobileView />;
 *   if (isTablet) return <TabletView />;
 *   return <DesktopView />;
 * }
 * ```
 */
export function useBreakpoints(
  breakpoints: Breakpoints,
  options?: Pick<UseMediaQueryOptions, 'ssrMatch'>
): BreakpointMatches {
  const isMobile = useMediaQuery(breakpoints.mobile, {
    ssrMatch: options?.ssrMatch,
  });

  const isTablet = useMediaQuery(breakpoints.tablet, {
    ssrMatch: options?.ssrMatch,
  });

  const isDesktop = useMediaQuery(breakpoints.desktop, {
    ssrMatch: options?.ssrMatch,
  });

  return { isMobile, isTablet, isDesktop };
}

/**
 * Clear the MediaQueryList cache
 * Useful for testing or memory management
 * @internal
 */
export function clearMediaQueryCache(): void {
  mqlCache.clear();
}
