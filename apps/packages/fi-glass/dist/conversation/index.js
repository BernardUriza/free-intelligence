'use client';

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

// src/conversation/useConversationLibrary.ts
import { useCallback, useEffect, useState } from "react";
import {
  CONVERSATION_SCHEMA_VERSION,
  deriveConversationPreview,
  resolveConversationTitle,
  renameConversationRecord,
  sanitizeConversationMessage
} from "@free-intelligence/core";
function useConversationLibrary(library, options = {}) {
  const idFactory = options.idFactory ?? (() => crypto.randomUUID());
  const nowFn = options.now ?? (() => (/* @__PURE__ */ new Date()).toISOString());
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
      const record = {
        id,
        title: resolveConversationTitle(clean, prevForTitle),
        titleCustom: prevForTitle?.titleCustom,
        createdAt,
        updatedAt: now,
        messages: clean,
        preview: deriveConversationPreview(clean),
        schemaVersion: CONVERSATION_SCHEMA_VERSION
      };
      await library.put(record);
      setActiveId(id);
      setActiveMessages(record.messages);
      setActiveRecord(record);
      await refresh();
    },
    [activeId, activeRecord, idFactory, nowFn, library, refresh]
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
  const renameConversation = useCallback(
    async (id, title) => {
      const record = await library.get(id);
      if (!record) {
        await refresh();
        throw new Error(
          `useConversationLibrary: conversation "${id}" not found`
        );
      }
      const next = renameConversationRecord(record, title, nowFn());
      await library.put(next);
      if (id === activeId) {
        setActiveRecord(next);
        setActiveMessages(next.messages);
      }
      await refresh();
    },
    [library, activeId, nowFn, refresh]
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
  IndexedDBConversationLibrary,
  useConversationLibrary,
  useIndexedDBConversationLibrary
};
//# sourceMappingURL=index.js.map