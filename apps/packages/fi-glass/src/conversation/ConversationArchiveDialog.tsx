'use client';

// Pick many chats and archive them at once, on the native <dialog> (focus trap, Escape,
// backdrop for free). Archive is reversible, so everything but pinned starts selected.

import { useEffect, useInsertionEffect, useRef, useState, type ReactNode } from 'react';
import type { ConversationSummary } from '@free-intelligence/core';
import { FI_MOBILE_QUERY } from '../theme/breakpoints';
import { glassTokens } from '../theme/glass-tokens.generated';
import { ensureTouchTargetStyle, withTouchTarget } from '../shell/touchTarget';

export interface ConversationArchiveDialogLabels {
  title: string;
  selectAll: string;
  selectNone: string;
  cancel: string;
  /** The confirm button for `n` selected chats. */
  archive: (n: number) => string;
  /** Shown after a partial failure: `failed` chats out of `total` could not be archived. */
  failed: (failed: number, total: number) => string;
  empty: string;
}

const DEFAULT_LABELS: ConversationArchiveDialogLabels = {
  title: 'Archivar chats',
  selectAll: 'Seleccionar todos',
  selectNone: 'Quitar selección',
  cancel: 'Cancelar',
  archive: (n) => (n === 1 ? 'Archivar 1 chat' : `Archivar ${n} chats`),
  failed: (failed, total) =>
    `${failed} de ${total} no se pudieron archivar. Los que fallaron siguen marcados: vuelve a intentarlo.`,
  empty: 'No hay chats para archivar.',
};

export interface ConversationArchiveDialogProps {
  open: boolean;
  /** The candidates: pass the chats that are NOT archived yet. */
  conversations: ConversationSummary[];
  /** Archive these ids; resolve with the ids that failed (see `archiveConversations`). */
  onArchive: (ids: string[]) => Promise<string[]>;
  onClose: () => void;
  /** Secondary line per row (e.g. a formatted date). Omit for title only. */
  renderMeta?: (conversation: ConversationSummary) => ReactNode;
  labels?: Partial<ConversationArchiveDialogLabels>;
}

export const FI_ARCHIVE_DIALOG_CLASS = 'fi-archive-dialog';
const STYLE_ID = 'fi-archive-dialog-style';

const CSS = `
.${FI_ARCHIVE_DIALOG_CLASS} {
  width: min(30rem, calc(100vw - 1.5rem));
  max-height: min(36rem, calc(100dvh - 3rem));
  padding: 0;
  border: 1px solid var(--glass-chat-surface-border, ${glassTokens.surfaceBorder});
  border-radius: 16px;
  background: var(--fi-archive-dialog-bg, ${glassTokens.bgMid});
  color: var(--glass-chat-text, ${glassTokens.text});
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
}
.${FI_ARCHIVE_DIALOG_CLASS}[open] {
  display: flex;
  flex-direction: column;
}
.${FI_ARCHIVE_DIALOG_CLASS}::backdrop {
  background: rgba(2, 6, 23, 0.6);
  backdrop-filter: blur(4px);
}
.fi-archive-dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem 1rem 0.5rem;
}
.fi-archive-dialog-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}
.fi-archive-dialog-toggle,
.fi-archive-dialog-cancel {
  padding: 0.45rem 0.75rem;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
  font-size: 0.82rem;
  cursor: pointer;
}
.fi-archive-dialog-toggle:hover,
.fi-archive-dialog-cancel:hover {
  background: var(--fi-sidebar-item-hover-bg, ${glassTokens.itemHover});
  color: var(--glass-chat-text, ${glassTokens.text});
}
.fi-archive-dialog-list {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 0 0.5rem;
  overflow-y: auto;
  list-style: none;
}
.fi-archive-dialog-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-height: var(--fi-touch-target, 44px);
  padding: 0.4rem 0.5rem;
  border-radius: 10px;
  cursor: pointer;
}
.fi-archive-dialog-row:hover {
  background: var(--fi-sidebar-item-hover-bg, ${glassTokens.itemHover});
}
.fi-archive-dialog-row input {
  flex-shrink: 0;
  width: 1.1rem;
  height: 1.1rem;
  accent-color: var(--fi-accent, ${glassTokens.accent});
}
.fi-archive-dialog-row-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.fi-archive-dialog-row-title {
  overflow: hidden;
  font-size: 0.9rem;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.fi-archive-dialog-row-meta {
  font-size: 0.75rem;
  color: var(--fi-sidebar-item-meta-color, ${glassTokens.itemMeta});
}
.fi-archive-dialog-empty {
  padding: 1.5rem 1rem;
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
}
.fi-archive-dialog-error {
  margin: 0.5rem 1rem 0;
  font-size: 0.82rem;
  color: var(--fi-sidebar-item-danger, ${glassTokens.danger});
}
.fi-archive-dialog-foot {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 1rem calc(0.75rem + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--glass-chat-surface-border, ${glassTokens.surfaceBorder});
}
.fi-archive-dialog-confirm {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 10px;
  background: var(--fi-accent, ${glassTokens.accent});
  color: var(--fi-archive-dialog-confirm-text, ${glassTokens.authorAgentText});
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}
.fi-archive-dialog-confirm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
@media ${FI_MOBILE_QUERY} {
  .${FI_ARCHIVE_DIALOG_CLASS} {
    width: 100vw;
    max-width: 100vw;
    height: 100dvh;
    max-height: 100dvh;
    margin: 0;
    border: none;
    border-radius: 0;
    padding-top: env(safe-area-inset-top, 0px);
  }
}
`;

