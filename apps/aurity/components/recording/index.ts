/**
 * Recording Components - Shared UI Primitives
 *
 * Reusable components for recording functionality across the app.
 *
 * Usage:
 *   import { RecordingButton, PulseRings, RecordingTimer } from '@/components/recording';
 *
 * Components:
 * - RecordingButton: Configurable circular button
 * - PulseRings: Animated ring effects (ping, rings, vad)
 * - RecordingTimer: Time display with optional dot
 * - StatusText: Status message display
 *
 * Types & Configs:
 * - RecordingStateType: Universal state enum
 * - BUTTON_SIZES: Size configurations
 * - COLOR_THEMES: Pre-built color schemes
 * - STATUS_TEXT_ES/EN: Localized status messages
 */

// Components
export { RecordingButton, type RecordingButtonProps } from './RecordingButton';
export { PulseRings, type PulseRingsProps } from './PulseRings';
export { RecordingTimer, formatRecordingTime, type RecordingTimerProps } from './RecordingTimer';
export { StatusText, type StatusTextProps } from './StatusText';

// Types & Configuration
export {
  // State types
  type RecordingStateType,
  // Button configuration
  type ButtonSize,
  type ButtonSizeConfig,
  BUTTON_SIZES,
  // Color themes
  type ColorTheme,
  type StateColors,
  COLOR_THEMES,
  // Pulse configuration
  type PulseStyle,
  type PulseConfig,
  // Status text
  type StatusTextConfig,
  STATUS_TEXT_ES,
  STATUS_TEXT_EN,
} from './types';
