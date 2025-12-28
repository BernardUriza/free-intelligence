/**
 * useMediaQuery test suite
 *
 * Tests:
 * 1. SSR returns ssrMatch without window
 * 2. Initial snapshot reflects MQL.matches
 * 3. Change events trigger re-render
 * 4. Cleanup removes event listener
 * 5. Cache shares MediaQueryList instances
 * 6. RAF batches updates
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useMediaQuery,
  useBreakpoints,
  clearMediaQueryCache,
} from '../useMediaQuery';

/**
 * Mock matchMedia API with listener tracking
 */
interface MockMQL {
  media: string;
  matches: boolean;
  listeners: Set<(evt: { matches: boolean }) => void>;
  addEventListener: (type: string, cb: any) => void;
  removeEventListener: (type: string, cb: any) => void;
  addListener?: (cb: any) => void;
  removeListener?: (cb: any) => void;
  // Test helpers
  triggerChange: (matches: boolean) => void;
}

function setupMatchMedia(initialMatches = false) {
  const mqls = new Map<string, MockMQL>();

  const matchMedia = vi.fn((query: string): MockMQL => {
    // Return cached MQL if exists
    if (mqls.has(query)) {
      return mqls.get(query)!;
    }

    const listeners = new Set<(evt: { matches: boolean }) => void>();

    const mql: MockMQL = {
      media: query,
      matches: initialMatches,
      listeners,

      addEventListener(type: string, cb: any) {
        if (type === 'change') {
          listeners.add(cb);
        }
      },

      removeEventListener(type: string, cb: any) {
        if (type === 'change') {
          listeners.delete(cb);
        }
      },

      // Legacy API
      addListener(cb: any) {
        listeners.add(cb);
      },

      removeListener(cb: any) {
        listeners.delete(cb);
      },

      // Test helper to trigger change
      triggerChange(matches: boolean) {
        this.matches = matches;
        const event = { matches };
        listeners.forEach((cb) => cb(event));
      },
    };

    mqls.set(query, mql);
    return mql;
  });

  (global as any).window = { matchMedia };

  return {
    matchMedia,
    mqls,
    getMql: (query: string) => mqls.get(query),
  };
}

