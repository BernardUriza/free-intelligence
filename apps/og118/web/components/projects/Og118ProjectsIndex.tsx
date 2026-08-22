'use client';

/**
 * The Projects INDEX — the grid of cards (FIGLASS-PROJECTS-PAGE-1, §A).
 *
 * Every visual decision (grid, card anatomy, search box, header layout) belongs
 * to fi-glass's resource primitives. What lives here is what fi-glass must never
 * know: the word "proyecto", the Spanish copy, the sort criteria, and the route
 * a card navigates to.
 */

import { useMemo, useState } from 'react';
import {
  ResourceCard,
  ResourceCardGrid,
  ResourceIndexHeader,
  ResourceSearchInput,
  filterByQuery,
} from 'fi-glass/resource';
import type { Og118Project } from '@/lib/useOg118Projects';
import { relativeTime } from '@/lib/og118RelativeTime';

export type Og118ProjectSort = 'updated' | 'created' | 'name';

const SORT_LABEL: Record<Og118ProjectSort, string> = {
  updated: 'Actualizado',
  created: 'Creado',
  name: 'Nombre',
};

export interface Og118ProjectsIndexProps {
  projects: Og118Project[];
  ready: boolean;
  onOpen: (id: string) => void;
  onCreate: () => void;
  /** Injectable so a test pins a phrase without racing the wall clock. */
  now?: number;
}

export function Og118ProjectsIndex({
  projects,
  ready,
  onOpen,
  onCreate,
  now,
}: Og118ProjectsIndexProps) {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<Og118ProjectSort>('updated');

  const visible = useMemo(() => {
    const matched = filterByQuery(projects, query, (p) => [p.name, p.description]);
    const ordered = [...matched];
    ordered.sort((a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name, 'es');
      const key = sort === 'created' ? 'createdAt' : 'updatedAt';
      return (b[key] || '').localeCompare(a[key] || '');
    });
    return ordered;
  }, [projects, query, sort]);

  return (
    <div className="og-projects-page">
      <ResourceIndexHeader
        title="Proyectos"
        sortSlot={
          <label className="og-projects-sort">
            <span className="og-projects-sort-label">Ordenar por</span>
            <select
              value={sort}
              aria-label="Ordenar proyectos"
              onChange={(e) => setSort(e.target.value as Og118ProjectSort)}
            >
              {(Object.keys(SORT_LABEL) as Og118ProjectSort[]).map((key) => (
                <option key={key} value={key}>
                  {SORT_LABEL[key]}
                </option>
              ))}
            </select>
          </label>
        }
        actionSlot={
          <button type="button" className="og-projects-cta" onClick={onCreate}>
            Nuevo proyecto
          </button>
        }
      />

      <ResourceSearchInput
        value={query}
        onChange={setQuery}
        placeholder="Buscar proyectos..."
        ariaLabel="Buscar proyectos"
      />

      {!ready ? (
        <p className="og-projects-note">Cargando tus proyectos…</p>
      ) : (
        <ResourceCardGrid
          ariaLabel="Proyectos"
          emptyState={
            <p className="og-projects-note">
              {projects.length === 0
                ? 'Todavía no tienes proyectos. Crea uno para darle a tu agente un corpus que consultar.'
                : `Ningún proyecto coincide con "${query}".`}
            </p>
          }
        >
          {visible.map((p) => (
            <ResourceCard
              key={p.id}
              title={p.name}
              description={p.description || undefined}
              meta={metaFor(p, sort, now)}
              onClick={() => onOpen(p.id)}
            />
          ))}
        </ResourceCardGrid>
      )}
    </div>
  );
}

function metaFor(p: Og118Project, sort: Og118ProjectSort, now?: number): string | undefined {
  const iso = sort === 'created' ? p.createdAt : p.updatedAt;
  const phrase = relativeTime(iso, now);
  if (!phrase) return undefined;
  return `${sort === 'created' ? 'Creado' : 'Actualizado'} ${phrase}`;
}
