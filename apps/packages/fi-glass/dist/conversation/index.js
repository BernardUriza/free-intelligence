'use client';

// src/conversation/EphemeralConversationLibrary.ts
var EphemeralConversationLibrary = class {
  constructor() {
    this.records = /* @__PURE__ */ new Map();
  }
  async list() {
    return [...this.records.values()].map(({ messages: _messages, ...summary }) => summary).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }
  async get(id) {
    const found = this.records.get(id);
    return found ? structuredClone(found) : null;
  }
  async put(record) {
    this.records.set(record.id, structuredClone(record));
  }
  async delete(id) {
    this.records.delete(id);
  }
  async clear() {
    this.records.clear();
  }
};

// src/conversation/IndexedDBConversationLibrary.ts
import { summarizeConversation } from "@free-intelligence/core";
var DEFAULT_DB_NAME = "free-intelligence-conversations";
var DEFAULT_STORE_NAME = "conversations";
var DB_VERSION = 1;
var UPDATED_AT_INDEX = "by_updatedAt";
function indexedDBUnavailable() {
  return typeof indexedDB === "undefined";
}
function unavailableError() {
  return new Error(
    "IndexedDBConversationLibrary: IndexedDB is not available in this environment (server-side render or storage disabled). Use this adapter only in the browser."
  );
}
var IndexedDBConversationLibrary = class {
  constructor(options = {}) {
    this.dbPromise = null;
    this.dbName = options.dbName ?? DEFAULT_DB_NAME;
    this.storeName = options.storeName ?? DEFAULT_STORE_NAME;
  }
  /** Open (and lazily create) the database. Rejects clearly if unavailable. */
  open() {
    if (indexedDBUnavailable()) return Promise.reject(unavailableError());
    if (!this.dbPromise) {
      this.dbPromise = new Promise((resolve, reject) => {
        const request = indexedDB.open(this.dbName, DB_VERSION);
        request.onupgradeneeded = () => {
          const db = request.result;
          if (!db.objectStoreNames.contains(this.storeName)) {
            const store = db.createObjectStore(this.storeName, { keyPath: "id" });
            store.createIndex(UPDATED_AT_INDEX, "updatedAt", { unique: false });
          }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error ?? new Error("IndexedDB open failed"));
      });
    }
    return this.dbPromise;
  }
  /** Run one request inside a transaction and resolve with its result. */
  async run(mode, makeRequest) {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, mode);
      const request = makeRequest(transaction.objectStore(this.storeName));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error ?? new Error("IndexedDB request failed"));
    });
  }
  /** All conversations as light summaries, newest `updatedAt` first. */
  async list() {
    const records = await this.run(
      "readonly",
      (store) => store.getAll()
    );
    return records.map(summarizeConversation).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }
  /** The full record for `id`, or `null` if none. */
  async get(id) {
    const record = await this.run(
      "readonly",
      (store) => store.get(id)
    );
    return record ?? null;
  }
  /** Insert or replace a record by its `id`. */
  async put(record) {
    await this.run("readwrite", (store) => store.put(record));
  }
  /** Remove the record for `id` (no-op if absent). */
  async delete(id) {
    await this.run("readwrite", (store) => store.delete(id));
  }
  /** Remove every stored conversation. */
  async clear() {
    await this.run("readwrite", (store) => store.clear());
  }
};

