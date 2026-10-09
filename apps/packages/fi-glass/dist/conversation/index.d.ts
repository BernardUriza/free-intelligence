import { ConversationLibrary, ConversationSummary, ConversationRecord, ConversationMetadataPatch, ChatMessage } from '@free-intelligence/core';

/**
 * EphemeralConversationLibrary — conversations that die with the tab.
 *
 * The ConversationLibrary contract satisfied by a plain in-memory Map: nothing
 * reaches IndexedDB, localStorage or a server, and closing the tab is the whole
 * cleanup story.
 *
 * It exists for **shared-machine / kiosk surfaces**, where persistence is not a
 * missing feature but a hazard: a public terminal that remembers threads shows
 * the previous stranger's conversation to the next one. IndexedDB is the wrong
 * tool there (it is per-browser, not per-person, so every visitor inherits the
 * last one's history), and a remote library is worse (it publishes it).
 *
 * The live thread still works exactly as anywhere else — messages, streaming,
 * switching between conversations opened during this visit — because the
 * contract is the same. What disappears is only what should: everything, on
 * close.
 *
 * @example
 * const library = useMemo(
 *   () => (isPublicTerminal ? new EphemeralConversationLibrary() : remote),
 *   [isPublicTerminal, remote],
 * );
 * const lib = useConversationLibrary(library);
 */

declare class EphemeralConversationLibrary implements ConversationLibrary {
    private readonly records;
    list(): Promise<ConversationSummary[]>;
    get(id: string): Promise<ConversationRecord | null>;
    put(record: ConversationRecord): Promise<void>;
    delete(id: string): Promise<void>;
    clear(): Promise<void>;
}

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
    patch(id: string, patch: ConversationMetadataPatch): Promise<ConversationRecord | null>;
    delete(id: string): Promise<void>;
    clear(): Promise<void>;
}

/**
 * migrateConversationLibrary — local→cloud transcript migration.
 *
 * When a shell flips from a local library (IndexedDB) to a remote one (the
 * account signed in and the cloud store is now authoritative), the transcripts
 * that already live in the browser must not be stranded. A record the target
 * lacks is copied. A record BOTH have is merged when the source was written
 * after the target: the shell writes locally while the cloud store is still
 * connecting, so skipping the collision lost exactly those turns. The merge is
 * a union of messages (target metadata wins); nothing is ever removed, and the
 * source is left intact. Idempotent: a second run finds nothing to write.
 */

interface MigrateConversationsResult {
    /** How many records were copied into the target. */
    migrated: number;
    /** How many existing target records gained messages only the source had. */
    merged: number;
    /** How many source records needed no write (the target already had everything). */
    skipped: number;
}
/**
 * Union of two copies of the same conversation: every message of `target`,
 * plus the ones only `source` has, ordered by timestamp (stable for ties).
 * `target` keeps its title, flags and project.
 *
 * @returns `target` itself (same reference) when `source` adds nothing.
 */
declare function mergeConversationRecords(target: ConversationRecord, source: ConversationRecord): ConversationRecord;
declare function migrateConversationLibrary(source: ConversationLibrary, target: ConversationLibrary): Promise<MigrateConversationsResult>;

interface UseConversationLibraryOptions {
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
/** `load` = the store could not be read (mount, store swap, or its retry). */
type ConversationAction = 'load' | 'switch' | 'delete' | 'rename' | 'pin' | 'archive';
interface ConversationActionError {
    action: ConversationAction;
    conversationId: string;
    message: string;
    cause: unknown;
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
    /**
     * Persist a conversation's messages (no-op for an empty thread). `conversationId`
     * is the conversation the thread BELONGS to (default: the active one); a write
     * that lands after the user moved elsewhere saves that conversation and leaves
     * the active one alone.
     */
    persist: (messages: ChatMessage[], conversationId?: string | null) => Promise<void>;
    /**
     * Mark a conversation (default: the active one) as holding the user's work —
     * a turn was sent in it. A store swap then keeps it active even before its
     * first save, instead of moving the user to the new store's most recent.
     */
    claimActive: (conversationId?: string | null) => void;
    /** Re-read the summary list from storage. */
    refresh: () => Promise<void>;
    /**
     * Re-read the ACTIVE record from storage and adopt it if another writer (a
     * background worker, the same account on another device) bumped `updatedAt`.
     * A no-op when nothing changed, so polling it costs no re-render. Throws
     * like `switchConversation` when a previously stored record is gone.
     */
    reloadActive: () => Promise<void>;
    /** The last sidebar action that failed, kept until it succeeds, is retried or dismissed. */
    actionError: ConversationActionError | null;
    /** Re-run exactly the failed action. */
    retryAction: () => void;
    dismissActionError: () => void;
}
declare function useConversationLibrary(library: ConversationLibrary, options?: UseConversationLibraryOptions): ConversationLibraryState;

declare function useIndexedDBConversationLibrary(identityKey: string | null | undefined, options?: Omit<IndexedDBConversationLibraryOptions, 'dbName'>): IndexedDBConversationLibrary;

type CloudSyncStatus = 'local' | 'connecting' | 'cloud' | 'unreachable';
interface UseCloudConversationLibraryOptions {
    local: ConversationLibrary;
    remote: ConversationLibrary;
    enabled: boolean;
    scopeKey: string | null;
    retryDelaysMs?: readonly number[];
    slowAfterMs?: number;
}
interface CloudConversationLibraryState {
    library: ConversationLibrary;
    status: CloudSyncStatus;
    slow: boolean;
    retry: () => void;
}
/**
 * Hands a shell its conversation store while the cloud one is reached: local until the
 * local→cloud migration settles, then remote; an unreachable server retries with backoff.
 *
 * @returns `status` tells the UI the truth about where writes land right now; `slow` flips
 * when connecting outlasts `slowAfterMs` (a scale-to-zero cold start); `retry` reconnects now.
 */
declare function useCloudConversationLibrary({ local, remote, enabled, scopeKey, retryDelaysMs, slowAfterMs, }: UseCloudConversationLibraryOptions): CloudConversationLibraryState;

export { type CloudConversationLibraryState, type CloudSyncStatus, type ConversationAction, type ConversationActionError, type ConversationLibraryState, EphemeralConversationLibrary, IndexedDBConversationLibrary, type IndexedDBConversationLibraryOptions, type MigrateConversationsResult, RemoteConversationLibrary, type RemoteConversationLibraryOptions, type UseCloudConversationLibraryOptions, type UseConversationLibraryOptions, mergeConversationRecords, migrateConversationLibrary, useCloudConversationLibrary, useConversationLibrary, useIndexedDBConversationLibrary };
