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
    /** Persist the active conversation's messages (no-op for an empty thread). */
    persist: (messages: ChatMessage[]) => Promise<void>;
    /** Re-read the summary list from storage. */
    refresh: () => Promise<void>;
}
declare function useConversationLibrary(library: ConversationLibrary, options?: UseConversationLibraryOptions): ConversationLibraryState;

export { type ConversationLibraryState, IndexedDBConversationLibrary, type IndexedDBConversationLibraryOptions, type UseConversationLibraryOptions, useConversationLibrary };
