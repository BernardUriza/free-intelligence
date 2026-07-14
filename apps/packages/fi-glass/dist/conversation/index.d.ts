import { ConversationLibrary, ConversationSummary, ConversationRecord, ChatMessage } from '@free-intelligence/core';

/**
 * IndexedDBConversationLibrary — a browser ConversationLibrary (DD-002B1.2).
 *
 * Implements the @free-intelligence/core ConversationLibrary contract over
 * IndexedDB, zero external dependencies (a small promisified wrapper). This is
 * the first concrete adapter for the local-first transcript persistence the
 * core contract describes; later layers may add a backend adapter against the
 * SAME contract.
 *
 * Privacy: this adapter is a dumb store — it persists exactly the records it is
 * given. Sanitization (role/content/timestamp only, no tokens / metadata /
 * glass-box) happens upstream in core helpers, which the conversation hook uses
 * to build every record before `put`.
 *
 * SSR safety: the constructor never touches `indexedDB` (only stores config), so
 * instantiating during a server render is harmless. Any method that needs the DB
 * rejects with a CLEAR error when IndexedDB is unavailable (server render /
 * storage disabled) — it never fails silently.
 */

interface IndexedDBConversationLibraryOptions {
    /** Database name. Default: `free-intelligence-conversations`. */
    dbName?: string;
    /** Object store name. Default: `conversations`. */
    storeName?: string;
}
declare class IndexedDBConversationLibrary implements ConversationLibrary {
    private readonly dbName;
    private readonly storeName;
    private dbPromise;
    constructor(options?: IndexedDBConversationLibraryOptions);
    /** Open (and lazily create) the database. Rejects clearly if unavailable. */
    private open;
    /** Run one request inside a transaction and resolve with its result. */
    private run;
    /** All conversations as light summaries, newest `updatedAt` first. */
    list(): Promise<ConversationSummary[]>;
    /** The full record for `id`, or `null` if none. */
    get(id: string): Promise<ConversationRecord | null>;
    /** Insert or replace a record by its `id`. */
    put(record: ConversationRecord): Promise<void>;
    /** Remove the record for `id` (no-op if absent). */
    delete(id: string): Promise<void>;
    /** Remove every stored conversation. */
    clear(): Promise<void>;
}

/**
 * RemoteConversationLibrary — the cloud ConversationLibrary adapter.
 *
 * Implements the @free-intelligence/core contract over the server's
 * /conversations CRUD (og118 is the canary backend), so a signed-in account's
 * transcripts follow it across browsers/devices instead of living in one
 * browser's IndexedDB. Same dumb-store discipline as the IndexedDB adapter:
 * records arrive already sanitized (core helpers upstream) and are stored as
 * given; the server enforces ownership by the auth principal.
 *
 * Transport is injected, never assumed: `headers` supplies the Authorization
 * header per request (tokens rotate — read at call time, not construction),
 * and `fetchImpl` is overridable for tests/non-browser runtimes.
 */

interface RemoteConversationLibraryOptions {
    /** API origin, e.g. `https://api.example.com` (no trailing slash needed). */
    baseUrl: string;
    /** Per-request headers (Authorization). Read at call time so rotated tokens
     * are picked up. Default: none. */
    headers?: () => Record<string, string>;
    /** Fetch implementation. Default: the global `fetch`. */
    fetchImpl?: typeof fetch;
}
declare class RemoteConversationLibrary implements ConversationLibrary {
    private readonly baseUrl;
    private readonly headers;
    private readonly fetchImpl;
    constructor(options: RemoteConversationLibraryOptions);
    private request;
    private static fail;
    list(): Promise<ConversationSummary[]>;
    get(id: string): Promise<ConversationRecord | null>;
    put(record: ConversationRecord): Promise<void>;
    delete(id: string): Promise<void>;
    clear(): Promise<void>;
}

/**
 * migrateConversationLibrary — one-time local→cloud transcript migration.
 *
 * When a shell flips from a local library (IndexedDB) to a remote one (the
 * account signed in and the cloud store is now authoritative), the transcripts
 * that already live in the browser must not be stranded. This copies every
 * source record the target does not already have — target wins on id collision
 * (the cloud copy may be newer, written from another device), and the source is
 * left intact (never destructive: the local data remains a fallback until the
 * user clears it). Idempotent: a second run finds nothing to copy.
 */

interface MigrateConversationsResult {
    /** How many records were copied into the target. */
    migrated: number;
    /** How many source records were skipped because the target already had them. */
    skipped: number;
}
declare function migrateConversationLibrary(source: ConversationLibrary, target: ConversationLibrary): Promise<MigrateConversationsResult>;

interface UseConversationLibraryOptions {
    /** Mint a new conversation id. Default: `crypto.randomUUID`. Injectable for tests. */
    idFactory?: () => string;
    /** ISO timestamp provider for createdAt/updatedAt. Default: wall clock. Injectable for tests. */
    now?: () => string;
}
interface ConversationLibraryState {
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
declare function useConversationLibrary(library: ConversationLibrary, options?: UseConversationLibraryOptions): ConversationLibraryState;

declare function useIndexedDBConversationLibrary(identityKey: string | null | undefined, options?: Omit<IndexedDBConversationLibraryOptions, 'dbName'>): IndexedDBConversationLibrary;

export { type ConversationLibraryState, IndexedDBConversationLibrary, type IndexedDBConversationLibraryOptions, type MigrateConversationsResult, RemoteConversationLibrary, type RemoteConversationLibraryOptions, type UseConversationLibraryOptions, migrateConversationLibrary, useConversationLibrary, useIndexedDBConversationLibrary };
