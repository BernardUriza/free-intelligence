'use client';

/**
 * The Projects page: index and detail behind one static route.
 *
 * Navigation is `history.pushState` over `?p=<id>` rather than a router push,
 * so the browser's Back button walks index ⇄ detail exactly as a reader expects
 * and a copied URL reopens the same project. `popstate` is what keeps the
 * rendered state honest when Back is pressed — without it the URL would change
 * and the page would not.
 */

import { useCallback, useEffect, useState } from 'react';
import { useOg118Identity } from '@/lib/og118Identity';
import { useOg118Projects } from '@/lib/useOg118Projects';
import { Og118ProjectsIndex } from './Og118ProjectsIndex';
import { Og118ProjectWorkspace } from './Og118ProjectWorkspace';

const PARAM = 'p';

function readParam(): string | null {
  if (typeof window === 'undefined') return null;
  return new URLSearchParams(window.location.search).get(PARAM);
}

export function Og118ProjectsPage() {
  const { userId, tokenReady } = useOg118Identity();
  const projects = useOg118Projects(userId, tokenReady);
  const [selected, setSelected] = useState<string | null>(null);

  // Read the URL AFTER mount, never during render: the static export prerenders
  // this file on a server with no location, and reading it in the render body
  // would hydrate a different tree than it shipped.
  useEffect(() => {
    setSelected(readParam());
    const onPop = () => setSelected(readParam());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const go = useCallback((id: string | null) => {
    const url = new URL(window.location.href);
    if (id) url.searchParams.set(PARAM, id);
    else url.searchParams.delete(PARAM);
    window.history.pushState({}, '', url);
    setSelected(id);
  }, []);

  const open = useCallback(
    (id: string) => {
      // Opening a project also makes it the ACTIVE corpus, so a conversation
      // started from here is bound to it — and gets stamped with its projectId.
      projects.selectProject(id);
      go(id);
    },
    [projects, go],
  );

  const create = useCallback(async () => {
    const name = window.prompt('Nombre del proyecto');
    if (name === null) return;
    const id = await projects.createProject(name);
    go(id);
  }, [projects, go]);

  const project = selected ? projects.projects.find((p) => p.id === selected) : undefined;

  if (selected && projects.ready && !project) {
    // A link to a project this account does not own (or one already deleted)
    // says so, instead of rendering an empty workspace that looks like a bug.
    return (
      <main className="og-projects-shell">
        <p className="og-projects-note">
          Ese proyecto ya no existe o no es tuyo.{' '}
          <button type="button" className="og-projects-edit" onClick={() => go(null)}>
            Volver a Proyectos
          </button>
        </p>
      </main>
    );
  }

  return (
    <main className="og-projects-shell">
      {project ? (
        <Og118ProjectWorkspace
          project={project}
          tokenReady={tokenReady}
          onBack={() => go(null)}
          onOpenConversation={(id) => {
            window.location.href = `/?c=${encodeURIComponent(id)}`;
          }}
          onStartConversation={() => {
            projects.selectProject(project.id);
            window.location.href = '/';
          }}
          onRename={(name) => projects.updateProject(project.id, { name })}
          onDescribe={(description) => projects.updateProject(project.id, { description })}
          onInstruct={(instructions) => projects.updateProject(project.id, { instructions })}
        />
      ) : (
        <Og118ProjectsIndex
          projects={projects.projects}
          ready={projects.ready}
          onOpen={open}
          onCreate={create}
        />
      )}
    </main>
  );
}
