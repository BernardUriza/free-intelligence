/**
 * Shared Recording Component Types
 *
 * Common types and configurations for recording UI components.
 * Used by: RecordingControls, VoiceMicButton, and future recording UIs.
 */

import type { LucideIcon } from 'lucide-react';

// =============================================================================
// Recording State
// =============================================================================

/**
 * Universal recording state enum.
 * All recording components should use these states.
 */
export type RecordingStateType =
  | 'idle'        // Ready to start
  | 'starting'    // Initializing microphone
  | 'recording'   // Actively recording
  | 'pausing'     // Stopping to pause
  | 'paused'      // Paused, can resume
  | 'resuming'    // Restarting after pause
  | 'processing'  // Processing/transcribing
  | 'stopping'    // Stopping to finish
  | 'finalized';  // Session complete

// =============================================================================
// Button Configuration
// =============================================================================

export type ButtonSize = 'sm' | 'md' | 'lg' | 'xl';

export interface ButtonSizeConfig {
  button: string;    // Domain class for button size
  icon: string;      // Domain class for icon size
  ring?: string;     // Domain class for ring/pulse size
}

export const BUTTON_SIZES: Record<ButtonSize, ButtonSizeConfig> = {
  sm: {
    button: 'rec-btn-sm',
    icon: 'rec-icon-sm',
    ring: 'rec-ring-sm',
  },
  md: {
    button: 'rec-btn-md',
    icon: 'rec-icon-md',
    ring: 'rec-ring-md',
  },
  lg: {
    button: 'rec-btn-lg',
    icon: 'rec-icon-lg',
    ring: 'rec-ring-lg',
  },
  xl: {
    button: 'rec-btn-xl',
    icon: 'rec-icon-xl',
    ring: 'rec-ring-xl',
  },
};

// =============================================================================
// Color Themes
// =============================================================================

export type ColorTheme = 'medical' | 'chat' | 'minimal';

export interface StateColors {
  idle: string;
  starting: string;
  recording: string;
  pausing: string;
  paused: string;
  resuming: string;
  processing: string;
  stopping: string;
  finalized: string;
}

export const COLOR_THEMES: Record<ColorTheme, StateColors> = {
  medical: {
    idle: 'rec-theme-medical-idle',
    starting: 'rec-theme-medical-starting',
    recording: 'rec-theme-medical-recording',
    pausing: 'rec-theme-medical-pausing',
    paused: 'rec-theme-medical-paused',
    resuming: 'rec-theme-medical-resuming',
    processing: 'rec-theme-medical-processing',
    stopping: 'rec-theme-medical-stopping',
    finalized: 'rec-theme-medical-finalized',
  },
  chat: {
    idle: 'rec-theme-chat-idle',
    starting: 'rec-theme-chat-starting',
    recording: 'rec-theme-chat-recording',
    pausing: 'rec-theme-chat-pausing',
    paused: 'rec-theme-chat-paused',
    resuming: 'rec-theme-chat-resuming',
    processing: 'rec-theme-chat-processing',
    stopping: 'rec-theme-chat-stopping',
    finalized: 'rec-theme-chat-finalized',
  },
  minimal: {
    idle: 'rec-theme-minimal-idle',
    starting: 'rec-theme-minimal-starting',
    recording: 'rec-theme-minimal-recording',
    pausing: 'rec-theme-minimal-pausing',
    paused: 'rec-theme-minimal-paused',
    resuming: 'rec-theme-minimal-resuming',
    processing: 'rec-theme-minimal-processing',
    stopping: 'rec-theme-minimal-stopping',
    finalized: 'rec-theme-minimal-finalized',
  },
};

// =============================================================================
// Icon Configuration
// =============================================================================

export interface StateIcons {
  idle: LucideIcon;
  starting: LucideIcon;
  recording: LucideIcon;
  pausing: LucideIcon;
  paused: LucideIcon;
  resuming: LucideIcon;
  processing: LucideIcon;
  stopping: LucideIcon;
  finalized: LucideIcon;
}

// =============================================================================
// Pulse/Animation Configuration
// =============================================================================

export type PulseStyle = 'none' | 'ping' | 'rings' | 'vad';

export interface PulseConfig {
  style: PulseStyle;
  color?: string;           // Color name (e.g. 'yellow-500')
  audioLevel?: number;      // 0-255 for VAD style
  isSilent?: boolean;       // For VAD color switching
}

// =============================================================================
// Status Text Configuration
// =============================================================================

export interface StatusTextConfig {
  idle: string;
  starting: string;
  recording: string;
  pausing: string;
  paused: string;
  resuming: string;
  processing: string;
  stopping: string;
  finalized: string;
}

export const STATUS_TEXT_ES: StatusTextConfig = {
  idle: 'Presiona para comenzar',
  starting: 'Iniciando...',
  recording: 'Grabando...',
  pausing: 'Pausando...',
  paused: 'Pausado',
  resuming: 'Reanudando...',
  processing: 'Procesando...',
  stopping: 'Finalizando...',
  finalized: 'Completado',
};

export const STATUS_TEXT_EN: StatusTextConfig = {
  idle: 'Press to start',
  starting: 'Starting...',
  recording: 'Recording...',
  pausing: 'Pausing...',
  paused: 'Paused',
  resuming: 'Resuming...',
  processing: 'Processing...',
  stopping: 'Stopping...',
  finalized: 'Complete',
};
