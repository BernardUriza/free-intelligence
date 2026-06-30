import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

import { useOg118Projects } from '../useOg118Projects';

// PROJ-SYNC-1: projects are SERVER-owned. The hook hydrates from GET /projects
// (owner-filtered by the token), POST mints the id, DELETE removes server-side.
// localStorage is only a render cache. This mock is a stateful per-owner server
// keyed by the Authorization header, so reconciliation + ownership are exercised
// for real instead of a generic stub.

interface SrvProject {
  id: string;
  name: string;
  createdAt: string;
}

let store: Map<string, SrvProject[]>;
let mintCount: number;
let lastCreateBody: unknown;
let failNetwork: boolean;

function ownerOf(init?: RequestInit): string {
  const h = (init?.headers ?? {}) as Record<string, string>;
  return h.Authorization ?? 'anon';
}

beforeEach(() => {
  localStorage.clear();
  store = new Map();
  mintCount = 0;
  lastCreateBody = null;
  failNetwork = false;

  vi.stubGlobal('fetch', async (url: string, init: RequestInit = {}) => {
    if (failNetwork) throw new TypeError('network down');
    const owner = ownerOf(init);
    const list = store.get(owner) ?? [];
    const method = (init.method ?? 'GET').toUpperCase();

    if (url.endsWith('/projects') && method === 'GET') {
      return { ok: true, json: async () => ({ projects: list }) } as Response;
    }
    if (url.endsWith('/projects') && method === 'POST') {
      lastCreateBody = JSON.parse(String(init.body));
      mintCount += 1;
      const id = `project-server-${mintCount}`;
      store.set(owner, [
        { id, name: (lastCreateBody as { name: string }).name, createdAt: '2026-01-01T00:00:00Z' },
        ...list,
      ]);
      return { ok: true, json: async () => ({ project_id: id }) } as Response;
    }
    if (url.includes('/projects/') && method === 'DELETE') {
      const id = decodeURIComponent(url.split('/projects/')[1]);
      store.set(owner, list.filter((p) => p.id !== id));
      return { ok: true, json: async () => ({ deleted: id }) } as Response;
    }
    return { ok: false, status: 404, json: async () => ({}) } as Response;
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useOg118Projects (PROJ-SYNC-1, server-owned)', () => {
  it('starts empty and becomes ready after the server hydrate', async () => {
    const { result } = renderHook(() => useOg118Projects());
    expect(result.current.projects).toEqual([]);
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current.projects).toEqual([]);
    expect(result.current.activeProjectId).toBeNull();
  });

  it('hydrates from GET /projects (the server is the source of truth)', async () => {
    store.set('anon', [{ id: 'srv-1', name: 'Ya existía', createdAt: '2026-01-01T00:00:00Z' }]);
    const { result } = renderHook(() => useOg118Projects());
    await waitFor(() => expect(result.current.projects).toHaveLength(1));
    expect(result.current.projects[0]).toMatchObject({ id: 'srv-1', name: 'Ya existía' });
  });

  it('creates a project with the SERVER-minted id and makes it active', async () => {
    const { result } = renderHook(() => useOg118Projects());
    await waitFor(() => expect(result.current.ready).toBe(true));
    let id = '';
    await act(async () => {
      id = await result.current.createProject('Negocio de mamá');
    });
    expect(id).toBe('project-server-1');
    expect(result.current.projects[0].name).toBe('Negocio de mamá');
    expect(result.current.activeProjectId).toBe(id);
    // The invariant: the client sends only the name, never a corpus_id.
    expect(lastCreateBody).toEqual({ name: 'Negocio de mamá' });
  });

  it('the newest created project becomes active', async () => {
    const { result } = renderHook(() => useOg118Projects());
    await waitFor(() => expect(result.current.ready).toBe(true));
    let second = '';
    await act(async () => {
      await result.current.createProject('Uno');
      second = await result.current.createProject('Dos');
    });
    expect(result.current.projects).toHaveLength(2);
    expect(result.current.activeProjectId).toBe(second);
  });

  it('selectProject switches the active project', async () => {
    const { result } = renderHook(() => useOg118Projects());
    await waitFor(() => expect(result.current.ready).toBe(true));
    let first = '';
    await act(async () => {
      first = await result.current.createProject('Uno');
      await result.current.createProject('Dos');
    });
    act(() => result.current.selectProject(first));
    expect(result.current.activeProjectId).toBe(first);
  });

  it('deleteProject removes it SERVER-side and clears the active selection', async () => {
    const { result } = renderHook(() => useOg118Projects());
    await waitFor(() => expect(result.current.ready).toBe(true));
    let id = '';
    await act(async () => {
      id = await result.current.createProject('Solo');
    });
    expect(store.get('anon')).toHaveLength(1);

    await act(async () => {
      await result.current.deleteProject(id);
    });
    expect(result.current.projects).toHaveLength(0);
    expect(result.current.activeProjectId).toBeNull();
    // the server registry (not just the local cache) lost it
    expect(store.get('anon')).toHaveLength(0);
  });

  it('the server list REPLACES a stale local cache (a project gone from the account disappears)', async () => {
    // Seed the cache with a project the server does NOT have (deleted elsewhere).
    localStorage.setItem(
      'og118.projects--legacy',
      JSON.stringify([{ id: 'ghost', name: 'Fantasma', createdAt: '2026-01-01T00:00:00Z' }]),
    );
    const { result } = renderHook(() => useOg118Projects(null));
    // Instant cache render shows the ghost first…
    expect(result.current.projects.map((p) => p.id)).toContain('ghost');
    // …then the server reconcile (empty) removes it.
    await waitFor(() => expect(result.current.projects).toHaveLength(0));
  });

  it('keeps the cache when the server fetch fails (offline resilience)', async () => {
    localStorage.setItem(
      'og118.projects--legacy',
      JSON.stringify([{ id: 'cached', name: 'En cache', createdAt: '2026-01-01T00:00:00Z' }]),
    );
    failNetwork = true;
    const { result } = renderHook(() => useOg118Projects(null));
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current.projects.map((p) => p.id)).toContain('cached');
  });
});

// The shared-device boundary: the SERVER owner-filters by token, and the local
// cache is partitioned by identity so two accounts on one browser never read each
// other's cached list during the in-flight fetch.
describe('identity scoping (no cross-account leak)', () => {
  it("an account never sees another account's server projects", async () => {
    localStorage.setItem('og118_access_token', 'tok-A');
    const a = renderHook(() => useOg118Projects('google-oauth2|aaa'));
    await waitFor(() => expect(a.result.current.ready).toBe(true));
    let aId = '';
    await act(async () => {
      aId = await a.result.current.createProject('Lo de A');
    });
    a.unmount();

    localStorage.setItem('og118_access_token', 'tok-B');
    const b = renderHook(() => useOg118Projects('google-oauth2|bbb'));
    await waitFor(() => expect(b.result.current.ready).toBe(true));
    expect(b.result.current.projects.map((p) => p.id)).not.toContain(aId);
    expect(b.result.current.projects).toHaveLength(0);
  });

  it('a null (bearer/legacy) identity caches under the legacy namespace, never the bare global key', async () => {
    const legacy = renderHook(() => useOg118Projects(null));
    await waitFor(() => expect(legacy.result.current.ready).toBe(true));
    await act(async () => {
      await legacy.result.current.createProject('Legacy');
    });
    expect(localStorage.getItem('og118.projects')).toBeNull();
    const legacyRaw = localStorage.getItem('og118.projects--legacy');
    expect(legacyRaw).not.toBeNull();
    expect(JSON.parse(legacyRaw as string)).toHaveLength(1);
  });
});
