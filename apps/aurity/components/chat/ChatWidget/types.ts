/**
 * ChatWidget Types
 *
 * Type definitions for the chat widget component.
 */

import type { ChatViewMode } from '../ChatWidgetContainer';
import type { ChatConfig } from '@/config/chat.config';
import type { ChatHook } from '@aurity-standalone/types/chat';

export interface ChatWidgetProps {
  /** Custom configuration (optional) */
  config?: Partial<ChatConfig>;
  /** Start with chat open (default: false) */
  initialOpen?: boolean;
  /** Initial view mode (default: 'normal') */
  initialMode?: ChatViewMode;
  /** Hide the floating button when closed - for embedded/page usage */
  embedded?: boolean;
  /** Dependency-injected chat hook */
  chatHook?: ChatHook;
}

// Re-export from ChatToolbar for consistency
export type { ResponseMode, PersonaType } from '../ChatToolbar';

export interface VoiceRecordingState {
  isRecording: boolean;
  isTranscribing: boolean;
  audioLevel: number;
  isSilent: boolean;
  recordingTime: number;
}

export type { ChatViewMode };
