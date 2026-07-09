'use client';

/**
 * useOg118Projects — server-owned Projects library (PROJ-SYNC-1).
 *
 * A project is a named corpus the agent can search (proj-sidebar). The project
 * `id` IS the `corpus_id` passed to POST /projects/{id}/upload and to the agent
 * via context={"corpus_id": activeProjectId}.
 *
 * Source of truth = the SERVER registry (owner-filtered by the caller's account).
 * On sign-in the hook hydrates from GET /projects; localStorage is only a CACHE
 * for instant render before that fetch resolves, then reconciled to the server
 * list. So the account's projects travel across devices and survive a cleared
 * browser — not local-first state that lives in one browser (the pre-PROJ-SYNC-1
 * behavior, where delete was local-only and the server corpus was orphaned).
 *
 * Identity scoping (shared-device leak fix): the localStorage cache keys are
 * partitioned by the signed-in account (`userId` = the Auth0 principal's sub) via
 * fi-glass's `scopedStoreName`, so two accounts on the SAME browser never read
 * each other's cached list while the server fetch is in flight. The server is the
 * real owner gate (PROJ-ACCOUNT-1); this scopes the client-side cache to match.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { scopedStoreName } from 'fi-glass/identity';
import { authHeaders } from './og118Token';

export interface Og118Project {
  /** Also the corpus_id (corpus_id = project id), MINTED server-side. */
  id: string;
  name: string;
  createdAt: string;
}

export interface UseOg118Projects {
  projects: Og118Project[];
  activeProjectId: string | null;
  /** True once the server list has been reconciled (or the fetch settled). */
  ready: boolean;
  /** Mints the corpus_id server-side (POST /projects), never client-side. */
  createProject: (name: string) => Promise<string>;
  selectProject: (id: string) => void;
  /** Deletes server-side (DELETE /projects/{id}) AND the local cache. */
  deleteProject: (id: string) => Promise<void>;
}

const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';
const PROJECTS_KEY_BASE = 'og118.projects';
const ACTIVE_KEY_BASE = 'og118.activeProjectId';

