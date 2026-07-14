'use client';

/**
 * Og118Sidebar — the app-specific chat list (DD-002B1.3).
 *
 * Pure presentation + branding over fi-glass primitives: the conversation list is
 * a fi-glass `AgentSidebarSection` (B3-FIGLASS-SHELL-PRIMITIVES-1C, the shared
 * header the projects rail also uses) and the rows are `EditableResourceItem`
 * (1A) — the section header, row anatomy, selection, inline-rename state machine
 * and hover/touch-revealed actions all live in the framework now. This consumer
 * owns ONLY the meaning: the Spanish copy, the es-MX timestamp, the delete
 * confirm, the "og118.ai" branding, and the local-storage privacy note. No
 * storage logic, no IndexedDB, no access token — those stay in the hook / token module.
 *
 * CONV-ORGANIZE-1: the list renders in three sections from core's
 * `organizeConversationSummaries` — Fijados (last-pinned first), Chats (most
 * recent first) and a collapsible Archivados (last-archived first). Archiving is
 * the gentle path: active rows offer pin/rename/archive, and the destructive
 * delete lives only inside Archivados.
 */

import { useState } from 'react';
import {
  filterConversationSummaries,
  organizeConversationSummaries,
  type ConversationSummary,
} from '@free-intelligence/core';
import {
  Archive,
  ArchiveRestore,
  ChevronDown,
  ChevronRight,
  Pin,
  PinOff,
} from 'lucide-react';
import { FI_TOUCH_TARGET_CLASS, useTouchTargetStyle } from 'fi-glass/shell';
import {
  AgentSidebarItem,
  AgentSidebarSection,
  DestructiveActionSlot,
  EditableResourceItem,
  ItemActionSlot,
  FI_SECTION_TITLE_CLASS,
} from 'fi-glass/agent';

const TITLE_MAX = 60;
const ACTION_ICON_SIZE = 14;

