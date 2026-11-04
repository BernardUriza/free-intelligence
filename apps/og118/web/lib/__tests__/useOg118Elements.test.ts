import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

import { useOg118Elements } from '../useOg118Elements';
import { setToken } from '../og118Token';

// 2026-10-28, app.og118.ai: /elements/slots went out before Auth0 had stored the
// token, got a 401, and "Nuevo elemento" never showed for its own author.
let slotCalls: (string | undefined)[];

beforeEach(() => {
  localStorage.clear();
  slotCalls = [];
  vi.stubGlobal('fetch', async (url: string, init: RequestInit = {}) => {
    const auth = (init.headers as Record<string, string> | undefined)?.Authorization;
    if (url.endsWith('/elements/slots')) {
      slotCalls.push(auth);
      const ok = Boolean(auth);
      return {
        ok,
        json: async () => (ok ? { canCreate: true, slots: [{ atomicNumber: 86, symbol: 'Rn', slug: 'radon', displayName: 'Radón' }] } : {}),
      } as Response;
    }
    return { ok: true, json: async () => ({ elements: [] }) } as Response;
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useOg118Elements slots', () => {
  it('waits for the token, then asks with the bearer', async () => {
    const { result, rerender } = renderHook(({ ready }) => useOg118Elements('auth0|bernard', ready), {
      initialProps: { ready: false },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(slotCalls).toEqual([]);
    expect(result.current.canCreate).toBe(false);

    setToken('tok-1');
    rerender({ ready: true });
    await waitFor(() => expect(result.current.canCreate).toBe(true));
    expect(slotCalls).toEqual(['Bearer tok-1']);
    expect(result.current.slots.map((s) => s.atomicNumber)).toEqual([86]);
  });
});
