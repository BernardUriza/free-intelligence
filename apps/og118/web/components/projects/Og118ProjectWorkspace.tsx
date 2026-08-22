'use client';

/**
 * The Projects DETAIL — one project as a workspace (FIGLASS-PROJECTS-PAGE-1, §B).
 *
 * Main column: the project's own conversations ("Recents"), plus the way into a
 * new one. Rail: the knowledge panel — capacity meter over the document grid,
 * both from the single `/projects/{id}/documents` response.
 *
 * The Instructions panel is here now that the turn actually READS the field: it
 * rides the system prompt of every turn in this project (fi-runner's
 * `owner_instructions_binding`). It was deliberately absent while the field was
 * only stored — an editor for a setting the agent ignores is a promise the
 * product cannot keep.
 */

import { useEffect, useState } from 'react';
import {
  CapacityMeter,
  DocCard,
  DocCardGrid,
  RailPanel,
  RailPanelStack,
  WorkspaceBreadcrumb,
  WorkspaceDetailLayout,
} from 'fi-glass/resource';
import type { Og118Project } from '@/lib/useOg118Projects';
import { useOg118ProjectDocuments } from '@/lib/useOg118ProjectDocuments';
import { useOg118ProjectConversations } from '@/lib/useOg118ProjectConversations';
import { relativeTime } from '@/lib/og118RelativeTime';

/** Mirrors fi-runner's MAX_OWNER_INSTRUCTIONS_CHARS: past it the server 422s. */
const MAX_INSTRUCTIONS = 4000;

export interface Og118ProjectWorkspaceProps {
  project: Og118Project;
  tokenReady: boolean;
  onBack: () => void;
  onOpenConversation: (id: string) => void;
  onStartConversation: () => void;
  onRename: (name: string) => Promise<void>;
  onDescribe: (description: string) => Promise<void>;
  onInstruct: (instructions: string) => Promise<void>;
  now?: number;
}

