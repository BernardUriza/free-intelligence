'use client';

/**
 * useOg118Projects — local-first Projects library for the papelería canary.
 *
 * A project is a named corpus the agent can search (proj-sidebar). The project
 * `id` IS the `corpus_id` passed to POST /projects/{id}/upload and to the agent
 * via context={"corpus_id": activeProjectId}.
 *
 * Identity scoping (shared-device leak fix): the localStorage keys are partitioned
 * by the signed-in account (`userId` = the Auth0 principal's sub) via fi-glass's
 * `scopedStoreName`, so two accounts on the SAME browser never see each other's
 * projects. A null identity (bearer / legacy single-tenant) keeps the original
 * unscoped key, so pre-auth data survives. The corpus CONTENT is already
 * owner-gated server-side (PROJ-ACCOUNT-1); this scopes the client-side list to
 * match.
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
  /** Mints the corpus_id server-side (POST /projects), never client-side. */
  createProject: (name: string) => Promise<string>;
  selectProject: (id: string) => void;
  deleteProject: (id: string) => void;
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

export function useOg118Projects(userId: string | null = null): UseOg118Projects {
  const projectsKey = scopedStoreName(PROJECTS_KEY_BASE, userId);
  const activeKey = scopedStoreName(ACTIVE_KEY_BASE, userId);

  const [projects, setProjects] = useState<Og118Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const activeRef = useRef<string | null>(null);
  // The committed list, updated SYNCHRONOUSLY inside each write (and on hydrate),
  // so two mutations before a re-render compose without a stale closure — and the
  // persistence stays OUT of the setState updater (a side-effect inside an updater
  // is a smell: React may double-invoke updaters under Strict/Concurrent mode).
  const projectsRef = useRef<Og118Project[]>([]);
  activeRef.current = activeProjectId;

  // Hydrate whenever the identity (its storage key) changes. This is the ONLY
  // place that READS storage, and it never writes — so an identity switch can
  // never clobber the new account's data with the old account's state.
  useEffect(() => {
    const loaded = loadProjects(projectsKey);
    projectsRef.current = loaded;
    setProjects(loaded);
    const active = localStorage.getItem(activeKey);
    setActiveProjectId(active && loaded.some((p) => p.id === active) ? active : null);
  }, [projectsKey, activeKey]);

  // Write-through on mutation (not via a state-change effect) so a key swap during
  // an identity switch can never persist the wrong account's list: `projectsKey`
  // is captured from the closure at call time = the CURRENT identity. The ref is
  // advanced synchronously so consecutive writes compose; persistence is a plain
  // statement, never a side-effect inside setState.
  const writeProjects = useCallback(
    (update: (prev: Og118Project[]) => Og118Project[]) => {
      const next = update(projectsRef.current);
      projectsRef.current = next;
      setProjects(next);
      try {
        localStorage.setItem(projectsKey, JSON.stringify(next));
      } catch {
        /* private mode / storage disabled */
      }
    },
    [projectsKey],
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
    (id: string) => {
      writeProjects((prev) => prev.filter((p) => p.id !== id));
      if (activeRef.current === id) writeActive(null);
    },
    [writeProjects, writeActive],
  );

  return { projects, activeProjectId, createProject, selectProject, deleteProject };
}