/** Inject the idempotent archive-dialog stylesheet (no-op on the server / if already present). */
export function ensureArchiveDialogStyle(): void {
  if (typeof document === 'undefined') return;
  ensureTouchTargetStyle();
  if (document.getElementById(STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

const initialSelection = (conversations: ConversationSummary[]) =>
  new Set(conversations.filter((c) => !c.pinnedAt).map((c) => c.id));

export function ConversationArchiveDialog({
  open,
  conversations,
  onArchive,
  onClose,
  renderMeta,
  labels: labelOverrides,
}: ConversationArchiveDialogProps) {
  useInsertionEffect(() => {
    ensureArchiveDialogStyle();
  }, []);
  const labels = { ...DEFAULT_LABELS, ...labelOverrides };
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState<Set<string>>(() => initialSelection(conversations));
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<{ failed: number; total: number } | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setSelected(initialSelection(conversations));
      setFailure(null);
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
    // Re-seed the selection only when the dialog opens, not on every list refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const selectedIds = conversations.filter((c) => selected.has(c.id)).map((c) => c.id);
  const allSelected = conversations.length > 0 && selectedIds.length === conversations.length;
  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const confirm = async () => {
    const ids = selectedIds;
    if (ids.length === 0) return;
    setBusy(true);
    setFailure(null);
    const failed = await onArchive(ids);
    setBusy(false);
    if (failed.length === 0) {
      onClose();
      return;
    }
    setSelected(new Set(failed));
    setFailure({ failed: failed.length, total: ids.length });
  };

  return (
    <dialog
      ref={dialogRef}
      className={FI_ARCHIVE_DIALOG_CLASS}
      aria-labelledby="fi-archive-dialog-title"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <div className="fi-archive-dialog-head">
        <h2 id="fi-archive-dialog-title" className="fi-archive-dialog-title">
          {labels.title}
        </h2>
        {conversations.length > 0 && (
          <button
            type="button"
            className={withTouchTarget('fi-archive-dialog-toggle')}
            onClick={() =>
              setSelected(allSelected ? new Set() : new Set(conversations.map((c) => c.id)))
            }
            disabled={busy}
          >
            {allSelected ? labels.selectNone : labels.selectAll}
          </button>
        )}
      </div>
      {conversations.length === 0 ? (
        <p className="fi-archive-dialog-empty">{labels.empty}</p>
      ) : (
        <ul className="fi-archive-dialog-list">
          {conversations.map((c) => (
            <li key={c.id}>
              <label className="fi-archive-dialog-row">
                <input
                  type="checkbox"
                  checked={selected.has(c.id)}
                  onChange={() => toggle(c.id)}
                  disabled={busy}
                />
                <span className="fi-archive-dialog-row-body">
                  <span className="fi-archive-dialog-row-title">{c.title}</span>
                  {renderMeta && (
                    <span className="fi-archive-dialog-row-meta">{renderMeta(c)}</span>
                  )}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      {failure && (
        <p className="fi-archive-dialog-error" role="alert">
          {labels.failed(failure.failed, failure.total)}
        </p>
      )}
      <div className="fi-archive-dialog-foot">
        <button
          type="button"
          className={withTouchTarget('fi-archive-dialog-cancel')}
          onClick={onClose}
          disabled={busy}
        >
          {labels.cancel}
        </button>
        <button
          type="button"
          className={withTouchTarget('fi-archive-dialog-confirm')}
          onClick={() => void confirm()}
          disabled={busy || selectedIds.length === 0}
        >
          {labels.archive(selectedIds.length)}
        </button>
      </div>
    </dialog>
  );
}
