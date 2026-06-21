'use client';

/**
 * useOg118Projects — local-first Projects library for the papelería canary.
 *
 * A project is a named corpus the agent can search (proj-sidebar). The project
 * `id` IS the `corpus_id` passed to POST /projects/{id}/upload and, once
 * proj-corpusbind lands, to the agent via context={"corpus_id": activeProjectId}.
 * Persisted in localStorage (small list, no auth yet — Gate 3 ties projects to a
 * user). Consumer-local for now; a candidate to lift into fi-glass if a second
 * shell needs Projects (framework-first-canary).
 */

import { useCallback, useEffect, useState } from 'react';
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
const PROJECTS_KEY = 'og118.projects';
const ACTIVE_KEY = 'og118.activeProjectId';

function loadProjects(): Og118Project[] {
  try {
    const raw = localStorage.getItem(PROJECTS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function useOg118Projects(): UseOg118Projects {
  const [projects, setProjects] = useState<Og118Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);

  // Hydrate from localStorage on mount (client-only; SSR renders empty).
  useEffect(() => {
    const loaded = loadProjects();
    setProjects(loaded);
    const active = localStorage.getItem(ACTIVE_KEY);
    setActiveProjectId(active && loaded.some((p) => p.id === active) ? active : null);
  }, []);

  // Persist on change.
  useEffect(() => {
    localStorage.setItem(PROJECTS_KEY, JSON.stringify(projects));
  }, [projects]);
  useEffect(() => {
    if (activeProjectId) localStorage.setItem(ACTIVE_KEY, activeProjectId);
    else localStorage.removeItem(ACTIVE_KEY);
  }, [activeProjectId]);

  const createProject = useCallback(async (name: string): Promise<string> => {
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
    setProjects((prev) => [project, ...prev]);
    setActiveProjectId(project.id);
    return project.id;
  }, []);

  const selectProject = useCallback((id: string) => setActiveProjectId(id), []);

  const deleteProject = useCallback((id: string) => {
    setProjects((prev) => prev.filter((p) => p.id !== id));
    setActiveProjectId((cur) => (cur === id ? null : cur));
  }, []);

  return { projects, activeProjectId, createProject, selectProject, deleteProject };
}
