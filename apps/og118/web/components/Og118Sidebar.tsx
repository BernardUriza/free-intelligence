'use client';

/**
 * Og118Sidebar — the app-specific chat list (DD-002B1.3).
 *
 * Pure presentation + branding: it renders the conversation summaries the
 * fi-glass `useConversationLibrary` hook owns and routes clicks back to the
 * library's actions. It has NO storage logic and never touches IndexedDB or the
 * access token — those stay in the hook / token module. This is the consumer's
 * legitimate slice: layout, copy, and the "Nuevo chat" affordance.
 */

import type { ConversationSummary } from '@free-intelligence/core';

export interface Og118SidebarProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  onNew: () => void;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
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
  disabled = false,
}: Og118SidebarProps) {
  return (
    <aside className="og-sidebar">
      <div className="og-sidebar-head">
        <span className="og-sidebar-title">
          og118<span style={{ color: 'var(--og-accent, #34d399)' }}>.ai</span>
        </span>
        <button
          className="og-sidebar-new"
          onClick={onNew}
          disabled={disabled}
          aria-label="Nuevo chat"
        >
          + Nuevo chat
        </button>
      </div>

      <nav className="og-sidebar-list">
        {conversations.map((c) => {
          const active = c.id === activeId;
          return (
            <div
              key={c.id}
              className={`og-chat-item${active ? ' is-active' : ''}`}
              role="button"
              tabIndex={0}
              aria-current={active}
              onClick={() => !disabled && !active && onSwitch(c.id)}
              onKeyDown={(e) => {
                if ((e.key === 'Enter' || e.key === ' ') && !disabled && !active) {
                  e.preventDefault();
                  onSwitch(c.id);
                }
              }}
            >
              <div className="og-chat-item-main">
                <span className="og-chat-item-title">{c.title}</span>
                {c.preview && <span className="og-chat-item-preview">{c.preview}</span>}
                <span className="og-chat-item-time">{shortTime(c.updatedAt)}</span>
              </div>
              <button
                className="og-chat-item-del"
                aria-label="Borrar chat"
                disabled={disabled}
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm(`¿Borrar "${c.title}"? Solo se borra de este navegador.`)) {
                    onDelete(c.id);
                  }
                }}
              >
                ×
              </button>
            </div>
          );
        })}
      </nav>

      <p className="og-sidebar-privacy">Guardado localmente en este navegador.</p>
    </aside>
  );
}
