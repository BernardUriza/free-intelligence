import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

import { useOg118ProjectUpload } from '../useOg118ProjectUpload';

// The backend ingests UTF-8 text synchronously and returns {corpus_id, doc_id,
// chunks}. These assert the consumer transport: validation, the multipart POST
// to the right URL with the auth header, the success → indexed path, and a
// backend 4xx surfaced as a human message.

function textFile(name = 'inventario.txt', body = 'lápices 100\nplumas 50') {
  return new File([body], name, { type: 'text/plain' });
}

let lastUrl = '';
let lastInit: RequestInit | null = null;

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem('og118_access_token', 'tok-123');
  lastUrl = '';
  lastInit = null;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useOg118ProjectUpload', () => {
  it('starts idle (no file, selecting status)', () => {
    const { result } = renderHook(() => useOg118ProjectUpload());
    expect(result.current.file).toBeNull();
    expect(result.current.status).toBe('selecting');
    expect(result.current.isActive).toBe(false);
  });

  it('rejects a non-text file client-side without hitting the network', async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const { result } = renderHook(() => useOg118ProjectUpload());
    const pdf = new File([new Uint8Array([0x25, 0x50, 0x44, 0x46])], 'doc.pdf', {
      type: 'application/pdf',
    });

    await act(async () => {
      await result.current.uploadFile('proj-1', pdf);
    });

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.status).toBe('error');
    expect(result.current.error).toMatch(/solo archivos de texto/i);
  });

  it('uploads a text file as multipart to the project corpus with the auth header', async () => {
    vi.stubGlobal('fetch', async (url: string, init: RequestInit) => {
      lastUrl = url;
      lastInit = init;
      return {
        ok: true,
        json: async () => ({ corpus_id: 'proj-1', doc_id: 'inventario.txt', chunks: 3 }),
      } as Response;
    });

    const { result } = renderHook(() => useOg118ProjectUpload());
    await act(async () => {
      await result.current.uploadFile('proj-1', textFile());
    });

    await waitFor(() => expect(result.current.status).toBe('indexed'));
    expect(lastUrl).toBe('http://localhost:8118/projects/proj-1/upload');
    expect(lastInit?.method).toBe('POST');
    expect((lastInit?.headers as Record<string, string>).Authorization).toBe('Bearer tok-123');
    expect(lastInit?.body).toBeInstanceOf(FormData);
    expect((lastInit?.body as FormData).get('file')).toBeInstanceOf(File);
    expect(result.current.progress).toBe(100);
    expect(result.current.result).toEqual({
      corpusId: 'proj-1',
      docId: 'inventario.txt',
      chunks: 3,
    });
  });

  it('surfaces the backend error detail message on a 4xx', async () => {
    vi.stubGlobal('fetch', async () => {
      return {
        ok: false,
        json: async () => ({ detail: { code: 'NOT_TEXT', message: 'file is not UTF-8 text' } }),
      } as Response;
    });

    const { result } = renderHook(() => useOg118ProjectUpload());
    await act(async () => {
      await result.current.uploadFile('proj-1', textFile());
    });

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.error).toBe('file is not UTF-8 text');
    expect(result.current.result).toBeNull();
  });

  it('cancel clears the preview back to idle', async () => {
    vi.stubGlobal('fetch', async () => {
      return {
        ok: true,
        json: async () => ({ corpus_id: 'proj-1', doc_id: 'x.txt', chunks: 1 }),
      } as Response;
    });

    const { result } = renderHook(() => useOg118ProjectUpload());
    await act(async () => {
      await result.current.uploadFile('proj-1', textFile());
    });
    expect(result.current.isActive).toBe(true);

    act(() => result.current.cancel());
    expect(result.current.file).toBeNull();
    expect(result.current.status).toBe('selecting');
    expect(result.current.isActive).toBe(false);
  });
});
