'use client';

/**
 * useConversationLibrary — the reusable multi-conversation manager (DD-002B1.2).
 *
 * Wraps any ConversationLibrary (e.g. IndexedDBConversationLibrary) into the
 * state a sidebar needs: the list of summaries, the active conversation's id +
 * messages, and the lifecycle (new / switch / delete / persist). It owns the
 * conversation identity; the active id is what a consumer (og118) will reuse as
 * the backend session_id so the local transcript and the server thread share one
 * identity.
 *
 * It does NOT render anything and takes no transport/agent dependency — the app
 * composes it with `useAgentConversation` (live thread) and builds the sidebar
 * UI itself. Keeping the manager here (not in the consumer) is the framework-first
 * answer to DD-002: every future shell inherits conversation persistence.
 *
 * Privacy: every persisted record is built through core helpers
 * (`sanitizeConversationMessage` + title/preview derivation), so only
 * role/content/timestamp reach storage — never tokens, metadata, tool payloads
 * or glass-box state.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  type ChatMessage,
  type ConversationLibrary,
  type ConversationMetadataPatch,
  type ConversationRecord,
  type ConversationSummary,
  applyConversationMetadataPatch,
  conversationArchivePatch,
  conversationPinPatch,
  conversationRenamePatch,
  CONVERSATION_SCHEMA_VERSION,
  deriveConversationPreview,
  resolveConversationTitle,
  sanitizeConversationMessage,
} from '@free-intelligence/core';

export interface UseConversationLibraryOptions {
  /** Mint a new conversation id. Default: `crypto.randomUUID`. Injectable for tests. */
  idFactory?: () => string;
  /** ISO timestamp provider for createdAt/updatedAt. Default: wall clock. Injectable for tests. */
  now?: () => string;
  /**
   * The resource a NEW conversation is born into (og118 passes its active
   * project). Stamped on first persist and preserved after that.
   *
   * Deliberately birth-only: an existing conversation keeps the resource it was
   * started in, so changing the selection does not re-file the whole history
   * under whatever happens to be active right now.
   */
  projectId?: string;
}

export interface ConversationLibraryState {
  /** False until the first hydration from storage finishes. */
  ready: boolean;
  /** All conversations as light summaries, newest first (for the sidebar). */
  conversations: ConversationSummary[];
  /** The active conversation id (doubles as the backend session_id). */
  activeId: string | null;
  /** The active conversation's messages (seed for the live thread). */
  activeMessages: ChatMessage[];
  /** The active conversation's full record, or null if not yet persisted. */
  activeRecord: ConversationRecord | null;
  /** Start a fresh conversation: new id, empty thread, NOT persisted until first message. */
  newConversation: () => void;
  /** Load and activate an existing conversation by id. Throws clearly if it is gone. */
  switchConversation: (id: string) => Promise<void>;
  /** Delete a conversation; if it was active, activate the next most recent (or a fresh one). */
  deleteConversation: (id: string) => Promise<void>;
  /** Rename a conversation; an empty/whitespace title reverts to the auto-derived
   * one. A custom title survives future message persists. Throws if `id` is gone. */
  renameConversation: (id: string, title: string) => Promise<void>;
  /** Pin (`true`) or unpin (`false`) a conversation. Pinning lifts it out of the
   * archive; the pinned section orders by last-pinned first. Throws if `id` is gone. */
  pinConversation: (id: string, pinned: boolean) => Promise<void>;
  /** Archive (`true`) or unarchive (`false`) a conversation — the reversible
   * alternative to delete. Archiving clears any pin. Throws if `id` is gone. */
  archiveConversation: (id: string, archived: boolean) => Promise<void>;
  /** Persist the active conversation's messages (no-op for an empty thread). */
  persist: (messages: ChatMessage[]) => Promise<void>;
  /** Re-read the summary list from storage. */
  refresh: () => Promise<void>;
}