export function Og118ProjectWorkspace({
  project,
  tokenReady,
  onBack,
  onOpenConversation,
  onStartConversation,
  onRename,
  onDescribe,
  onInstruct,
  now,
}: Og118ProjectWorkspaceProps) {
  const docs = useOg118ProjectDocuments(project.id, tokenReady);
  const recents = useOg118ProjectConversations(project.id, tokenReady);

  return (
    <div className="og-projects-page">
      <WorkspaceBreadcrumb
        ariaLabel="Ruta"
        crumbs={[{ label: 'Proyectos', onClick: onBack }, { label: project.name }]}
      />

      <ProjectHeading project={project} onRename={onRename} onDescribe={onDescribe} />

      <WorkspaceDetailLayout
        railLabel="Conocimiento del proyecto"
        rail={
          <RailPanelStack>
            <InstructionsPanel project={project} onInstruct={onInstruct} />
            <RailPanel title="Contexto">
              {!docs.ready ? (
                <p className="og-projects-note">Leyendo el corpus…</p>
              ) : docs.failed ? (
                <p className="og-projects-note">
                  No se pudo leer el corpus. Vuelve a intentarlo.
                </p>
              ) : (
                <>
                  {docs.capacity && (
                    <CapacityMeter
                      used={docs.capacity.bytes}
                      max={docs.capacity.maxBytes}
                      label={(percent) =>
                        percent === null
                          ? `${docs.capacity!.docs} ${plural(docs.capacity!.docs, 'documento', 'documentos')} · sin límite de capacidad`
                          : `${Math.round(percent)}% de la capacidad del proyecto`
                      }
                    />
                  )}
                  <DocCardGrid
                    ariaLabel="Documentos del proyecto"
                    emptyState={
                      <p className="og-projects-note">
                        Sin documentos todavía. Súbelos desde la barra lateral para que el
                        agente pueda consultarlos.
                      </p>
                    }
                  >
                    {docs.documents.map((d) => (
                      <DocCard
                        key={d.docId}
                        title={d.docId}
                        badge="text"
                        meta={`${d.chunks} ${plural(d.chunks, 'fragmento', 'fragmentos')}`}
                      />
                    ))}
                  </DocCardGrid>
                </>
              )}
            </RailPanel>
          </RailPanelStack>
        }
      >
        <section className="og-projects-recents" aria-label="Conversaciones del proyecto">
          <div className="og-projects-recents-head">
            <h2>Conversaciones</h2>
            <button type="button" className="og-projects-cta" onClick={onStartConversation}>
              Nueva conversación
            </button>
          </div>
          {!recents.ready ? (
            <p className="og-projects-note">Cargando…</p>
          ) : recents.conversations.length === 0 ? (
            <p className="og-projects-note">
              Todavía no hay conversaciones en este proyecto. La que empieces desde aquí
              queda ligada a él.
            </p>
          ) : (
            <ul className="og-projects-recent-list">
              {recents.conversations.map((c) => (
                <li key={c.id}>
                  <button type="button" onClick={() => onOpenConversation(c.id)}>
                    <span className="og-projects-recent-title">{c.title}</span>
                    <span className="og-projects-recent-time">
                      {relativeTime(c.updatedAt, now) ?? ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </WorkspaceDetailLayout>
    </div>
  );
}

function ProjectHeading({
  project,
  onRename,
  onDescribe,
}: {
  project: Og118Project;
  onRename: (name: string) => Promise<void>;
  onDescribe: (description: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description);

  // A rename from another device (or another tab) must win over a draft nobody
  // is typing; while `editing`, the user's keystrokes win instead.
  useEffect(() => {
    if (editing) return;
    setName(project.name);
    setDescription(project.description);
  }, [project.name, project.description, editing]);

  if (!editing) {
    return (
      <header className="og-projects-heading">
        <div>
          <h1>{project.name}</h1>
          {project.description ? <p>{project.description}</p> : null}
        </div>
        <button type="button" className="og-projects-edit" onClick={() => setEditing(true)}>
          Editar
        </button>
      </header>
    );
  }

  return (
    <form
      className="og-projects-heading og-projects-heading--editing"
      onSubmit={async (e) => {
        e.preventDefault();
        // Two PATCHes only where something actually changed: sending an
        // unchanged field would move `updatedAt` and reorder the index for an
        // edit that never happened.
        if (name.trim() && name !== project.name) await onRename(name.trim());
        if (description !== project.description) await onDescribe(description);
        setEditing(false);
      }}
    >
      <label>
        <span>Nombre</span>
        <input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
      </label>
      <label>
        <span>Descripción</span>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          maxLength={500}
        />
      </label>
      <div className="og-projects-heading-actions">
        <button type="submit" className="og-projects-cta">
          Guardar
        </button>
        <button
          type="button"
          className="og-projects-edit"
          onClick={() => {
            setName(project.name);
            setDescription(project.description);
            setEditing(false);
          }}
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}

function plural(n: number, one: string, many: string): string {
  return n === 1 ? one : many;
}


function InstructionsPanel({
  project,
  onInstruct,
}: {
  project: Og118Project;
  onInstruct: (instructions: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(project.instructions);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editing) setDraft(project.instructions);
  }, [project.instructions, editing]);

  if (!editing) {
    return (
      <RailPanel
        title="Instrucciones"
        actionSlot={
          <button type="button" className="og-projects-edit" onClick={() => setEditing(true)}>
            {project.instructions ? 'Editar' : 'Añadir'}
          </button>
        }
      >
        <p className="og-projects-note og-projects-instructions-preview">
          {project.instructions ||
            'Sin instrucciones. Lo que escribas aquí viaja en cada turno de este proyecto.'}
        </p>
      </RailPanel>
    );
  }

  return (
    <RailPanel title="Instrucciones">
      <form
        className="og-projects-instructions-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          try {
            await onInstruct(draft);
            setEditing(false);
          } catch {
            // The server enforces the same ceiling and answers 422. Saying so
            // beats a silent no-op that looks like the save worked.
            setError('No se pudo guardar. Revisa que no pase de 4000 caracteres.');
          }
        }}
      >
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={6}
          maxLength={MAX_INSTRUCTIONS}
          aria-label="Instrucciones del proyecto"
          placeholder="Ej.: Contesta en español, corto, y cita siempre el documento del que sacaste el precio."
        />
        <p className="og-projects-note">
          {draft.length}/{MAX_INSTRUCTIONS} · viajan en el prompt de cada turno de este proyecto
        </p>
        {error ? <p className="og-projects-note og-projects-error">{error}</p> : null}
        <div className="og-projects-heading-actions">
          <button type="submit" className="og-projects-cta">
            Guardar
          </button>
          <button
            type="button"
            className="og-projects-edit"
            onClick={() => {
              setDraft(project.instructions);
              setError(null);
              setEditing(false);
            }}
          >
            Cancelar
          </button>
        </div>
      </form>
    </RailPanel>
  );
}
