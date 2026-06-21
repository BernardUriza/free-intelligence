import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

import { useOg118Projects } from '../useOg118Projects';

beforeEach(() => {
  localStorage.clear();
});

describe('useOg118Projects', () => {
  it('starts empty with no active project', () => {
    const { result } = renderHook(() => useOg118Projects());
    expect(result.current.projects).toEqual([]);
    expect(result.current.activeProjectId).toBeNull();
  });

  it('creates a project, returns its id, and makes it active', () => {
    const { result } = renderHook(() => useOg118Projects());
    let id = '';
    act(() => {
      id = result.current.createProject('Negocio de mamá');
    });
    expect(id).toBeTruthy();
    expect(result.current.projects).toHaveLength(1);
    expect(result.current.projects[0].name).toBe('Negocio de mamá');
    expect(result.current.activeProjectId).toBe(id);
  });

  it('the newest created project becomes active', () => {
    const { result } = renderHook(() => useOg118Projects());
    let second = '';
    act(() => {
      result.current.createProject('Uno');
      second = result.current.createProject('Dos');
    });
    expect(result.current.projects).toHaveLength(2);
    expect(result.current.activeProjectId).toBe(second);
  });

  it('selectProject switches the active project', () => {
    const { result } = renderHook(() => useOg118Projects());
    let first = '';
    act(() => {
      first = result.current.createProject('Uno');
      result.current.createProject('Dos');
    });
    act(() => {
      result.current.selectProject(first);
    });
    expect(result.current.activeProjectId).toBe(first);
  });

  it('deleting the active project clears the active selection', () => {
    const { result } = renderHook(() => useOg118Projects());
    let id = '';
    act(() => {
      id = result.current.createProject('Solo');
    });
    act(() => {
      result.current.deleteProject(id);
    });
    expect(result.current.projects).toHaveLength(0);
    expect(result.current.activeProjectId).toBeNull();
  });

  it('persists projects across hook remounts (localStorage)', () => {
    const first = renderHook(() => useOg118Projects());
    let id = '';
    act(() => {
      id = first.result.current.createProject('Persistente');
    });
    first.unmount();

    const second = renderHook(() => useOg118Projects());
    expect(second.result.current.projects.map((p) => p.id)).toContain(id);
    expect(second.result.current.activeProjectId).toBe(id);
  });
});
