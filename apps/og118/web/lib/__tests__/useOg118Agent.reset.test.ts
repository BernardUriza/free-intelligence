// @vitest-environment jsdom
/**
 * reset() drops the live turn — including a request still streaming. Left
 * alive, that stream kept painting its answer over whatever thread the
 * conversation layer had just opened.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useOg118Agent } from '../useOg118Agent';

describe('useOg118Agent — reset', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(
      (_url: string, init: { signal: AbortSignal }) =>
        new Promise((_resolve, reject) => {
          init.signal.addEventListener('abort', () =>
            reject(new DOMException('aborted', 'AbortError')),
          );
        }),
    );
    vi.stubGlobal('fetch', fetchMock);
  });

  it('aborts the in-flight request and leaves streaming', async () => {
    const { result } = renderHook(() => useOg118Agent('conv-1'));
    let sending: Promise<void> = Promise.resolve();
    act(() => {
      sending = result.current.send('hola');
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(true));
    const signal: AbortSignal = fetchMock.mock.calls[0][1].signal;

    await act(async () => {
      result.current.reset?.();
      await sending;
    });

    expect(signal.aborted).toBe(true);
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.turn.status).not.toBe('error');
  });
});
