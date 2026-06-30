/**
 * fi-glass/conversation — local-first conversation persistence (DD-002B1.2).
 *
 * The browser adapter for core's ConversationLibrary contract plus the reusable
 * multi-conversation manager hook. Composes with `fi-glass/agent`'s
 * `useAgentConversation` (live thread) so any shell can offer a chat sidebar +
 * refresh-safe transcript without re-implementing persistence in the app.
 */

export {
  IndexedDBConversationLibrary,
  type IndexedDBConversationLibraryOptions,
} from './IndexedDBConversationLibrary';
export {
  useConversationLibrary,
  type UseConversationLibraryOptions,
  type ConversationLibraryState,
} from './useConversationLibrary';
export { useIndexedDBConversationLibrary } from './useIndexedDBConversationLibrary';