export function useConversationLibrary(
  library: ConversationLibrary,
  options: UseConversationLibraryOptions = {},
): ConversationLibraryState {
  const idFactory = options.idFactory ?? (() => crypto.randomUUID());
  const nowFn = options.now ?? (() => new Date().toISOString());
  const { projectId } = options;

  const [ready, setReady] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeMessages, setActiveMessages] = useState<ChatMessage[]>([]);
  const [activeRecord, setActiveRecord] = useState<ConversationRecord | null>(null);

  const refresh = useCallback(async () => {
    setConversations(await library.list());
  }, [library]);

  // Mount: hydrate from storage. Activate the most recent conversation, or seed a
  // fresh in-memory id (NOT persisted) when there is nothing stored yet.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const list = await library.list();
        if (cancelled) return;
        setConversations(list);
        if (list.length > 0) {
          const record = await library.get(list[0].id);
          if (cancelled) return;
          setActiveId(list[0].id);
          setActiveMessages(record?.messages ?? []);
          setActiveRecord(record ?? null);
        } else {
          setActiveId(idFactory());
          setActiveMessages([]);
          setActiveRecord(null);
        }
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
    // Hydrate once per library instance; idFactory is stable enough for mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [library]);

  const newConversation = useCallback(() => {
    setActiveId(idFactory());
    setActiveMessages([]);
    setActiveRecord(null);
  }, [idFactory]);

  const switchConversation = useCallback(
    async (id: string) => {
      const record = await library.get(id);
      if (!record) {
        // Stale summary (record deleted elsewhere): refresh and surface clearly.
        await refresh();
        throw new Error(
          `useConversationLibrary: conversation "${id}" not found`,
        );
      }
      setActiveId(id);
      setActiveMessages(record.messages);
      setActiveRecord(record);
    },
    [library, refresh],
  );

  const persist = useCallback(
    async (messages: ChatMessage[]) => {
      // Never persist an empty thread — a brand-new conversation stays in-memory
      // until its first real message.
      if (messages.length === 0) return;
      const id = activeId ?? idFactory();
      const now = nowFn();
      // Preserve createdAt when updating the same record; otherwise it's new.
      const prevForTitle = activeRecord?.id === id ? activeRecord : undefined;
      const createdAt = prevForTitle ? prevForTitle.createdAt : now;
      const clean = messages.map(sanitizeConversationMessage);
      // Birth-only, and the discriminator is the RECORD's existence, not whether
      // it happens to carry a value. `prev?.projectId ?? projectId` reads the
      // same and is wrong: a conversation started with nothing selected would
      // adopt whatever project got selected later, silently re-filing a thread
      // the user never moved.
      const bornIn = prevForTitle ? prevForTitle.projectId : projectId;
      const record: ConversationRecord = {
        id,
        title: resolveConversationTitle(clean, prevForTitle),
        titleCustom: prevForTitle?.titleCustom,
        createdAt,
        updatedAt: now,
        messages: clean,
        preview: deriveConversationPreview(clean),
        // Organization flags ride along for the SINGLE-WRITER (IndexedDB) store,
        // where nothing else preserves them. A shared store ignores what a put
        // says about them and keeps its own — a device with a stale copy is not
        // allowed to have an opinion here, which is what closes the race.
        ...(prevForTitle?.pinnedAt ? { pinnedAt: prevForTitle.pinnedAt } : {}),
        ...(prevForTitle?.archivedAt ? { archivedAt: prevForTitle.archivedAt } : {}),
        ...(bornIn ? { projectId: bornIn } : {}),
        schemaVersion: CONVERSATION_SCHEMA_VERSION,
      };
      await library.put(record);
      setActiveId(id);
      setActiveMessages(record.messages);
      setActiveRecord(record);
      await refresh();
    },
    [activeId, activeRecord, idFactory, nowFn, library, refresh, projectId],
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      await library.delete(id);
      const list = await library.list();
      setConversations(list);
      if (id !== activeId) return;
      // Deleted the active one: fall back to the next most recent, or a fresh id.
      if (list.length > 0) {
        const record = await library.get(list[0].id);
        setActiveId(list[0].id);
        setActiveMessages(record?.messages ?? []);
        setActiveRecord(record ?? null);
      } else {
        setActiveId(idFactory());
        setActiveMessages([]);
        setActiveRecord(null);
      }
    },
    [library, activeId, idFactory],
  );

  // Shared metadata-mutation seam for rename/pin/archive.
  //
  // The delta — not the whole record — is what travels when the backing store
  // offers `patch`. A shared cloud store has a second writer (the same account
  // on a phone and a desktop), and a whole-record write from whichever side
  // holds the older copy silently drops the flags it never knew about: pin on
  // the phone, send a message from the desktop, pin gone, nothing reported.
  // A delta carries no opinion about what it does not name, so there is
  // nothing left to drop. A single-browser store has no second writer, so the
  // read-apply-write below stays correct there and needs no extra verb.
  const mutateMetadata = useCallback(
    async (
      id: string,
      patchOf: (record: ConversationRecord) => ConversationMetadataPatch,
    ) => {
      const record = await library.get(id);
      if (!record) {
        // Stale summary (deleted elsewhere): refresh and surface clearly.
        await refresh();
        throw new Error(
          `useConversationLibrary: conversation "${id}" not found`,
        );
      }
      const patch = patchOf(record);
      let next: ConversationRecord | null;
      if (library.patch) {
        next = await library.patch(id, patch);
        if (!next) {
          // Deleted between the read and the write, from the other device.
          await refresh();
          throw new Error(
            `useConversationLibrary: conversation "${id}" not found`,
          );
        }
      } else {
        next = applyConversationMetadataPatch(record, patch);
        await library.put(next);
      }
      if (id === activeId) {
        setActiveRecord(next);
        setActiveMessages(next.messages);
      }
      await refresh();
    },
    [library, activeId, refresh],
  );

  const renameConversation = useCallback(
    async (id: string, title: string) =>
      mutateMetadata(id, (record) => conversationRenamePatch(record, title, nowFn())),
    [mutateMetadata, nowFn],
  );

  const pinConversation = useCallback(
    async (id: string, pinned: boolean) =>
      mutateMetadata(id, () => conversationPinPatch(pinned, nowFn())),
    [mutateMetadata, nowFn],
  );

  const archiveConversation = useCallback(
    async (id: string, archived: boolean) =>
      mutateMetadata(id, () => conversationArchivePatch(archived, nowFn())),
    [mutateMetadata, nowFn],
  );

  return {
    ready,
    conversations,
    activeId,
    activeMessages,
    activeRecord,
    newConversation,
    switchConversation,
    deleteConversation,
    renameConversation,
    pinConversation,
    archiveConversation,
    persist,
    refresh,
  };
}