// src/conversation/RemoteConversationLibrary.ts
var RemoteConversationLibrary = class _RemoteConversationLibrary {
  constructor(options) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.headers = options.headers ?? (() => ({}));
    this.fetchImpl = options.fetchImpl ?? fetch.bind(globalThis);
  }
  async request(method, path, body) {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method,
      headers: {
        ...body !== void 0 ? { "Content-Type": "application/json" } : {},
        ...this.headers()
      },
      ...body !== void 0 ? { body: JSON.stringify(body) } : {}
    });
    return response;
  }
  static async fail(operation, response) {
    throw new Error(
      `RemoteConversationLibrary.${operation} failed: HTTP ${response.status}`
    );
  }
  async list() {
    const response = await this.request("GET", "/conversations");
    if (!response.ok) await _RemoteConversationLibrary.fail("list", response);
    const data = await response.json();
    return data.conversations;
  }
  async get(id) {
    const response = await this.request(
      "GET",
      `/conversations/${encodeURIComponent(id)}`
    );
    if (response.status === 404) return null;
    if (!response.ok) await _RemoteConversationLibrary.fail("get", response);
    return await response.json();
  }
  async put(record) {
    const response = await this.request(
      "PUT",
      `/conversations/${encodeURIComponent(record.id)}`,
      record
    );
    if (!response.ok) await _RemoteConversationLibrary.fail("put", response);
  }
  /**
   * Send a metadata delta instead of the whole record.
   *
   * Implemented HERE and not on the IndexedDB adapter because this is the
   * adapter with a second writer: the same account on a phone and a desktop
   * both write this store. A whole-record `put` from whichever device holds the
   * older copy drops the flags it never knew about — the delta carries no
   * opinion about anything it does not name, so there is nothing to drop.
   *
   * Returns the server's merged record (it owns the merge), or `null` if the
   * conversation is gone — deleted from the other device, the same shape `get`
   * already reports.
   */
  async patch(id, patch) {
    const response = await this.request(
      "PATCH",
      `/conversations/${encodeURIComponent(id)}`,
      patch
    );
    if (response.status === 404) return null;
    if (!response.ok) await _RemoteConversationLibrary.fail("patch", response);
    return await response.json();
  }
  async delete(id) {
    const response = await this.request(
      "DELETE",
      `/conversations/${encodeURIComponent(id)}`
    );
    if (!response.ok) await _RemoteConversationLibrary.fail("delete", response);
  }
  async clear() {
    const response = await this.request("DELETE", "/conversations");
    if (!response.ok) await _RemoteConversationLibrary.fail("clear", response);
  }
};

// src/conversation/migrateConversationLibrary.ts
import {
  deriveConversationPreview,
  resolveConversationTitle
} from "@free-intelligence/core";
function messageKey(message) {
  return `${message.role}\0${message.timestamp ?? ""}\0${message.content}`;
}
function mergeConversationRecords(target, source) {
  const known = new Set(target.messages.map(messageKey));
  const missing = source.messages.filter((m) => !known.has(messageKey(m)));
  if (missing.length === 0) return target;
  const messages = [...target.messages, ...missing].map((message, order) => ({ message, order })).sort((a, b) => (a.message.timestamp ?? "").localeCompare(b.message.timestamp ?? "") || a.order - b.order).map(({ message }) => message);
  return {
    ...target,
    messages,
    title: resolveConversationTitle(messages, target),
    preview: deriveConversationPreview(messages),
    updatedAt: source.updatedAt > target.updatedAt ? source.updatedAt : target.updatedAt
  };
}
async function migrateConversationLibrary(source, target) {
  const [sourceList, targetList] = await Promise.all([source.list(), target.list()]);
  const existing = new Map(targetList.map((summary) => [summary.id, summary]));
  let migrated = 0;
  let merged = 0;
  let skipped = 0;
  for (const summary of sourceList) {
    const theirs = existing.get(summary.id);
    if (theirs && summary.updatedAt <= theirs.updatedAt) {
      skipped += 1;
      continue;
    }
    const record = await source.get(summary.id);
    if (!record) continue;
    if (!theirs) {
      await target.put(record);
      migrated += 1;
      continue;
    }
    const current = await target.get(summary.id);
    const next = current ? mergeConversationRecords(current, record) : record;
    if (next === current) {
      skipped += 1;
      continue;
    }
    await target.put(next);
    merged += 1;
  }
  return { migrated, merged, skipped };
}

