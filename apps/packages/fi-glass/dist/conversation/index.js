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
async function migrateConversationLibrary(source, target) {
  const [sourceList, targetList] = await Promise.all([source.list(), target.list()]);
  const existing = new Set(targetList.map((summary) => summary.id));
  let migrated = 0;
  let skipped = 0;
  for (const summary of sourceList) {
    if (existing.has(summary.id)) {
      skipped += 1;
      continue;
    }
    const record = await source.get(summary.id);
    if (!record) continue;
    await target.put(record);
    migrated += 1;
  }
  return { migrated, skipped };
}

// src/conversation/useConversationLibrary.ts
import { useCallback, useEffect, useState } from "react";
import {
  applyConversationMetadataPatch,
  conversationArchivePatch,
  conversationPinPatch,
  conversationRenamePatch,
  CONVERSATION_SCHEMA_VERSION,
  deriveConversationPreview,
  resolveConversationTitle,
  sanitizeConversationMessage
} from "@free-intelligence/core";
function useConversationLibrary(library, options = {}) {
  const idFactory = options.idFactory ?? (() => crypto.randomUUID());
  const nowFn = options.now ?? (() => (/* @__PURE__ */ new Date()).toISOString());
  const { projectId } = options;
  const [ready, setReady] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [activeMessages, setActiveMessages] = useState([]);
  const [activeRecord, setActiveRecord] = useState(null);
  const refresh = useCallback(async () => {
    setConversations(await library.list());
  }, [library]);
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
  }, [library]);
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
  const persist = useCallback(
    async (messages) => {
      if (messages.length === 0) return;
      const id = activeId ?? idFactory();
      const now = nowFn();
      const prevForTitle = activeRecord?.id === id ? activeRecord : void 0;
      const createdAt = prevForTitle ? prevForTitle.createdAt : now;
      const clean = messages.map(sanitizeConversationMessage);
      const bornIn = prevForTitle ? prevForTitle.projectId : projectId;
      const record = {
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
        ...prevForTitle?.pinnedAt ? { pinnedAt: prevForTitle.pinnedAt } : {},
        ...prevForTitle?.archivedAt ? { archivedAt: prevForTitle.archivedAt } : {},
        ...bornIn ? { projectId: bornIn } : {},
        schemaVersion: CONVERSATION_SCHEMA_VERSION
      };
      await library.put(record);
      setActiveId(id);
      setActiveMessages(record.messages);
      setActiveRecord(record);
      await refresh();
    },
    [activeId, activeRecord, idFactory, nowFn, library, refresh, projectId]
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
    refresh
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
export {
  EphemeralConversationLibrary,
  IndexedDBConversationLibrary,
  RemoteConversationLibrary,
  migrateConversationLibrary,
  useConversationLibrary,
  useIndexedDBConversationLibrary
};
//# sourceMappingURL=index.js.map