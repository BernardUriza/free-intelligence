/**
 * fi-glass · shell types — the dependency-inverted ChatWidget contract.
 *
 * The shell consumes core's `ChatHook` (the conversation spine) and receives
 * everything domain-shaped as props or slots: auth (`user`/`isAuthenticated`/
 * `onLogin`), navigation (`onNavigate`, a TYPED union — not next/link), the
 * persona selector / history / messages (React-node SLOTS the app fills), and
 * the voice + file-upload state (their hooks live in the app). fi-glass NEVER
 * imports useAuth / useFIConversation / usePersonas / next/* / @/components/ui/*.
 */

import type { ReactNode } from 'react';
import type { ChatHook, ChatMessage } from '@free-intelligence/core';
import type { ChatConfig } from './config';

/** View modes handled by ChatWidgetContainer. */
export type ChatViewMode =
  | 'normal'
  | 'fullscreen'
  | 'dense'
  | 'minimized'
  | 'expanded';

/** Response verbosity preference (app-owned, surfaced in the toolbar). */
export type ResponseMode = 'explanatory' | 'concise';

/** Persona id — opaque string, resolved by the app's persona registry. */
export type PersonaType = string;

/** Typed navigation destinations — replaces the 3 hardcoded next/link hrefs. */
export type ChatNavDest = 'chat' | 'downloads' | 'personas';

/** Upload lifecycle the file-preview renders against (state owned by the app). */
export type UploadStatus =
  | 'selecting'
  | 'uploading'
  | 'pending_instructions'
  | 'processing'
  | 'indexed'
  | 'error';

/** Voice recorder snapshot the toolbar's mic button renders against. */
export interface VoiceRecordingState {
  isRecording: boolean;
  isTranscribing: boolean;
  audioLevel: number;
  isSilent: boolean;
  recordingTime: number;
}

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
  message: string;
  onMessageChange: (value: string) => void;
  onSend: () => void;

  // ---- Preferences (app-owned; usePersonas resolves personaName) ----
  responseMode: ResponseMode;
  selectedPersona: PersonaType;
  personaName: string;
  showThinking?: boolean;
  onResponseModeToggle: () => void;
  onShowThinkingToggle?: () => void;
  onPersonaChange: (persona: PersonaType) => void;
  onClearConversation?: () => void;

  // ---- Voice (state from the app's useChatVoiceRecorder) ----
  voiceState: VoiceRecordingState;
  onVoiceStart: () => void;
  onVoiceStop: () => void;

  // ---- File upload (state from the app's useChatUpload) ----
  uploadFile: File | null;
  uploadStatus: UploadStatus;
  isUploadActive: boolean;
  onAttach: () => void;
  onCancelUpload: () => void;

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

  // Preferences
  responseMode: ResponseMode;
  selectedPersona: PersonaType;
  personaName: string;
  showThinking?: boolean;

  // Voice
  voiceState: VoiceRecordingState;

  // File upload
  uploadFile: File | null;
  uploadStatus: UploadStatus;
  isUploadActive: boolean;

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
  onResponseModeToggle: () => void;
  onShowThinkingToggle?: () => void;
  onPersonaChange: (persona: PersonaType) => void;
  onClearConversation?: () => void;
  onVoiceStart: () => void;
  onVoiceStop: () => void;
  onAttach: () => void;
  onCancelUpload: () => void;
  onCopyCurl?: () => void;

  // Slots
  personaSelector?: ReactNode;
  renderHistory?: (ctx: { onClose: () => void }) => ReactNode;
  renderMessages?: (ctx: { viewMode: ChatViewMode }) => ReactNode;
}
