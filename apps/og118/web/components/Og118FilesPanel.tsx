'use client';

/**
 * Og118FilesPanel — the sidebar's "Archivos" entry and its sheet: what the
 * account's chats saved through `save_file`, each one downloadable and deletable.
 */

import { useId, useState } from 'react';
import { Download, FolderOpen, Trash2, X } from 'lucide-react';
import { AdminAlert, AdminButton, AdminSheet } from 'fi-glass/admin-kit';
import { FI_TOUCH_TARGET_CLASS } from 'fi-glass/shell';
import { formatBytes, useOg118Files, type Og118File } from '../lib/useOg118Files';
import { shortTime } from './Og118Sidebar';

export interface Og118FilesPanelProps {
  /** False until the account's token is usable; the entry stays hidden until then. */
  enabled: boolean;
  /** Title of the chat a file was saved from, when that chat still exists. */
  conversationTitle?: (conversationId: string) => string | undefined;
}

export function Og118FilesPanel({ enabled, conversationTitle }: Og118FilesPanelProps) {
  const [open, setOpen] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const titleId = useId();
  const store = useOg118Files(enabled && open);

  if (!enabled) return null;

  const download = async (file: Og118File) => {
    setProblem((await store.download(file)) ? null : `No se pudo bajar «${file.name}».`);
  };
  const remove = async (file: Og118File) => {
    if (!window.confirm(`¿Borrar «${file.name}»? Se borra de tu cuenta y no se puede recuperar.`)) return;
    setProblem((await store.remove(file)) ? null : `No se pudo borrar «${file.name}».`);
  };

  return (
    <>
      <button
        type="button"
        className={`${FI_TOUCH_TARGET_CLASS} og-files-open`}
        onClick={() => setOpen(true)}
      >
        <FolderOpen size={14} aria-hidden="true" />
        Archivos
      </button>
      {open && (
        <AdminSheet
          onDismiss={() => setOpen(false)}
          labelledBy={titleId}
          className="og-files"
          header={
            <div className="og-files-head">
              <div>
                <h2 id={titleId} className="og-files-title">
                  Archivos
                </h2>
                {store.ready && !store.failed && (
                  <p className="og-files-usage">
                    {formatBytes(store.usedBytes)} de {formatBytes(store.quotaBytes)} usados
                  </p>
                )}
              </div>
              <AdminButton variant="ghost" icon={X} iconOnly aria-label="Cerrar" onClick={() => setOpen(false)} />
            </div>
          }
        >
          {problem && <AdminAlert>{problem}</AdminAlert>}
          {store.failed && (
            <AdminAlert action={<AdminButton onClick={store.refresh}>Reintentar</AdminButton>}>
              No se pudieron cargar tus archivos.
            </AdminAlert>
          )}
          {!store.ready && !store.failed && <p className="og-files-empty">Cargando…</p>}
          {store.ready && !store.failed && store.files.length === 0 && (
            <p className="og-files-empty">
              Todavía no hay archivos. Pídele a un chat que guarde algo y aparecerá aquí.
            </p>
          )}
          <ul className="og-files-list">
            {store.files.map((file) => {
              const chat = file.conversationId ? conversationTitle?.(file.conversationId) : undefined;
              return (
                <li key={file.id} className="og-files-row">
                  <div className="og-files-row-text">
                    <span className="og-files-name">{file.name}</span>
                    <span className="og-files-meta">
                      {formatBytes(file.size)} · {shortTime(file.createdAt)}
                      {chat ? ` · ${chat}` : ''}
                    </span>
                  </div>
                  <AdminButton
                    variant="ghost"
                    icon={Download}
                    iconOnly
                    aria-label={`Bajar ${file.name}`}
                    onClick={() => void download(file)}
                  />
                  <AdminButton
                    variant="ghost"
                    tone="danger"
                    icon={Trash2}
                    iconOnly
                    aria-label={`Borrar ${file.name}`}
                    onClick={() => void remove(file)}
                  />
                </li>
              );
            })}
          </ul>
        </AdminSheet>
      )}
    </>
  );
}
