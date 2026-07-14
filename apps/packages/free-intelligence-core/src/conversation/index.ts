/**
 * @free-intelligence/core — conversation library contract (DD-002B1).
 *
 * Local-first transcript persistence primitives: the record/summary types, the
 * storage contract (ConversationLibrary), and pure helpers (title/preview
 * derivation + privacy-by-structure sanitization). Adapters (IndexedDB, backend)
 * implement ConversationLibrary in later layers — they live in fi-glass and the
 * apps, never here.
 */

export type { ConversationRecord, ConversationSummary } from './record';
export type { ConversationLibrary } from './library';
export {
  CONVERSATION_SCHEMA_VERSION,
  createConversationRecord,
  summarizeConversation,
  organizeConversationSummaries,
  filterConversationSummaries,
  deriveConversationTitle,
  deriveConversationPreview,
  resolveConversationTitle,
  renameConversationRecord,
  setConversationPinned,
  setConversationArchived,
  sanitizeConversationMessage,
  type CreateConversationRecordArgs,
  type OrganizedConversations,
} from './helpers';
