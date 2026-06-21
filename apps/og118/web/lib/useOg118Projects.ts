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

export interface Og118Project {
  /** Also the corpus_id (corpus_id = project id). */
  id: string;
  name: string;
  createdAt: string;
}

export interface UseOg118Projects {
  projects: Og118Project[];
  activeProjectId: string | null;
  createProject: (name: string) => string;
  selectProject: (id: string) => void;
  deleteProject: (id: string) => void;
}

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

function newProjectId(): string {
  const rand =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2);
  return `project-${rand}`;
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

  const createProject = useCallback((name: string): string => {
    const project: Og118Project = {
      id: newProjectId(),
      name: name.trim() || 'Proyecto',
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