// src/conversation/useConversationLibrary.ts
import { useCallback, useEffect, useRef, useState } from "react";
import {
  applyConversationMetadataPatch,
  conversationArchivePatch,
  conversationPinPatch,
  conversationRenamePatch,
  CONVERSATION_SCHEMA_VERSION,
  deriveConversationPreview as deriveConversationPreview2,
  resolveConversationTitle as resolveConversationTitle2,
  sanitizeConversationMessage
} from "@free-intelligence/core";
var ARCHIVE_BATCH_CONCURRENCY = 4;
function useConversationLibrary(library, options = {}) {
  const idFactory = options.idFactory ?? (() => crypto.randomUUID());
  const nowFn = options.now ?? (() => (/* @__PURE__ */ new Date()).toISOString());
  const { projectId } = options;
  const [ready, setReady] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [activeMessages, setActiveMessages] = useState([]);
  const [activeRecord, setActiveRecord] = useState(null);
  const activeIdRef = useRef(activeId);
  activeIdRef.current = activeId;
  const activeRecordRef = useRef(activeRecord);
  activeRecordRef.current = activeRecord;
  const claimedId = useRef(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [actionError, setActionError] = useState(null);
  const failedRun = useRef(null);
  const guard = useCallback(async function guarded(action, conversationId, run) {
    try {
      await run();
      setActionError(
        (prev) => prev?.action === action && prev.conversationId === conversationId ? null : prev
      );
    } catch (cause) {
      failedRun.current = () => guarded(action, conversationId, run);
      setActionError({
        action,
        conversationId,
        message: cause instanceof Error && cause.message ? cause.message : String(cause),
        cause
      });
      throw cause;
    }
  }, []);
  const retryAction = useCallback(() => {
    const again = failedRun.current;
    if (!again) return;
    failedRun.current = null;
    setActionError(null);
    void again().catch(() => {
    });
  }, []);
  const dismissActionError = useCallback(() => {
    failedRun.current = null;
    setActionError(null);
  }, []);
  const refresh = useCallback(async () => {
    setConversations(await library.list());
  }, [library]);
  useEffect(() => {
    let cancelled = false;
    const isCurrent = (id) => !cancelled && activeIdRef.current === id;
    const adopt = (id, record) => {
      setActiveId(id);
      setActiveMessages(record?.messages ?? []);
      setActiveRecord(record);
    };
    void (async () => {
      const current = activeIdRef.current;
      try {
        const list = await library.list();
        if (cancelled) return;
        setConversations(list);
        const previous = activeRecordRef.current;
        if (current && list.some((summary) => summary.id === current)) {
          const stored = await library.get(current);
          if (!isCurrent(current) || !stored) return;
          const carried = previous?.id === current ? mergeConversationRecords(stored, previous) : stored;
          if (carried !== stored) await library.put(carried);
          if (isCurrent(current)) adopt(current, carried);
          return;
        }
        if (current && claimedId.current === current) {
          if (previous?.id === current) await library.put(previous);
          return;
        }
        if (list.length > 0) {
          const record = await library.get(list[0].id);
          if (isCurrent(current)) adopt(list[0].id, record ?? null);
        } else if (isCurrent(current) && (current === null || previous !== null)) {
          adopt(idFactory(), null);
        }
      } catch (cause) {
        if (cancelled) return;
        failedRun.current = async () => setLoadAttempt((n) => n + 1);
        setActionError({
          action: "load",
          conversationId: current ?? "",
          message: cause instanceof Error && cause.message ? cause.message : String(cause),
          cause
        });
        if (activeIdRef.current === null) adopt(idFactory(), null);
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [library, loadAttempt]);
  const claimActive = useCallback((conversationId) => {
    claimedId.current = conversationId ?? activeIdRef.current;
  }, []);
  const newConversation = useCallback(() => {
    setActiveId(idFactory());
    setActiveMessages([]);
    setActiveRecord(null);
  }, [idFactory]);
  const switchConversation = useCallback(
    async (id) => {
      const record = await library.get(id);
      if (!record) {
        await refresh();
        throw new Error(
          `useConversationLibrary: conversation "${id}" not found`
        );
      }
      setActiveId(id);
      setActiveMessages(record.messages);
      setActiveRecord(record);
    },
    [library, refresh]
  );
  const reloadActive = useCallback(async () => {
    const id = activeId;
    if (!id) return;
    const record = await library.get(id);
    if (activeIdRef.current !== id) return;
    if (!record) {
      if (!activeRecord) return;
      await refresh();
      throw new Error(
        `useConversationLibrary: conversation "${id}" not found`
      );
    }
    if (record.updatedAt === activeRecord?.updatedAt) return;
    setActiveRecord(record);
    setActiveMessages(record.messages);
    await refresh();
  }, [library, activeId, activeRecord, refresh]);
  const persist = useCallback(
    async (messages, conversationId) => {
      if (messages.length === 0) return;
      const id = conversationId ?? activeIdRef.current ?? idFactory();
      const now = nowFn();
      const held = activeRecordRef.current;
      const prevForTitle = held?.id === id ? held : id === activeIdRef.current ? void 0 : await library.get(id) ?? void 0;
      const createdAt = prevForTitle ? prevForTitle.createdAt : now;
      const clean = messages.map(sanitizeConversationMessage);
      const bornIn = prevForTitle ? prevForTitle.projectId : projectId;
      const record = {
        id,
        title: resolveConversationTitle2(clean, prevForTitle),
        titleCustom: prevForTitle?.titleCustom,
        createdAt,
        updatedAt: now,
        messages: clean,
        preview: deriveConversationPreview2(clean),
        // Organization flags ride along for the SINGLE-WRITER (IndexedDB) store,
        // where nothing else preserves them. A shared store ignores what a put
        // says about them and keeps its own — a device with a stale copy is not
        // allowed to have an opinion here, which is what closes the race.
        ...prevForTitle?.pinnedAt ? { pinnedAt: prevForTitle.pinnedAt } : {},
        ...prevForTitle?.archivedAt ? { archivedAt: prevForTitle.archivedAt } : {},
        ...bornIn ? { projectId: bornIn } : {},
        schemaVersion: CONVERSATION_SCHEMA_VERSION
      };
      await library.put(record);
      if (activeIdRef.current === id || activeIdRef.current === null) {
        setActiveId(id);
        setActiveMessages(record.messages);
        setActiveRecord(record);
      }
      await refresh();
    },
    [idFactory, nowFn, library, refresh, projectId]
  );
  const deleteConversation = useCallback(
    async (id) => {
      await library.delete(id);
      const list = await library.list();
      setConversations(list);
      if (id !== activeId) return;
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
    [library, activeId, idFactory]
  );
  const mutateMetadata = useCallback(
    async (id, patchOf) => {
      const record = await library.get(id);
      if (!record) {
        await refresh();
        throw new Error(
          `useConversationLibrary: conversation "${id}" not found`
        );
      }
      const patch = patchOf(record);
      let next;
      if (library.patch) {
        next = await library.patch(id, patch);
        if (!next) {
          await refresh();
          throw new Error(
            `useConversationLibrary: conversation "${id}" not found`
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
    [library, activeId, refresh]
  );
  const renameConversation = useCallback(
    async (id, title) => mutateMetadata(id, (record) => conversationRenamePatch(record, title, nowFn())),
    [mutateMetadata, nowFn]
  );
  const pinConversation = useCallback(
    async (id, pinned) => mutateMetadata(id, () => conversationPinPatch(pinned, nowFn())),
    [mutateMetadata, nowFn]
  );
  const archiveConversation = useCallback(
    async (id, archived) => mutateMetadata(id, () => conversationArchivePatch(archived, nowFn())),
    [mutateMetadata, nowFn]
  );
  const archiveConversations = useCallback(
    async (ids) => {
      const pending = [...new Set(ids)];
      const failed = [];
      const archiveOne = async (id) => {
        const patch = conversationArchivePatch(true, nowFn());
        try {
          if (library.patch) {
            if (!await library.patch(id, patch)) failed.push(id);
            return;
          }
          const record = await library.get(id);
          if (!record) {
            failed.push(id);
            return;
          }
          await library.put(applyConversationMetadataPatch(record, patch));
        } catch {
          failed.push(id);
        }
      };
      for (let i = 0; i < pending.length; i += ARCHIVE_BATCH_CONCURRENCY) {
        await Promise.all(pending.slice(i, i + ARCHIVE_BATCH_CONCURRENCY).map(archiveOne));
      }
      const active = activeIdRef.current;
      if (active && pending.includes(active) && !failed.includes(active)) {
        const record = await library.get(active).catch(() => null);
        if (record && activeIdRef.current === active) {
          setActiveRecord(record);
          setActiveMessages(record.messages);
        }
      }
      await refresh().catch(() => void 0);
      return failed;
    },
    [library, nowFn, refresh]
  );
  const guardedSwitch = useCallback(
    (id) => guard("switch", id, () => switchConversation(id)),
    [guard, switchConversation]
  );
  const guardedDelete = useCallback(
    (id) => guard("delete", id, () => deleteConversation(id)),
    [guard, deleteConversation]
  );
  const guardedRename = useCallback(
    (id, title) => guard("rename", id, () => renameConversation(id, title)),
    [guard, renameConversation]
  );
  const guardedPin = useCallback(
    (id, pinned) => guard("pin", id, () => pinConversation(id, pinned)),
    [guard, pinConversation]
  );
  const guardedArchive = useCallback(
    (id, archived) => guard("archive", id, () => archiveConversation(id, archived)),
    [guard, archiveConversation]
  );
  return {
    ready,
    conversations,
    activeId,
    activeMessages,
    activeRecord,
    newConversation,
    switchConversation: guardedSwitch,
    deleteConversation: guardedDelete,
    renameConversation: guardedRename,
    pinConversation: guardedPin,
    archiveConversation: guardedArchive,
    archiveConversations,
    persist,
    claimActive,
    refresh,
    reloadActive,
    actionError,
    retryAction,
    dismissActionError
  };
}

// src/conversation/useIndexedDBConversationLibrary.ts
import { useMemo } from "react";

// src/identity/scopedStore.ts
var SCOPE_SEPARATOR = "--";
var LEGACY_SCOPE = "legacy";
function scopedStoreName(base, identityKey) {
  const scope = identityKey && identityKey.trim() ? identityKey : LEGACY_SCOPE;
  return `${base}${SCOPE_SEPARATOR}${scope}`;
}

// src/conversation/useIndexedDBConversationLibrary.ts
var BASE_DB_NAME = "free-intelligence-conversations";
function useIndexedDBConversationLibrary(identityKey, options = {}) {
  const { storeName } = options;
  return useMemo(
    () => new IndexedDBConversationLibrary({
      dbName: scopedStoreName(BASE_DB_NAME, identityKey),
      storeName
    }),
    [identityKey, storeName]
  );
}

// src/conversation/ConversationArchiveDialog.tsx
import { useEffect as useEffect2, useInsertionEffect as useInsertionEffect2, useRef as useRef2, useState as useState2 } from "react";

// src/theme/breakpoints.ts
var FI_MOBILE_BREAKPOINT_PX = 768;
var FI_MOBILE_QUERY = `(max-width: ${FI_MOBILE_BREAKPOINT_PX}px)`;
var FI_TOUCH_QUERY = `(pointer: coarse), ${FI_MOBILE_QUERY}`;

// src/theme/glass-tokens.generated.ts
var glassTokens = {
  /** slate-950. --glass-chat-body y --glass-chat-bg-from del preset. OJO: og118 web re-tinta --glass-chat-bg-from a #0a0e16 (--og-bg-deep en globals.css); el iPhone hoy pinta el default del preset, no el re-tint — divergencia heredada, documentada, no resuelta aquí. */
  bgDeep: "#020617",
  /** slate-900. --glass-chat-bg-mid, el centro del barrido diagonal del fondo. */
  bgMid: "#0f172a",
  /** emerald-400. --og-accent en globals.css de og118 — el acento del CONSUMER, no del preset (el preset arranca su gradiente en accentDeep). */
  accent: "#34d399",
  /** emerald-600. --glass-chat-accent-from del preset; tambien el extremo final del gradiente del botón de enviar de og118. */
  accentDeep: "#059669",
  /** cyan-600. --glass-chat-accent-to: cierra el gradiente header/CTA del preset. Hoy sólo la web lo usa. */
  accentTo: "#0891b2",
  /** emerald-300. --glass-chat-accent-text. Hoy sólo la web lo usa. */
  accentText: "#6ee7b7",
  /** --og-accent-muted en globals.css. OJO: globals.css tiene un fallback var(--og-accent-muted, #94a3b8) que no coincide con la definición de :root — bug preexistente de la web. */
  accentMuted: "#a3a3a3",
  /** red-400. --og-danger y el fallback de --fi-sidebar-item-danger en sidebarItemStyle.ts. */
  danger: "#f87171",
  /** --glass-chat-text, el texto primario sobre el vidrio. */
  text: "#ffffff",
  /** slate-200. El color de body en og118 y content.user en messages/styles.ts. La web pinta al asistente un paso más claro (slate-100, text-slate-100); el iPhone usa este mismo para ambos lados — matiz heredado. */
  textBody: "#e2e8f0",
  /** slate-400. --glass-chat-text-muted: placeholders y subtítulos. */
  textMuted: "#94a3b8",
  /** slate-500. Timestamps (MessageAuthorHeader), placeholders terciarios. */
  textFaint: "#64748b",
  /** slate-800/60. --glass-chat-surface: el relleno esmerilado del composer. */
  surface: "rgba(30, 41, 59, 0.6)",
  /** slate-600/40. --glass-chat-surface-border. */
  surfaceBorder: "rgba(71, 85, 105, 0.4)",
  /** emerald-600/32. --glass-chat-bubble-user: lavado esmeralda translúcido, no sólido — el sólido leía como verde WhatsApp. */
  bubbleUser: "rgba(5, 150, 105, 0.32)",
  /** emerald-400/25. --glass-chat-bubble-user-border. */
  bubbleUserBorder: "rgba(52, 211, 153, 0.25)",
  /** slate-800/55. --glass-chat-bubble-assistant. */
  bubbleAssistant: "rgba(30, 41, 59, 0.55)",
  /** slate-600/35. --glass-chat-bubble-border. */
  bubbleBorder: "rgba(71, 85, 105, 0.35)",
  /** --glass-chat-bg-glow del preset: el resplandor radial apenas-visible sobre el fondo. OJO: og118 web lo re-tinta a rgba(52, 211, 153, 0.06) — 'og emerald, not preset cyan'; el iPhone hoy pinta el cyan del preset — divergencia heredada, documentada, no resuelta aquí. */
  glow: "rgba(8, 145, 178, 0.07)",
  /** violet-600/80. avatar.user en messages/styles.ts: el chip de autor del usuario. */
  authorUser: "rgba(124, 58, 237, 0.8)",
  /** --fi-author-agent-fg en MessageAuthorHeader.tsx: texto oscuro sobre el chip ámbar del agente. */
  authorAgentText: "#0a0f1e",
  /** slate-300. El nombre del hablante en MessageAuthorHeader.tsx (meta.name). */
  authorName: "#cbd5e1",
  /** amber-400/80. typing.dot en messages/styles.ts. */
  typingDot: "rgba(251, 191, 36, 0.8)",
  /** amber-300/90. markdownStyles.code — el ámbar del código inline, distinto a propósito del esmeralda de los links. */
  codeInline: "rgba(252, 211, 77, 0.9)",
  /** slate-900/80. markdownStyles.pre. */
  codeBlockBg: "rgba(15, 23, 42, 0.8)",
  /** slate-700/30. Borde de markdownStyles.pre. */
  codeBlockBorder: "rgba(51, 65, 85, 0.3)",
  /** white/3. markdownStyles.blockquote. */
  quoteBg: "rgba(255, 255, 255, 0.03)",
  /** amber-500/60. El filete izquierdo del blockquote. */
  quoteAccent: "rgba(245, 158, 11, 0.6)",
  /** emerald-500/30. Borde del selector de elemento (Og118ElementSelector). */
  chipBorder: "rgba(16, 185, 129, 0.3)",
  /** white/5. Relleno del selector de elemento. */
  chipFill: "rgba(255, 255, 255, 0.05)",
  /** El tinte .is-selected de la fila del sidebar (sidebarItemStyle.ts). */
  itemSelectedBg: "rgba(52, 211, 153, 0.08)",
  /** El borde .is-selected de la fila del sidebar. */
  itemSelectedBorder: "rgba(52, 211, 153, 0.3)",
  /** white/4. Fallback de --fi-sidebar-item-hover-bg. */
  itemHover: "rgba(255, 255, 255, 0.04)",
  /** slate-600. Fallback de --fi-sidebar-item-meta-color: la hora de la fila. */
  itemMeta: "#475569",
  /** slate-500. Fallback de --fi-sidebar-item-action-color: los botones de la fila. */
  itemAction: "#64748b",
  /** white/6. Los bordes del rail (.og-sidebar, .og-sidebar-foot, .og-sidebar-archived). */
  sidebarDivider: "rgba(255, 255, 255, 0.06)",
  /** white/4. Fondo de .og-sidebar-search. */
  searchFill: "rgba(255, 255, 255, 0.04)",
  /** white/10. Borde de .og-sidebar-search. */
  searchBorder: "rgba(255, 255, 255, 0.1)",
  /** emerald-500/30. El badge del elemento seleccionado (bg-emerald-500/30). */
  badgeSelected: "rgba(16, 185, 129, 0.3)",
  /** emerald-100. Texto del badge seleccionado (text-emerald-100). */
  badgeSelectedText: "#d1fae5",
  /** emerald-500/10. Relleno del chip de engine (bg-emerald-500/10). */
  engineChipFill: "rgba(16, 185, 129, 0.1)",
  /** slate-600. Fondo del swipe de archivar — affordance NATIVA del iPhone, sin gemelo web; el tono viene de la misma escala slate del rail. */
  archiveSwipe: "#475569",
  /** Texto oscuro sobre el gradiente esmeralda del botón de enviar (.og-send-btn color). */
  sendText: "#052e1a",
  /** El outline del enviar deshabilitado (.og-send-btn:disabled): mantiene la FORMA del control en el estado que más se ve. */
  sendDisabledBorder: "rgba(148, 163, 184, 0.28)",
  /** red-600/90. .og-stop-btn: el rojo dice 'esto lo detiene'. */
  stopFill: "rgba(220, 38, 38, 0.9)",
  /** red-400/60. Borde de .og-stop-btn. */
  stopBorder: "rgba(248, 113, 113, 0.6)",
  /** red-100. Texto de .og-stop-btn. */
  stopText: "#fee2e2",
  /** --glass-chat-radius (rounded-2xl): la esquina del composer y las superficies grandes. */
  radius: "16px",
  /** La esquina de la fila del sidebar (sidebarItemStyle.ts). */
  itemRadius: "10px",
  /** Fallback de --fi-item-gap (densidad comfortable). */
  itemGap: "0.4rem",
  /** Padding vertical de la fila (primera mitad de --fi-item-padding comfortable). */
  itemPadV: "0.55rem",
  /** Padding horizontal de la fila (segunda mitad de --fi-item-padding comfortable). */
  itemPadH: "0.6rem",
  /** Tipografía del título de la fila. */
  itemTitleSize: "0.85rem",
  /** Tipografía del subtítulo/preview de la fila. */
  itemSubtitleSize: "0.75rem",
  /** Tipografía de la hora/meta de la fila. */
  itemMetaSize: "0.68rem",
  /** --glass-chat-shadow (≈ shadow-2xl). Sólo la web: en SwiftUI la elevación se compone distinto. */
  shadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
  /** --glass-chat-watermark-opacity. Sólo la web: el watermark es del shell web. */
  watermarkOpacity: "0.08"
};

// src/shell/touchTarget.ts
import { useInsertionEffect } from "react";
var FI_TOUCH_TARGET_CLASS = "fi-touch-target";
var TOUCH_TARGET_STYLE_ID = "fi-touch-target-style";
function ensureTouchTargetStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(TOUCH_TARGET_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = TOUCH_TARGET_STYLE_ID;
  el.textContent = `
    @media ${FI_TOUCH_QUERY} {
      .${FI_TOUCH_TARGET_CLASS} {
        min-width: var(--fi-touch-target, 44px);
        min-height: var(--fi-touch-target, 44px);
        box-sizing: border-box;
      }
      :where(.${FI_TOUCH_TARGET_CLASS}) {
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
    }
  `;
  document.head.appendChild(el);
}
function withTouchTarget(className) {
  return className ? `${FI_TOUCH_TARGET_CLASS} ${className}` : FI_TOUCH_TARGET_CLASS;
}

// src/conversation/ConversationArchiveDialog.tsx
import { jsx, jsxs } from "react/jsx-runtime";
var DEFAULT_LABELS = {
  title: "Archivar chats",
  selectAll: "Seleccionar todos",
  selectNone: "Quitar selecci\xF3n",
  cancel: "Cancelar",
  archive: (n) => n === 1 ? "Archivar 1 chat" : `Archivar ${n} chats`,
  failed: (failed, total) => `${failed} de ${total} no se pudieron archivar. Los que fallaron siguen marcados: vuelve a intentarlo.`,
  empty: "No hay chats para archivar."
};
var FI_ARCHIVE_DIALOG_CLASS = "fi-archive-dialog";
var STYLE_ID = "fi-archive-dialog-style";
var CSS = `
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
function ensureArchiveDialogStyle() {
  if (typeof document === "undefined") return;
  ensureTouchTargetStyle();
  if (document.getElementById(STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}
var initialSelection = (conversations) => new Set(conversations.filter((c) => !c.pinnedAt).map((c) => c.id));
function ConversationArchiveDialog({
  open,
  conversations,
  onArchive,
  onClose,
  renderMeta,
  labels: labelOverrides
}) {
  useInsertionEffect2(() => {
    ensureArchiveDialogStyle();
  }, []);
  const labels = { ...DEFAULT_LABELS, ...labelOverrides };
  const dialogRef = useRef2(null);
  const [selected, setSelected] = useState2(() => initialSelection(conversations));
  const [busy, setBusy] = useState2(false);
  const [failure, setFailure] = useState2(null);
  useEffect2(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setSelected(initialSelection(conversations));
      setFailure(null);
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);
  const selectedIds = conversations.filter((c) => selected.has(c.id)).map((c) => c.id);
  const allSelected = conversations.length > 0 && selectedIds.length === conversations.length;
  const toggle = (id) => setSelected((prev) => {
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
  return /* @__PURE__ */ jsxs(
    "dialog",
    {
      ref: dialogRef,
      className: FI_ARCHIVE_DIALOG_CLASS,
      "aria-labelledby": "fi-archive-dialog-title",
      onCancel: (e) => {
        e.preventDefault();
        if (!busy) onClose();
      },
      onClick: (e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      },
      children: [
        /* @__PURE__ */ jsxs("div", { className: "fi-archive-dialog-head", children: [
          /* @__PURE__ */ jsx("h2", { id: "fi-archive-dialog-title", className: "fi-archive-dialog-title", children: labels.title }),
          conversations.length > 0 && /* @__PURE__ */ jsx(
            "button",
            {
              type: "button",
              className: withTouchTarget("fi-archive-dialog-toggle"),
              onClick: () => setSelected(allSelected ? /* @__PURE__ */ new Set() : new Set(conversations.map((c) => c.id))),
              disabled: busy,
              children: allSelected ? labels.selectNone : labels.selectAll
            }
          )
        ] }),
        conversations.length === 0 ? /* @__PURE__ */ jsx("p", { className: "fi-archive-dialog-empty", children: labels.empty }) : /* @__PURE__ */ jsx("ul", { className: "fi-archive-dialog-list", children: conversations.map((c) => /* @__PURE__ */ jsx("li", { children: /* @__PURE__ */ jsxs("label", { className: "fi-archive-dialog-row", children: [
          /* @__PURE__ */ jsx(
            "input",
            {
              type: "checkbox",
              checked: selected.has(c.id),
              onChange: () => toggle(c.id),
              disabled: busy
            }
          ),
          /* @__PURE__ */ jsxs("span", { className: "fi-archive-dialog-row-body", children: [
            /* @__PURE__ */ jsx("span", { className: "fi-archive-dialog-row-title", children: c.title }),
            renderMeta && /* @__PURE__ */ jsx("span", { className: "fi-archive-dialog-row-meta", children: renderMeta(c) })
          ] })
        ] }) }, c.id)) }),
        failure && /* @__PURE__ */ jsx("p", { className: "fi-archive-dialog-error", role: "alert", children: labels.failed(failure.failed, failure.total) }),
        /* @__PURE__ */ jsxs("div", { className: "fi-archive-dialog-foot", children: [
          /* @__PURE__ */ jsx(
            "button",
            {
              type: "button",
              className: withTouchTarget("fi-archive-dialog-cancel"),
              onClick: onClose,
              disabled: busy,
              children: labels.cancel
            }
          ),
          /* @__PURE__ */ jsx(
            "button",
            {
              type: "button",
              className: withTouchTarget("fi-archive-dialog-confirm"),
              onClick: () => void confirm(),
              disabled: busy || selectedIds.length === 0,
              children: labels.archive(selectedIds.length)
            }
          )
        ] })
      ]
    }
  );
}

// src/conversation/useCloudConversationLibrary.ts
import { useCallback as useCallback2, useEffect as useEffect3, useState as useState3 } from "react";
var DEFAULT_RETRY_DELAYS_MS = [5e3, 15e3, 3e4, 6e4];
var DEFAULT_SLOW_AFTER_MS = 4e3;
function useCloudConversationLibrary({
  local,
  remote,
  enabled,
  scopeKey,
  retryDelaysMs = DEFAULT_RETRY_DELAYS_MS,
  slowAfterMs = DEFAULT_SLOW_AFTER_MS
}) {
  const [settledFor, setSettledFor] = useState3(null);
  const [failedFor, setFailedFor] = useState3(null);
  const [attempt, setAttempt] = useState3(0);
  const [slow, setSlow] = useState3(false);
  const active = enabled && scopeKey !== null;
  const settled = active && settledFor === scopeKey;
  const failed = active && !settled && failedFor === scopeKey;
  useEffect3(() => {
    if (!active || settled) return;
    let cancelled = false;
    setSlow(false);
    const slowTimer = setTimeout(() => {
      if (!cancelled) setSlow(true);
    }, slowAfterMs);
    void (async () => {
      try {
        await migrateConversationLibrary(local, remote);
        await migrateConversationLibrary(local, remote);
        if (cancelled) return;
        setFailedFor(null);
        setSettledFor(scopeKey);
      } catch (error) {
        if (cancelled) return;
        console.error("fi-glass: cloud conversation store unreachable, staying local", error);
        setFailedFor(scopeKey);
      } finally {
        clearTimeout(slowTimer);
        if (!cancelled) setSlow(false);
      }
    })();
    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
  }, [active, settled, scopeKey, local, remote, attempt, slowAfterMs]);
  const [failures, setFailures] = useState3(0);
  useEffect3(() => {
    if (!failed) return;
    const delay = retryDelaysMs[Math.min(failures, retryDelaysMs.length - 1)];
    const timer = setTimeout(() => {
      setFailures((n) => n + 1);
      setAttempt((n) => n + 1);
    }, delay);
    return () => clearTimeout(timer);
  }, [failed, failures, retryDelaysMs]);
  useEffect3(() => {
    if (settled) setFailures(0);
  }, [settled]);
  const retry = useCallback2(() => {
    setFailedFor(null);
    setFailures(0);
    setAttempt((n) => n + 1);
  }, []);
  if (!active) return { library: local, status: "local", slow: false, retry };
  if (settled) return { library: remote, status: "cloud", slow: false, retry };
  return { library: local, status: failed ? "unreachable" : "connecting", slow, retry };
}
export {
  ConversationArchiveDialog,
  EphemeralConversationLibrary,
  FI_ARCHIVE_DIALOG_CLASS,
  IndexedDBConversationLibrary,
  RemoteConversationLibrary,
  ensureArchiveDialogStyle,
  mergeConversationRecords,
  migrateConversationLibrary,
  useCloudConversationLibrary,
  useConversationLibrary,
  useIndexedDBConversationLibrary
};
//# sourceMappingURL=index.js.map