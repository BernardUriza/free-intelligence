'use client';

/**
 * Og118Sidebar — the app-specific chat list (DD-002B1.3).
 *
 * Pure presentation + branding over fi-glass primitives: the conversation rows are
 * fi-glass `EditableResourceItem` (B3-FIGLASS-SHELL-PRIMITIVES-1A) — the row
 * anatomy, selection, inline-rename state machine and hover/touch-revealed actions
 * live in the framework now. This consumer owns ONLY the meaning: the Spanish copy,
 * the es-MX timestamp, the delete confirm, and the "og118.ai" header. No storage
 * logic, no IndexedDB, no access token — those stay in the hook / token module.
 */

import type { ConversationSummary } from '@free-intelligence/core';
import { FI_TOUCH_TARGET_CLASS, useTouchTargetStyle } from 'fi-glass/shell';
import { DestructiveActionSlot, EditableResourceItem } from 'fi-glass/agent';

const TITLE_MAX = 60;

export interface Og118SidebarProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  onNew: () => void;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
  /** Rename a conversation; empty title reverts to the auto-derived one. */
  onRename: (id: string, title: string) => void;
  /** Disable switching/new/delete while a turn streams (avoids cross-thread folds). */
  disabled?: boolean;
}

export function shortTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  // Pinned to es-MX 24h (B3-OG118-5): the UI copy is Spanish, so the date must
  // not follow the browser locale ("Jun 11, 12:18 AM" on an English browser).
  return d.toLocaleString('es-MX', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  });
}

export function Og118Sidebar({
  conversations,
  activeId,
  onNew,
  onSwitch,
  onDelete,
  onRename,
  disabled = false,
}: Og118SidebarProps) {
  // B3-FIGLASS-MOBILE-2 — the "Nuevo chat" affordance inherits the framework 44×44
  // touch minimum; the rows inherit it from EditableResourceItem's action slots.
  useTouchTargetStyle();

  return (
    <aside className="og-sidebar">
      <div className="og-sidebar-head">
        <span className="og-sidebar-title">
          og118<span style={{ color: 'var(--og-accent, #34d399)' }}>.ai</span>
        </span>
        <button
          className={`${FI_TOUCH_TARGET_CLASS} og-sidebar-new`}
          onClick={onNew}
          disabled={disabled}
          aria-label="Nuevo chat"
        >
          + Nuevo chat
        </button>
      </div>

      <nav className="og-sidebar-list">
        {conversations.map((c) => (
          <EditableResourceItem
            key={c.id}
            title={c.title}
            selected={c.id === activeId}
            onSelect={() => onSwitch(c.id)}
            onRename={(title) => onRename(c.id, title)}
            subtitle={c.preview || undefined}
            meta={shortTime(c.updatedAt)}
            disabled={disabled}
            maxLength={TITLE_MAX}
            renameLabel="Renombrar chat"
            renameInputLabel="Nombre del chat"
            ariaLabel={c.title}
            actions={
              <DestructiveActionSlot
                label="Borrar chat"
                disabled={disabled}
                onActivate={() => {
                  if (
                    window.confirm(`¿Borrar "${c.title}"? Solo se borra de este navegador.`)
                  ) {
                    onDelete(c.id);
                  }
                }}
              >
                ×
              </DestructiveActionSlot>
            }
          />
        ))}
      </nav>

      <p className="og-sidebar-privacy">Guardado localmente en este navegador.</p>
    </aside>
  );
}