export interface Og118SidebarProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  onNew: () => void;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
  /** Rename a conversation; empty title reverts to the auto-derived one. */
  onRename: (id: string, title: string) => void;
  /** Pin (`true`) / unpin (`false`) a conversation. */
  onPin: (id: string, pinned: boolean) => void;
  /** Archive (`true`) / unarchive (`false`) a conversation. */
  onArchive: (id: string, archived: boolean) => void;
  /** Disable switching/new/delete while a turn streams (avoids cross-thread folds). */
  disabled?: boolean;
  /** True when the server store is authoritative (signed in) — the storage note
   * and delete-confirm copy must tell the truth about where the data lives. */
  cloud?: boolean;
  /** Account controls (e.g. the sign-out button) rendered in the sidebar footer,
   * next to the storage note — the layout home that replaced the floating pill. */
  accountSlot?: React.ReactNode;
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
  onPin,
  onArchive,
  disabled = false,
  cloud = false,
  accountSlot,
}: Og118SidebarProps) {
  // B3-FIGLASS-MOBILE-2 — the "Nuevo chat" affordance inherits the framework 44×44
  // touch minimum; the rows inherit it from EditableResourceItem's action slots.
  useTouchTargetStyle();
  const [showArchived, setShowArchived] = useState(false);
  const [query, setQuery] = useState('');

  const searching = query.trim() !== '';
  const { pinned, active, archived } = organizeConversationSummaries(
    filterConversationSummaries(conversations, query),
  );
  const noResults = searching && pinned.length + active.length + archived.length === 0;
  // While searching, an archived match must be VISIBLE, not hidden behind the
  // collapsed section — the search overrides the collapse.
  const archivedOpen = showArchived || searching;

  const chatRow = (c: ConversationSummary, isPinned: boolean) => (
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
        <>
          <ItemActionSlot
            label={isPinned ? 'Desfijar chat' : 'Fijar chat'}
            disabled={disabled}
            onActivate={() => onPin(c.id, !isPinned)}
          >
            {isPinned ? <PinOff size={ACTION_ICON_SIZE} /> : <Pin size={ACTION_ICON_SIZE} />}
          </ItemActionSlot>
          <ItemActionSlot
            label="Archivar chat"
            disabled={disabled}
            onActivate={() => onArchive(c.id, true)}
          >
            <Archive size={ACTION_ICON_SIZE} />
          </ItemActionSlot>
        </>
      }
    />
  );

  const archivedRow = (c: ConversationSummary) => (
    <AgentSidebarItem
      key={c.id}
      title={c.title}
      selected={c.id === activeId}
      onSelect={() => onSwitch(c.id)}
      subtitle={c.preview || undefined}
      meta={shortTime(c.archivedAt ?? c.updatedAt)}
      disabled={disabled}
      ariaLabel={c.title}
      actions={
        <>
          <ItemActionSlot
            label="Restaurar chat"
            disabled={disabled}
            onActivate={() => onArchive(c.id, false)}
          >
            <ArchiveRestore size={ACTION_ICON_SIZE} />
          </ItemActionSlot>
          <DestructiveActionSlot
            label="Borrar chat"
            disabled={disabled}
            onActivate={() => {
              const scope = cloud
                ? 'Se borra de tu cuenta en todos tus dispositivos.'
                : 'Solo se borra de este navegador.';
              if (window.confirm(`¿Borrar "${c.title}"? ${scope}`)) {
                onDelete(c.id);
              }
            }}
          >
            ×
          </DestructiveActionSlot>
        </>
      }
    />
  );

  return (
    <aside className="og-sidebar">
      <AgentSidebarSection
        className="og-sidebar-section"
        ariaLabel="Conversaciones"
        count={pinned.length + active.length}
        title={
          <span className={FI_SECTION_TITLE_CLASS}>
            og118<span style={{ color: 'var(--og-accent, #34d399)' }}>.ai</span>
          </span>
        }
        actionSlot={
          <button
            className={`${FI_TOUCH_TARGET_CLASS} og-sidebar-new`}
            onClick={onNew}
            disabled={disabled}
            aria-label="Nuevo chat"
          >
            + Nuevo chat
          </button>
        }
      >
        {conversations.length > 0 && (
          <input
            type="search"
            className="og-sidebar-search"
            placeholder="Buscar chats…"
            aria-label="Buscar chats"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        )}
        <nav className="og-sidebar-list">
          {noResults && (
            <p className="og-sidebar-noresults">Sin resultados para «{query.trim()}».</p>
          )}
          {pinned.length > 0 && (
            <>
              <span className="og-sidebar-group-label">Fijados</span>
              {pinned.map((c) => chatRow(c, true))}
              {active.length > 0 && (
                <span className="og-sidebar-group-label">Chats</span>
              )}
            </>
          )}
          {active.map((c) => chatRow(c, false))}
        </nav>
      </AgentSidebarSection>

      {archived.length > 0 && (
        <AgentSidebarSection
          className="og-sidebar-archived"
          ariaLabel="Archivados"
          count={archived.length}
          title={
            <span className={FI_SECTION_TITLE_CLASS}>
              Archivados ({archived.length})
            </span>
          }
          actionSlot={
            <button
              className={`${FI_TOUCH_TARGET_CLASS} og-sidebar-archive-toggle`}
              onClick={() => setShowArchived((v) => !v)}
              aria-expanded={archivedOpen}
              aria-label={archivedOpen ? 'Ocultar archivados' : 'Mostrar archivados'}
            >
              {archivedOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>
          }
        >
          {archivedOpen && (
            <nav className="og-sidebar-list og-sidebar-archived-list">
              {archived.map(archivedRow)}
            </nav>
          )}
        </AgentSidebarSection>
      )}

      <div className="og-sidebar-foot">
        <p className="og-sidebar-privacy">
          {cloud
            ? 'Sincronizado en tu cuenta — disponible en todos tus dispositivos.'
            : 'Guardado localmente en este navegador.'}
        </p>
        {accountSlot}
      </div>
    </aside>
  );
}
