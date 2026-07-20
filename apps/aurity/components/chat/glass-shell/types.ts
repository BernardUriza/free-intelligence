/**
 * aurity · glass-shell types — the props contracts of the legacy ChatWidget
 * orchestrator, relocated out of fi-glass together with the components they
 * describe (B3-FIGLASS-SHELL-CONSOLIDATION-1).
 *
 * The SHARED vocabulary (ChatViewMode, ResponseMode, PersonaType, ChatNavDest,
 * UploadStatus, VoiceRecordingState) stayed in `fi-glass/shell` because live
 * surfaces still speak it — og118 types its project uploads against
 * `UploadStatus`. Only these widget-shaped props came along.
 */

import type { ReactNode } from 'react';
import type { ChatMessage } from '@free-intelligence/core';
import type {
  ChatViewMode,
  ResponseMode,
  PersonaType,
  ChatNavDest,
  UploadStatus,
  VoiceRecordingState,
} from 'fi-glass/shell';

/** Streaming snapshot passed through to the messages slot. */
export interface ShellStreamingState {
  status: 'idle' | 'streaming' | 'complete' | 'error';
  content: string;
  thinking: string;
  isStreaming: boolean;
}

/**
 * ChatWidget props — generic over the message type (`TMessage`, the app's
 * FIMessage) and the custom-slot node type (`TNode`) the ChatHook is keyed on.
 */
export interface ChatWidgetProps<TMessage = ChatMessage, TNode = unknown> {
  /** REQUIRED — the conversation hook. No internal default. */
  chatHook: ChatHook<TMessage, TNode>;

  /** App ChatConfig (merged over the fi-glass neutral default). */
  config?: Partial<ChatConfig>;

  // ---- Auth (injected; was useAuth) ----
  user?: { sub?: string; name?: string } | null;
  isAuthenticated?: boolean;
  onLogin?: () => void;

  // ---- Navigation (typed prop; was 3 next/link hrefs) ----
  onNavigate?: (dest: ChatNavDest) => void;

  // ---- Responsive (injected, or computed internally via useMediaQuery) ----
  isMobile?: boolean;

  // ---- Initial UI state ----
  initialOpen?: boolean;
  initialMode?: ChatViewMode;
  embedded?: boolean;

  // ---- Input (message state lifted to the app; voice mutates it) ----
  // The conversation essentials — always required (there is no chat without them).
  message: string;
  onMessageChange: (value: string) => void;
  onSend: () => void;

  // ---- Preferences (app-owned; usePersonas resolves personaName) ----
  // OPTIONAL: a feature is OFF when its handler is absent. An app with no
  // response-mode toggle / personas (e.g. og118 hello-chat) simply omits these
  // and the toolbar hides the corresponding control. Mirrors ChatHook, which
  // already treats voice/personas/upload as optional capabilities.
  responseMode?: ResponseMode;
  selectedPersona?: PersonaType;
  personaName?: string;
  showThinking?: boolean;
  onResponseModeToggle?: () => void;
  onShowThinkingToggle?: () => void;
  onPersonaChange?: (persona: PersonaType) => void;
  onClearConversation?: () => void;

  // ---- Voice (state from the app's useChatVoiceRecorder) ----
  // OPTIONAL: omit onVoiceStart/onVoiceStop → the mic button is hidden.
  voiceState?: VoiceRecordingState;
  onVoiceStart?: () => void;
  onVoiceStop?: () => void;

  // ---- File upload (state from the app's useChatUpload) ----
  // OPTIONAL: omit onAttach → the attach control + file preview are hidden.
  uploadFile?: File | null;
  uploadStatus?: UploadStatus;
  isUploadActive?: boolean;
  onAttach?: () => void;
  onCancelUpload?: () => void;
  /**
   * What the app asks the user AFTER a document lands and BEFORE it is indexed —
   * aurity's "¿cómo debe usarlo la persona?" (reference / quote verbatim /
   * background context). Rendered under the file preview while the upload sits
   * in `pending_instructions`.
   *
   * Without this slot the step had nowhere to render: aurity's
   * ChatInstructionsPrompt was never mounted by anyone, so `setInstructions` was
   * never called, indexing never started, and the file chip span "Procesando…"
   * forever. A staged flow needs its stage.
   */
  uploadPrompt?: ReactNode;

  // ---- Conversation start screen ----
  isStartingConversation?: boolean;
  onStartConversation?: () => void;

  // ---- SLOTS (domain UI the app fills) ----
  /** PersonaSelectorPanel (uses @/components/ui/select) — lives in the app. */
  personaSelector?: ReactNode;
  /** HistorySearch (useAuth + backend fetch) — lives in the app. fi-glass owns the close. */
  renderHistory?: (ctx: { onClose: () => void }) => ReactNode;
  /** ChatWidgetMessages + ./messages subtree (domain) — lives in the app. fi-glass owns the view mode. */
  renderMessages?: (ctx: { viewMode: ChatViewMode }) => ReactNode;
  /** Copy-curl dev tool (uses app routes/env). */
  onCopyCurl?: () => void;
}

/** Props for the presentational shell skeleton (ChatContent). */
export interface ChatContentProps {
  config: ChatConfig;
  embedded: boolean;
  isAuthenticated: boolean;
  userName?: string;

  // Widget state (from useChatWidgetState)
  viewMode: ChatViewMode;
  isHistoryOpen: boolean;
  isStartingConversation: boolean;

  // Conversation gating (read from the ChatHook)
  messageCount: number;
  loading: boolean;
  isTyping: boolean;
  loadingInitial: boolean;
  customEmptyState?: ReactNode;
  customQuickReplies?: ReactNode;

  // Input
  message: string;

  // Preferences (optional — feature-off when the matching handler is absent)
  responseMode?: ResponseMode;
  selectedPersona?: PersonaType;
  personaName?: string;
  showThinking?: boolean;

  // Voice (optional)
  voiceState?: VoiceRecordingState;

  // File upload (optional)
  uploadFile?: File | null;
  uploadStatus?: UploadStatus;
  isUploadActive?: boolean;

  // Navigation
  onNavigate?: (dest: ChatNavDest) => void;

  // Actions (from useChatWidgetState)
  onModeChange: (mode: ChatViewMode) => void;
  onMinimize: () => void;
  onMaximize: () => void;
  onToggleDenseMode: () => void;
  onClose: () => void;
  onHistoryOpen: () => void;
  onHistoryClose: () => void;
  onStartConversation: () => void;

  // Actions (app-owned)
  onLogin: () => void;
  onMessageChange: (message: string) => void;
  onSend: () => void;
  // Optional capability handlers — their absence hides the matching control.
  onResponseModeToggle?: () => void;
  onShowThinkingToggle?: () => void;
  onPersonaChange?: (persona: PersonaType) => void;
  onClearConversation?: () => void;
  onVoiceStart?: () => void;
  onVoiceStop?: () => void;
  onAttach?: () => void;
  /** The staged "how should the persona use this document?" step (see above). */
  uploadPrompt?: ReactNode;
  onCancelUpload?: () => void;
  onCopyCurl?: () => void;

  // Slots
  personaSelector?: ReactNode;
  renderHistory?: (ctx: { onClose: () => void }) => ReactNode;
  renderMessages?: (ctx: { viewMode: ChatViewMode }) => ReactNode;
}