function loadProjects(key: string): Og118Project[] {
  try {
    const raw = localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

interface ServerProject {
  id: string;
  name: string;
  createdAt?: string;
}

export function useOg118Projects(
  userId: string | null = null,
  tokenReady: boolean = true,
): UseOg118Projects {
  const projectsKey = scopedStoreName(PROJECTS_KEY_BASE, userId);
  const activeKey = scopedStoreName(ACTIVE_KEY_BASE, userId);

  const [projects, setProjects] = useState<Og118Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const activeRef = useRef<string | null>(null);
  // The committed list, updated SYNCHRONOUSLY inside each write (and on hydrate),
  // so two mutations before a re-render compose without a stale closure — and the
  // persistence stays OUT of the setState updater (a side-effect inside an updater
  // is a smell: React may double-invoke updaters under Strict/Concurrent mode).
  const projectsRef = useRef<Og118Project[]>([]);
  activeRef.current = activeProjectId;

  // Persist the cache. Plain statement, never a side-effect inside setState; the
  // key is captured at call time = the CURRENT identity, so an identity switch can
  // never write the wrong account's list back to storage.
  const persist = useCallback(
    (next: Og118Project[], key: string) => {
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* private mode / storage disabled */
      }
    },
    [],
  );

  const writeProjects = useCallback(
    (update: (prev: Og118Project[]) => Og118Project[]) => {
      const next = update(projectsRef.current);
      projectsRef.current = next;
      setProjects(next);
      persist(next, projectsKey);
    },
    [persist, projectsKey],
  );

  const writeActive = useCallback(
    (id: string | null) => {
      setActiveProjectId(id);
      try {
        if (id) localStorage.setItem(activeKey, id);
        else localStorage.removeItem(activeKey);
      } catch {
        /* ignore */
      }
    },
    [activeKey],
  );

  // qa-stale-localstorage: sweep the pre-identity-scoping globals (pre-#276).
  // The scoped keys ALWAYS carry a suffix (signed-out = `--legacy`), so the bare
  // keys can never be the live store; and Projects are server-owned (#292), so
  // the vestigial globals hold nothing of record.
  useEffect(() => {
    try {
      localStorage.removeItem(PROJECTS_KEY_BASE);
      localStorage.removeItem(ACTIVE_KEY_BASE);
    } catch {
      /* private mode / storage disabled */
    }
  }, []);

  // Hydrate on identity change: render the cache instantly, then reconcile to the
  // SERVER list (the owner of record). The server list REPLACES the cache, so a
  // project that lives only in this browser (stale cache, or another account's,
  // or one deleted server-side from another device) simply disappears. On a fetch
  // failure (offline / 401) the cache is kept untouched — never wipe on error.
  useEffect(() => {
    let cancelled = false;

    const cached = loadProjects(projectsKey);
    projectsRef.current = cached;
    setProjects(cached);
    const cachedActive = localStorage.getItem(activeKey);
    setActiveProjectId(cachedActive && cached.some((p) => p.id === cachedActive) ? cachedActive : null);
    setReady(false);

    // Wait for the Authorization token before the auth-gated server fetch: firing
    // GET /projects before TokenSync mirrors the Auth0 token just 401s and leaves
    // the section empty. The effect re-runs when tokenReady flips true.
    if (!tokenReady) return;

    (async () => {
      try {
        const res = await fetch(`${API}/projects`, { headers: { ...authHeaders() } });
        if (!res.ok || cancelled) return;
        const body = (await res.json()) as { projects?: ServerProject[] };
        if (cancelled) return;
        const server: Og118Project[] = (body.projects ?? []).map((p) => ({
          id: p.id,
          name: p.name,
          createdAt: p.createdAt ?? new Date().toISOString(),
        }));
        projectsRef.current = server;
        setProjects(server);
        persist(server, projectsKey);
        // Keep the active selection only if the server still has it.
        setActiveProjectId((prev) => {
          const keep = prev && server.some((p) => p.id === prev) ? prev : null;
          try {
            if (keep) localStorage.setItem(activeKey, keep);
            else localStorage.removeItem(activeKey);
          } catch {
            /* ignore */
          }
          return keep;
        });
      } catch {
        /* offline — keep the cache as-is */
      } finally {
        if (!cancelled) setReady(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [projectsKey, activeKey, persist, tokenReady]);

  const createProject = useCallback(
    async (name: string): Promise<string> => {
      const displayName = name.trim() || 'Proyecto';
      const res = await fetch(`${API}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ name: displayName }),
      });
      if (!res.ok) throw new Error(`create project failed: ${res.status}`);
      const { project_id } = await res.json();
      const project: Og118Project = {
        id: project_id,
        name: displayName,
        createdAt: new Date().toISOString(),
      };
      writeProjects((prev) => [project, ...prev]);
      writeActive(project.id);
      return project.id;
    },
    [writeProjects, writeActive],
  );

  const selectProject = useCallback((id: string) => writeActive(id), [writeActive]);

  const deleteProject = useCallback(
    async (id: string): Promise<void> => {
      // Optimistic: drop from the cache + clear the active selection immediately.
      writeProjects((prev) => prev.filter((p) => p.id !== id));
      if (activeRef.current === id) writeActive(null);
      try {
        // The server owns the project + its corpus. A 404 means it's already gone
        // (deleted from another device, or never owned) — the local removal above
        // already reflects that, so a 404 is success, not an error to surface.
        await fetch(`${API}/projects/${encodeURIComponent(id)}`, {
          method: 'DELETE',
          headers: { ...authHeaders() },
        });
      } catch {
        /* network — the local cache is updated; the next load reconciles */
      }
    },
    [writeProjects, writeActive],
  );

  return { projects, activeProjectId, ready, createProject, selectProject, deleteProject };
}
