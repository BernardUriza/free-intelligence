// @vitest-environment jsdom
/**
 * NEXT_PUBLIC_OG118_PROYECTOS — the transport half of the switch.
 *
 * BOTH branches are pinned on purpose. An OFF branch with no test rots in the
 * dark and is discovered broken on the day someone flips it back on; an ON
 * branch with no test is the `else` nobody ran. The same reasoning is written
 * into the server's `proyectos_activos` docstring — this is its mirror.
 *
 * What the OFF branch has to prove is NEGATIVE and therefore needs its control:
 * "no request fired" means nothing unless the ON branch, on the same mock,
 * demonstrably fires one.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

import { proyectosActivos } from '../og118Flags';
import { useOg118Projects } from '../useOg118Projects';
import { useOg118Agent } from '../useOg118Agent';
import { useOg118ProjectDocuments } from '../useOg118ProjectDocuments';
import { useOg118ProjectConversations } from '../useOg118ProjectConversations';
import { useOg118ProjectUpload } from '../useOg118ProjectUpload';

function on() {
  vi.stubEnv('NEXT_PUBLIC_OG118_PROYECTOS', '1');
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe('proyectosActivos — the truthy vocabulary matches the server', () => {
  it('is OFF when the variable is unset (the shipped default)', () => {
    vi.stubEnv('NEXT_PUBLIC_OG118_PROYECTOS', undefined);
    expect(proyectosActivos()).toBe(false);
  });

  it.each(['1', 'true', 'yes', 'on', 'TRUE', ' On '])('is ON for %o', (raw) => {
    vi.stubEnv('NEXT_PUBLIC_OG118_PROYECTOS', raw);
    expect(proyectosActivos()).toBe(true);
  });

  it.each(['0', 'false', 'no', 'off', '', 'sí'])('is OFF for %o', (raw) => {
    vi.stubEnv('NEXT_PUBLIC_OG118_PROYECTOS', raw);
    expect(proyectosActivos()).toBe(false);
  });
});

describe('useOg118Projects under the flag', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    localStorage.clear();
    fetchMock.mockReset();
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ projects: [] }) });
    vi.stubGlobal('fetch', fetchMock);
  });

  it('OFF: settles empty and never calls GET /projects', async () => {
    const { result } = renderHook(() => useOg118Projects(null, true));
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.current.projects).toEqual([]);
    expect(result.current.activeProjectId).toBeNull();
  });

  it('OFF: does not resurrect a stale localStorage cache from a flag-on session', async () => {
    localStorage.setItem(
      'og118.projects--legacy',
      JSON.stringify([{ id: 'p1', name: 'Negocio de mamá' }]),
    );
    localStorage.setItem('og118.activeProjectId--legacy', 'p1');
    const { result } = renderHook(() => useOg118Projects(null, true));
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current.projects).toEqual([]);
    expect(result.current.activeProjectId).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('OFF: createProject rejects instead of POSTing to a route that does not exist', async () => {
    const { result } = renderHook(() => useOg118Projects(null, true));
    await waitFor(() => expect(result.current.ready).toBe(true));
    await expect(result.current.createProject('Nuevo')).rejects.toThrow(/desactivado/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('OFF: deleteProject is a no-op (no DELETE on the wire)', async () => {
    const { result } = renderHook(() => useOg118Projects(null, true));
    await waitFor(() => expect(result.current.ready).toBe(true));
    await act(() => result.current.deleteProject('p1'));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('ON: the control — the very same mount DOES call GET /projects', async () => {
    on();
    const { result } = renderHook(() => useOg118Projects(null, true));
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/projects$/);
  });
});

describe('useOg118Agent corpus binding under the flag', () => {
  const fetchMock = vi.fn();

  function emptyStreamResponse() {
    return {
      status: 200,
      body: { getReader: () => ({ read: async () => ({ value: undefined, done: true as const }) }) },
    };
  }

  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(emptyStreamResponse());
    vi.stubGlobal('fetch', fetchMock);
  });

  it('OFF: omits corpus_id even when an active project id is passed in', async () => {
    const { result } = renderHook(() => useOg118Agent('conv-1', 'corpus-abc'));
    await act(() => result.current.send('hola'));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect('corpus_id' in body).toBe(false);
  });

  it('ON: the control — the same call DOES carry corpus_id', async () => {
    on();
    const { result } = renderHook(() => useOg118Agent('conv-1', 'corpus-abc'));
    await act(() => result.current.send('hola'));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.corpus_id).toBe('corpus-abc');
  });
});

describe('the workspace transports under the flag', () => {
  // These three only ever run from a surface the flag already removes, so the
  // gate inside them is belt-and-braces. It is tested anyway for the same reason
  // the OFF branch is tested at all: an untested guard is a guard nobody notices
  // has stopped guarding, and the day the flag flips these are the calls that
  // would 404 in a loop.
  const fetchMock = vi.fn();

  beforeEach(() => {
    localStorage.clear();
    fetchMock.mockReset();
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal('fetch', fetchMock);
  });

  it('OFF: the documents rail asks for nothing even with a project id in hand', async () => {
    const { result } = renderHook(() => useOg118ProjectDocuments('p1', true));
    await waitFor(() => expect(result.current.ready).toBe(false));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('ON: the control — the same mount DOES ask for the documents', async () => {
    on();
    renderHook(() => useOg118ProjectDocuments('p1', true));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/projects\/p1\/documents$/);
  });

  it("OFF: the project's Recents list asks for nothing", async () => {
    renderHook(() => useOg118ProjectConversations('p1', true));
    await new Promise((r) => setTimeout(r, 0));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('ON: the control — the same mount DOES ask for the conversations', async () => {
    on();
    renderHook(() => useOg118ProjectConversations('p1', true));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/conversations\?projectId=p1$/);
  });

  it('OFF: uploading a valid text file is a no-op, not a POST to a dead route', async () => {
    const { result } = renderHook(() => useOg118ProjectUpload());
    await act(() => result.current.uploadFile('p1', new File(['hola'], 'notas.txt', { type: 'text/plain' })));
    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.current.status).toBe('selecting');
  });

  it('ON: the control — the same file DOES POST to the corpus', async () => {
    on();
    const { result } = renderHook(() => useOg118ProjectUpload());
    await act(() => result.current.uploadFile('p1', new File(['hola'], 'notas.txt', { type: 'text/plain' })));
    expect(fetchMock).toHaveBeenCalled();
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/projects\/p1\/upload$/);
  });
});
