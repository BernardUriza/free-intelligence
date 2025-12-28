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
  button: string;    // Tailwind classes for button size
  icon: string;      // Tailwind classes for icon size
  ring?: string;     // Tailwind classes for ring/pulse size
}

export const BUTTON_SIZES: Record<ButtonSize, ButtonSizeConfig> = {
  sm: {
    button: 'w-10 h-10',
    icon: 'h-5 w-5',
    ring: 'ring-2',
  },
  md: {
    button: 'w-12 h-12',
    icon: 'h-6 w-6',
    ring: 'ring-2',
  },
  lg: {
    button: 'w-16 h-16',
    icon: 'h-8 w-8',
    ring: 'ring-3',
  },
  xl: {
    button: 'w-24 h-24',
    icon: 'h-10 w-10',
    ring: 'ring-4',
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
    idle: 'bg-emerald-500 hover:bg-emerald-600',
    starting: 'bg-cyan-500',
    recording: 'bg-yellow-500 hover:bg-yellow-600',
    pausing: 'bg-cyan-500',
    paused: 'bg-blue-500 hover:bg-blue-600',
    resuming: 'bg-cyan-500',
    processing: 'bg-slate-500',
    stopping: 'bg-cyan-500',
    finalized: 'bg-slate-600',
  },
  chat: {
    idle: 'bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600',
    starting: 'bg-blue-500',
    recording: 'bg-red-500 hover:bg-red-600',
    pausing: 'bg-blue-500',
    paused: 'bg-yellow-500 hover:bg-yellow-600',
    resuming: 'bg-blue-500',
    processing: 'bg-blue-500',
    stopping: 'bg-blue-500',
    finalized: 'bg-gray-400',
  },
  minimal: {
    idle: 'bg-slate-700 hover:bg-slate-600',
    starting: 'bg-slate-600',
    recording: 'bg-red-600 hover:bg-red-500',
    pausing: 'bg-slate-600',
    paused: 'bg-slate-600 hover:bg-slate-500',
    resuming: 'bg-slate-600',
    processing: 'bg-slate-600',
    stopping: 'bg-slate-600',
    finalized: 'bg-slate-800',
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
  color?: string;           // Tailwind color class
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