describe('useMediaQuery', () => {
  let mockApi: ReturnType<typeof setupMatchMedia>;

  beforeEach(() => {
    clearMediaQueryCache();
    mockApi = setupMatchMedia(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMediaQueryCache();
  });

  describe('SSR behavior', () => {
    it('returns ssrMatch when window is undefined', () => {
      const originalWindow = global.window;
      // @ts-ignore - deliberately delete window
      delete (global as any).window;

      const { result } = renderHook(() =>
        useMediaQuery('(min-width: 1024px)', { ssrMatch: true })
      );

      expect(result.current).toBe(true);

      // Restore window
      (global as any).window = originalWindow;
    });

    it('returns false by default on server', () => {
      const originalWindow = global.window;
      // @ts-ignore
      delete (global as any).window;

      const { result } = renderHook(() =>
        useMediaQuery('(min-width: 1024px)')
      );

      expect(result.current).toBe(false);

      (global as any).window = originalWindow;
    });
  });

  describe('Client-side matching', () => {
    it('returns initial matches state', () => {
      mockApi = setupMatchMedia(true);

      const { result } = renderHook(() =>
        useMediaQuery('(min-width: 1024px)')
      );

      expect(result.current).toBe(true);
    });

    it('returns false when query does not match', () => {
      mockApi = setupMatchMedia(false);

      const { result } = renderHook(() =>
        useMediaQuery('(max-width: 639.98px)')
      );

      expect(result.current).toBe(false);
    });
  });

  describe('Reactive updates', () => {
    it('updates when MediaQueryList changes', async () => {
      const query = '(min-width: 1024px)';
      const { result } = renderHook(() => useMediaQuery(query));

      expect(result.current).toBe(false);

      // Trigger change
      act(() => {
        mockApi.getMql(query)?.triggerChange(true);
      });

      await waitFor(() => {
        expect(result.current).toBe(true);
      });
    });

    it('handles multiple changes', async () => {
      const query = '(max-width: 639.98px)';
      const { result } = renderHook(() => useMediaQuery(query));

      expect(result.current).toBe(false);

      // First change
      act(() => {
        mockApi.getMql(query)?.triggerChange(true);
      });

      await waitFor(() => {
        expect(result.current).toBe(true);
      });

      // Second change
      act(() => {
        mockApi.getMql(query)?.triggerChange(false);
      });

      await waitFor(() => {
        expect(result.current).toBe(false);
      });
    });
  });

  describe('Cleanup', () => {
    it('removes event listener on unmount', () => {
      const query = '(min-width: 1024px)';
      const { unmount } = renderHook(() => useMediaQuery(query));

      const mql = mockApi.getMql(query);
      expect(mql).toBeDefined();
      expect(mql!.listeners.size).toBe(1);

      unmount();

      expect(mql!.listeners.size).toBe(0);
    });

    it('cancels pending RAF on unmount', () => {
      const cancelSpy = vi.spyOn(global, 'cancelAnimationFrame');
      const query = '(min-width: 1024px)';

      const { unmount } = renderHook(() =>
        useMediaQuery(query, { useRaf: true })
      );

      unmount();

      // cancelAnimationFrame should be called during cleanup
      expect(cancelSpy).toHaveBeenCalled();
    });
  });

  describe('Caching', () => {
    it('reuses MediaQueryList for same query', () => {
      const query = '(min-width: 1024px)';

      const { result: _result1 } = renderHook(() => useMediaQuery(query));
      const { result: _result2 } = renderHook(() => useMediaQuery(query));

      // Should use same MQL instance
      expect(mockApi.matchMedia).toHaveBeenCalledTimes(1);

      // Both hooks share listeners on same MQL
      const mql = mockApi.getMql(query);
      expect(mql!.listeners.size).toBe(2);
    });

    it('creates new MediaQueryList when cache disabled', () => {
      const query = '(min-width: 1024px)';

      renderHook(() => useMediaQuery(query, { cache: false }));
      renderHook(() => useMediaQuery(query, { cache: false }));

      // Should create MQL twice (cache disabled)
      expect(mockApi.matchMedia).toHaveBeenCalledTimes(2);
    });

    it('clears cache with clearMediaQueryCache', () => {
      const query = '(min-width: 1024px)';

      renderHook(() => useMediaQuery(query));
      expect(mockApi.matchMedia).toHaveBeenCalledTimes(1);

      clearMediaQueryCache();

      renderHook(() => useMediaQuery(query));
      expect(mockApi.matchMedia).toHaveBeenCalledTimes(2);
    });
  });

  describe('RAF optimization', () => {
    it('batches updates with requestAnimationFrame when enabled', async () => {
      const rafSpy = vi.spyOn(global, 'requestAnimationFrame');
      const query = '(min-width: 1024px)';

      const { result: _result } = renderHook(() =>
        useMediaQuery(query, { useRaf: true })
      );

      act(() => {
        mockApi.getMql(query)?.triggerChange(true);
      });

      await waitFor(() => {
        expect(rafSpy).toHaveBeenCalled();
      });
    });

    it('updates immediately when RAF disabled', async () => {
      const rafSpy = vi.spyOn(global, 'requestAnimationFrame');
      const query = '(min-width: 1024px)';

      const { result } = renderHook(() =>
        useMediaQuery(query, { useRaf: false })
      );

      act(() => {
        mockApi.getMql(query)?.triggerChange(true);
      });

      // Should NOT use RAF
      expect(rafSpy).not.toHaveBeenCalled();

      await waitFor(() => {
        expect(result.current).toBe(true);
      });
    });
  });

  describe('Legacy API fallback', () => {
    it('uses addListener when addEventListener unavailable', () => {
      const query = '(min-width: 1024px)';

      // Remove modern API
      const mql = mockApi.matchMedia(query);
      delete (mql as any).addEventListener;
      delete (mql as any).removeEventListener;

      const { unmount } = renderHook(() => useMediaQuery(query));

      // Should have used addListener
      expect(mql.listeners.size).toBe(1);

      unmount();

      // Should have used removeListener
      expect(mql.listeners.size).toBe(0);
    });
  });
});

describe('useBreakpoints', () => {
  let mockApi: ReturnType<typeof setupMatchMedia>;

  const BREAKPOINTS = {
    mobile: '(max-width: 639.98px)',
    tablet: '(min-width: 640px) and (max-width: 1023.98px)',
    desktop: '(min-width: 1024px)',
  };

  beforeEach(() => {
    clearMediaQueryCache();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMediaQueryCache();
  });

  it('returns all breakpoint flags', () => {
    mockApi = setupMatchMedia(false);

    const { result } = renderHook(() => useBreakpoints(BREAKPOINTS));

    expect(result.current).toEqual({
      isMobile: false,
      isTablet: false,
      isDesktop: false,
    });
  });

  it('detects mobile breakpoint', () => {
    mockApi = setupMatchMedia(false);

    const { result } = renderHook(() => useBreakpoints(BREAKPOINTS));

    act(() => {
      mockApi.getMql(BREAKPOINTS.mobile)?.triggerChange(true);
    });

    expect(result.current.isMobile).toBe(true);
  });

  it('detects tablet breakpoint', () => {
    mockApi = setupMatchMedia(false);

    const { result } = renderHook(() => useBreakpoints(BREAKPOINTS));

    act(() => {
      mockApi.getMql(BREAKPOINTS.tablet)?.triggerChange(true);
    });

    expect(result.current.isTablet).toBe(true);
  });

  it('detects desktop breakpoint', () => {
    mockApi = setupMatchMedia(false);

    const { result } = renderHook(() => useBreakpoints(BREAKPOINTS));

    act(() => {
      mockApi.getMql(BREAKPOINTS.desktop)?.triggerChange(true);
    });

    expect(result.current.isDesktop).toBe(true);
  });

  it('respects ssrMatch option', () => {
    const originalWindow = global.window;
    // @ts-ignore
    delete (global as any).window;

    const { result } = renderHook(() =>
      useBreakpoints(BREAKPOINTS, { ssrMatch: true })
    );

    // All should be true on server when ssrMatch is true
    expect(result.current.isMobile).toBe(true);
    expect(result.current.isTablet).toBe(true);
    expect(result.current.isDesktop).toBe(true);

    (global as any).window = originalWindow;
  });
});
