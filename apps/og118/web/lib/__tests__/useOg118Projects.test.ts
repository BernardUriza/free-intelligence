import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

import { useOg118Projects } from '../useOg118Projects';

// createProject now mints the corpus_id SERVER-SIDE (POST /projects). The mock
// returns a fresh server-minted id per call; the hook must use what the server
// returns and never fabricate one.
let mintCount = 0;
let lastBody: unknown = null;

beforeEach(() => {
  localStorage.clear();
  mintCount = 0;
  lastBody = null;
  vi.stubGlobal('fetch', async (_url: string, init: RequestInit) => {
    lastBody = JSON.parse(String(init.body));
    mintCount += 1;
    return {
      ok: true,
      json: async () => ({ project_id: `project-server-${mintCount}` }),
    } as Response;
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useOg118Projects', () => {
  it('starts empty with no active project', () => {
    const { result } = renderHook(() => useOg118Projects());
    expect(result.current.projects).toEqual([]);
    expect(result.current.activeProjectId).toBeNull();
  });

  it('creates a project with the SERVER-minted id and makes it active', async () => {
    const { result } = renderHook(() => useOg118Projects());
    let id = '';
    await act(async () => {
      id = await result.current.createProject('Negocio de mamá');
    });
    expect(id).toBe('project-server-1');
    expect(result.current.projects).toHaveLength(1);
    expect(result.current.projects[0].name).toBe('Negocio de mamá');
    expect(result.current.activeProjectId).toBe(id);
    // The invariant: the client sends only the name, never a corpus_id.
    expect(lastBody).toEqual({ name: 'Negocio de mamá' });
  });

  it('the newest created project becomes active', async () => {
    const { result } = renderHook(() => useOg118Projects());
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
    let first = '';
    await act(async () => {
      first = await result.current.createProject('Uno');
      await result.current.createProject('Dos');
    });
    act(() => {
      result.current.selectProject(first);
    });
    expect(result.current.activeProjectId).toBe(first);
  });

  it('deleting the active project clears the active selection', async () => {
    const { result } = renderHook(() => useOg118Projects());
    let id = '';
    await act(async () => {
      id = await result.current.createProject('Solo');
    });
    act(() => {
      result.current.deleteProject(id);
    });
    expect(result.current.projects).toHaveLength(0);
    expect(result.current.activeProjectId).toBeNull();
  });

  it('persists projects across hook remounts (localStorage)', async () => {
    const first = renderHook(() => useOg118Projects());
    let id = '';
    await act(async () => {
      id = await first.result.current.createProject('Persistente');
    });
    first.unmount();

    const second = renderHook(() => useOg118Projects());
    expect(second.result.current.projects.map((p) => p.id)).toContain(id);
    expect(second.result.current.activeProjectId).toBe(id);
  });

  // The shared-device data-leak fix: two accounts signing in on the SAME browser
  // must NOT see each other's projects. Each identity gets its own localStorage
  // partition; a null identity keeps the legacy unscoped key.
  describe('identity scoping (no cross-account leak)', () => {
    it('a project created under one account is INVISIBLE to another account', async () => {
      const accountA = renderHook(() => useOg118Projects('google-oauth2|aaa'));
      let aId = '';
      await act(async () => {
        aId = await accountA.result.current.createProject('Lo de A');
      });
      accountA.unmount();

      const accountB = renderHook(() => useOg118Projects('google-oauth2|bbb'));
      expect(accountB.result.current.projects.map((p) => p.id)).not.toContain(aId);
      expect(accountB.result.current.projects).toHaveLength(0);
      expect(accountB.result.current.activeProjectId).toBeNull();
    });

    it('the same account sees its own projects across remounts', async () => {
      const first = renderHook(() => useOg118Projects('google-oauth2|aaa'));
      let id = '';
      await act(async () => {
        id = await first.result.current.createProject('Mío');
      });
      first.unmount();

      const again = renderHook(() => useOg118Projects('google-oauth2|aaa'));
      expect(again.result.current.projects.map((p) => p.id)).toContain(id);
    });

    it('switching the active identity re-hydrates to that identity list', async () => {
      const { result, rerender } = renderHook(({ uid }) => useOg118Projects(uid), {
        initialProps: { uid: 'google-oauth2|aaa' as string | null },
      });
      await act(async () => {
        await result.current.createProject('De A');
      });
      expect(result.current.projects).toHaveLength(1);

      rerender({ uid: 'google-oauth2|bbb' });
      expect(result.current.projects).toHaveLength(0);

      rerender({ uid: 'google-oauth2|aaa' });
      expect(result.current.projects).toHaveLength(1);
      expect(result.current.projects[0].name).toBe('De A');
    });

    it('a null (bearer/legacy) identity writes to the legacy namespace, NEVER the bare global key', async () => {
      const legacy = renderHook(() => useOg118Projects(null));
      await act(async () => {
        await legacy.result.current.createProject('Legacy');
      });
      // The pre-fix global store must stay untouched — that is where the leaked
      // cross-account data lives; a bearer session must never write back to it.
      expect(localStorage.getItem('og118.projects')).toBeNull();
      const legacyRaw = localStorage.getItem('og118.projects--legacy');
      expect(legacyRaw).not.toBeNull();
      expect(JSON.parse(legacyRaw as string)).toHaveLength(1);
    });
  });
});
