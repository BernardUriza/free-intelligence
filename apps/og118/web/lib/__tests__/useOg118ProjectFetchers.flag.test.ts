import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

import { useOg118ProjectConversations } from '../useOg118ProjectConversations';
import { useOg118ProjectDocuments } from '../useOg118ProjectDocuments';

// Los dos hooks que LEEN del API de Proyectos, en sus dos ramas.
//
// El apagado importa más que el encendido aquí: con el flag del servidor abajo,
// `GET /projects/*` es un 404 REAL (el `projects_router` nunca se monta), así que
// un hook que dispare igual pinta un error por cada mount — ruido de consola que
// parece un bug y que manda a alguien a depurar una feature apagada a propósito.
//
// Que la petición NO salga es la aserción, no que el estado quede vacío: un hook
// puede vaciar su estado y aun así haber ido a la red.

const ORIGINAL_FETCH = globalThis.fetch;

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem('og118_access_token', 'tok-123');
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  globalThis.fetch = ORIGINAL_FETCH;
});

function espiarFetch(payload: unknown) {
  const spy = vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => payload,
  }));
  vi.stubGlobal('fetch', spy);
  return spy;
}

describe('useOg118ProjectConversations', () => {
  it('APAGADO: no toca la red aunque le pasen un projectId', async () => {
    vi.stubEnv('NEXT_PUBLIC_OG118_PROYECTOS', '0');
    const spy = espiarFetch({ conversations: [] });
    const { result } = renderHook(() => useOg118ProjectConversations('project-1'));
    await waitFor(() => expect(result.current.conversations).toEqual([]));
    expect(spy).not.toHaveBeenCalled();
  });

  it('ENCENDIDO: pide las conversaciones del proyecto', async () => {
    vi.stubEnv('NEXT_PUBLIC_OG118_PROYECTOS', '1');
    const spy = espiarFetch({ conversations: [{ id: 'c1', title: 'Hola' }] });
    const { result } = renderHook(() => useOg118ProjectConversations('project-1'));
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(String(spy.mock.calls[0]?.[0])).toContain('project-1');
    await waitFor(() => expect(result.current.conversations).toHaveLength(1));
  });
});

describe('useOg118ProjectDocuments', () => {
  it('APAGADO: no toca la red y no reporta fallo', async () => {
    vi.stubEnv('NEXT_PUBLIC_OG118_PROYECTOS', '0');
    const spy = espiarFetch({ documents: [], capacity: null });
    const { result } = renderHook(() => useOg118ProjectDocuments('project-1'));
    await waitFor(() => expect(result.current.documents).toEqual([]));
    expect(spy).not.toHaveBeenCalled();
    // `failed` en false y no en true: apagado no es un error, y pintarlo como
    // fallo le enseñaría al usuario que algo se rompió.
    expect(result.current.failed).toBe(false);
  });

  it('ENCENDIDO: pide los documentos del proyecto', async () => {
    vi.stubEnv('NEXT_PUBLIC_OG118_PROYECTOS', '1');
    const spy = espiarFetch({
      documents: [{ docId: 'acta.txt', chunks: 1, status: 'indexed', attributes: {} }],
      capacity: { docs: 1, chunks: 1, bytes: 209, maxDocs: null, maxBytes: null },
    });
    const { result } = renderHook(() => useOg118ProjectDocuments('project-1'));
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(String(spy.mock.calls[0]?.[0])).toContain('project-1');
    await waitFor(() => expect(result.current.documents).toHaveLength(1));
  });
});
