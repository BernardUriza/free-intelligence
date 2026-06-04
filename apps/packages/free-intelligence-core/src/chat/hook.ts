import type { ChatMessage, ChatStreamingState } from './message';

/**
 * ChatHook — the conversation contract the fi-glass shell consumes.
 *
 * This is the dependency-inversion spine of the chat shell: ChatWidget never
 * imports a concrete conversation hook, it consumes this interface. aurity
 * implements it with `useFIConversation`; og118 implements its own against its
 * backend. A fat contract (state + actions + streaming) → it earns a place in
 * core (unlike navigation, which is a plain callback prop).
 *
 * Generic over:
 * - `TMessage` — the message type (aurity passes its FIMessage; default ChatMessage).
 * - `TNode`    — the UI-slot node type (aurity passes React's ReactNode). Kept
 *   generic so core stays framework-agnostic (no React import).
 */
export interface ChatHook<TMessage = ChatMessage, TNode = unknown> {
  // ---- State ----
  messages: TMessage[];
  loading: boolean;
  isTyping: boolean;
  loadingInitial?: boolean;
  hasMoreMessages?: boolean;
  loadingOlder?: boolean;
  streamingMessage?: string;
  streaming?: ChatStreamingState;

  // ---- Core actions ----
  sendMessage: (message: string, metadata?: object) => Promise<void>;
  sendMessageStream?: (message: string, metadata?: object) => Promise<void>;
  loadOlderMessages?: () => Promise<void>;

  // ---- Optional actions ----
  clearConversation?: () => void;
  getIntroduction?: () => void;
  startConversation?: () => Promise<void>;
  sendQuickReply?: (reply: string) => Promise<void>;

  // ---- Optional state ----
  conversationState?: {
    quickReplies?: string[];
    actions?: Array<{ type: string; data: unknown }>;
    metadata?: Record<string, unknown>;
  };

  // ---- Custom UI slots (typed by the consumer's node type) ----
  customEmptyState?: TNode;
  customQuickReplies?: TNode;
}
