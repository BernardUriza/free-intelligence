// @vitest-environment jsdom
/**
 * OG118-IMAGE-UPLOAD-1 — the transport forwards attached images to
 * /chat/stream in the server's ChatImage shape ({media_type, data}), allows an
 * image-only send, and keeps the truly-empty send a no-op. History stays
 * role/content only (prior images are never re-uploaded).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useOg118Agent } from '../useOg118Agent';

const IMAGES = [{ mediaType: 'image/jpeg', data: 'aGk=' }];

function emptyStreamResponse() {
  return {
    status: 200,
    body: {
      getReader: () => ({
        read: async () => ({ value: undefined, done: true as const }),
      }),
    },
  };
}

describe('useOg118Agent — image sends', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(emptyStreamResponse());
    vi.stubGlobal('fetch', fetchMock);
  });

  it('forwards images in the ChatImage wire shape', async () => {
    const { result } = renderHook(() => useOg118Agent('conv-1'));
    await act(() => result.current.send('¿qué es esto?', { images: IMAGES }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.images).toEqual([{ media_type: 'image/jpeg', data: 'aGk=' }]);
    expect(body.message).toBe('¿qué es esto?');
  });

  it('allows an image-only send (empty text)', async () => {
    const { result } = renderHook(() => useOg118Agent('conv-1'));
    await act(() => result.current.send('', { images: IMAGES }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.message).toBe('');
    expect(body.images).toHaveLength(1);
  });

  it('keeps the truly empty send a no-op', async () => {
    const { result } = renderHook(() => useOg118Agent('conv-1'));
    await act(() => result.current.send('   ', { images: [] }));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('omits the images key on text-only sends and never re-uploads history images', async () => {
    const { result } = renderHook(() => useOg118Agent('conv-1'));
    await act(() =>
      result.current.send('hola', {
        history: [
          {
            role: 'user',
            content: 'mira',
            timestamp: '2026-01-01T00:00:00Z',
            images: IMAGES,
          },
        ],
      }),
    );
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect('images' in body).toBe(false);
    expect(body.history).toEqual([{ role: 'user', content: 'mira' }]);
  });
});
